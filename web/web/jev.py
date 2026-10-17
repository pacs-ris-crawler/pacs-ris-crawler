import json
import math
import time

import requests
from flask import Blueprint, current_app, jsonify, request
from urllib3.util import Timeout
from werkzeug.datastructures import MultiDict

from common.text import fix_utf8_mojibake
from web.query import query_body
from web.solr import solr_url

bp = Blueprint('jev', __name__, url_prefix='/jev')
BATCH_SIZE = 100
BATCH_SECONDS = 20


def questions_for(queries):
    if not isinstance(queries, list) or not queries:
        raise ValueError('Add and confirm at least one query.')
    questions, names = {}, set()
    for i, query in enumerate(queries, 1):
        name = query.get('name', '').strip()
        instructions = query.get('instructions', '').strip()
        kind = query.get('type')
        if not name or name in names or not instructions or kind not in ('noul', 'choice'):
            raise ValueError('Queries need unique names, a question, and type Noul or Choice.')
        names.add(name)
        question = {'type': kind, 'instructions': instructions}
        if kind == 'choice':
            criteria = query.get('criteria')
            if (not isinstance(criteria, dict) or len(criteria) < 2
                    or any(not k.strip() or not isinstance(v, str) for k, v in criteria.items())):
                raise ValueError('Choice queries need at least two named options.')
            question['criteria'] = {k: v or k for k, v in criteria.items()}
        questions[str(i)] = question
    return questions


def probability(value):
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value) or not 0 <= value <= 1:
        raise ValueError('Invalid model probability.')
    return value


def validate_answers(answers, questions):
    if not isinstance(answers, dict) or set(answers) != set(questions):
        raise ValueError('Incomplete model answers.')
    result = {}
    for key, question in questions.items():
        answer = answers[key]
        if not isinstance(answer, dict) or answer.get('type') != question['type']:
            raise ValueError('Invalid model answer type.')
        if question['type'] == 'noul':
            result[key] = {'type': 'noul', 'noul': probability(answer.get('noul'))}
        else:
            choice = answer.get('choice')
            if not isinstance(choice, str) or choice not in question['criteria']:
                raise ValueError('Invalid model choice.')
            result[key] = {'type': 'choice', 'choice': choice,
                           'confidence': probability(answer.get('confidence'))}
    return result


def evaluate(state, questions, config, session, timeout=None):
    response = session.post(config['JEV_URL'], json={
        'model': config['JEV_MODEL'], 'state': state, 'questions': questions,
    }, timeout=timeout if timeout is not None else config['JEV_TIMEOUT'])
    response.raise_for_status()
    return validate_answers(response.json().get('answers'), questions)


def search_body(search, limit):
    body = query_body(MultiDict(search), limit)
    body['offset'] = 0
    body['params'].update({'group': 'false', 'fl': 'id,AccessionNumber'})
    body['filter'].append('Category:parent')
    return body


def solr_fetch(session, body, deadline):
    remaining = deadline - time.monotonic()
    if remaining <= 0:
        raise requests.Timeout()
    response = session.post(solr_url(current_app.config), json=body,
                            timeout=Timeout(total=remaining, connect=min(3, remaining)))
    response.raise_for_status()
    return response.json()['response']


@bp.before_request
def enabled():
    if not current_app.config['JEV_URL']:
        return jsonify(error='Kev is not configured.'), 404


@bp.errorhandler(ValueError)
def invalid_request(error):
    return jsonify(error=str(error)), 400


@bp.errorhandler(requests.RequestException)
def unavailable(error):
    return jsonify(error='Could not fetch the cohort from Solr. Try again.'), 502


def check_count(result):
    if result['numFound'] > current_app.config['JEV_MAX_STUDIES']:
        raise ValueError(f"Narrow the initial search to at most {current_app.config['JEV_MAX_STUDIES']} studies.")


@bp.post('/cohort')
def cohort():
    body = search_body(request.get_json()['search'], current_app.config['JEV_MAX_STUDIES'])
    with requests.Session() as session:
        result = solr_fetch(session, body, time.monotonic() + BATCH_SECONDS)
    check_count(result)
    return jsonify(studies=result['docs'], model=current_app.config['JEV_MODEL'])


@bp.post('/batch')
def batch():
    data = request.get_json()
    studies = data['studies']
    if not isinstance(studies, list) or not 1 <= len(studies) <= BATCH_SIZE:
        raise ValueError('Send between 1 and 100 studies per batch.')
    ids = [study['id'] for study in studies]
    if len(set(ids)) != len(ids):
        raise ValueError('Duplicate study IDs in batch.')
    questions = questions_for(data['queries'])
    deadline = time.monotonic() + BATCH_SECONDS
    body = search_body(data['search'], 0)
    outcomes = []
    with requests.Session() as session:
        check_count(solr_fetch(session, body, deadline))
        body['limit'] = len(ids)
        body['params']['fl'] = 'id,AccessionNumber,RisReport'
        body['filter'].append('id:(' + ' OR '.join(json.dumps(i, ensure_ascii=False) for i in ids) + ')')
        docs = {doc['id']: doc for doc in solr_fetch(session, body, deadline)['docs']}
        for study in studies:
            remaining = deadline - time.monotonic()
            if remaining < 1:
                break
            doc = docs.get(study['id'])
            outcome = {'id': study['id'], 'AccessionNumber': study['AccessionNumber']}
            report = doc.get('RisReport', '') if doc else ''
            if not doc:
                outcome.update(status='failed', reason='Study no longer matches the search.')
            elif not report or not report.strip():
                outcome.update(status='missing', reason='No report text.')
            else:
                try:
                    timeout = min(current_app.config['JEV_TIMEOUT'], remaining)
                    answers = evaluate('Radiology Report: ' + fix_utf8_mojibake(report), questions,
                                       current_app.config, session,
                                       Timeout(total=timeout, connect=min(3, timeout)))
                    outcome.update(status='ok', answers=answers)
                except requests.Timeout:
                    outcome.update(status='failed', reason='Model request timed out.')
                except requests.RequestException:
                    outcome.update(status='failed', reason='Model request failed.')
                except (ValueError, AttributeError):
                    outcome.update(status='failed', reason='Invalid model response.')
            outcomes.append(outcome)
    return jsonify(outcomes=outcomes, remaining=studies[len(outcomes):])


def summary_lines(run):
    lines = [f"Kev pipeline: {run['name']}", f"Model: {run['model']}",
             f"Started: {run['started']}", f"Elapsed: {run['elapsed']:.1f} seconds", '', 'Initial search:']
    lines.extend(f'{key}: {value}' for key, value in run['search'] if value and key not in ('page', 'offset'))
    lines.extend(['', 'Queries:'])
    for query in run['queries']:
        lines.append(f"{query['name']} ({query['type']}): {query['instructions']}")
        lines.extend(f'  {key}: {value}' for key, value in query.get('criteria', {}).items())
    lines.extend(['', f"Studies: {len(run['outcomes'])}"])
    for status in ('ok', 'missing', 'failed'):
        lines.append(f"{status}: {sum(o['status'] == status for o in run['outcomes'])}")
    lines.extend(f"{o['AccessionNumber']}: {o['reason']}" for o in run['outcomes'] if o['status'] != 'ok')
    lines.extend(['', 'Activity:'] + run.get('history', []))
    return lines


def annotate_export(df, run):
    questions = questions_for(run['queries'])
    outcomes = {o['id']: o for o in run['outcomes']}
    answers = {key: validate_answers(o['answers'], questions)
               for key, o in outcomes.items() if o['status'] == 'ok'}
    for i, query in enumerate(run['queries'], 1):
        fields = [('P(Yes)', 'noul')] if query['type'] == 'noul' else [('Choice', 'choice'), ('Confidence', 'confidence')]
        for label, field in fields:
            column = f"{query['name']} — {label}"
            if column in df.columns:
                raise ValueError('Query name conflicts with an existing export column.')
            df[column] = df['id'].map(lambda key: answers.get(key, {}).get(str(i), {}).get(field))
    return df


@bp.post('/summary')
def summary():
    return current_app.response_class('\n'.join(summary_lines(request.get_json())), mimetype='text/plain')
