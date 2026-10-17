import io
import json
import sys
from pathlib import Path
from unittest.mock import Mock, patch
from zipfile import ZipFile

import pandas as pd
import pytest
import requests
from flask import Flask

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from web import jev

QUERIES = [
    {'name': 'Finding', 'type': 'noul', 'instructions': 'Is a finding present?'},
    {'name': 'Location', 'type': 'choice', 'instructions': 'Which side?',
     'criteria': {'left': 'Left side', 'right': 'Right side'}},
]
ANSWERS = {'1': {'type': 'noul', 'noul': 0.0},
           '2': {'type': 'choice', 'choice': 'left', 'confidence': 0.42,
                 'probabilities': {'left': 0.71, 'right': 0.29}}}
STUDIES = [{'id': f'synthetic-{i}', 'AccessionNumber': f'TEST-{i}'} for i in range(3)]


@pytest.fixture
def app():
    app = Flask(__name__)
    app.config.update(TESTING=True, JEV_URL='http://kev.test/v1/systemone', JEV_MODEL='kev-latest',
                      JEV_TIMEOUT=15, JEV_MAX_STUDIES=5000,
                      SOLR_HOSTNAME='solr.test', SOLR_PORT='8983', SOLR_CORE_NAME='test')
    app.register_blueprint(jev.bp)
    return app


def test_client_batches_questions_and_preserves_confidence(app):
    session = Mock()
    session.post.return_value.json.return_value = {'answers': ANSWERS}
    questions = jev.questions_for(QUERIES)
    result = jev.evaluate('Synthetic report', questions, app.config, session)
    assert result['1']['noul'] == 0
    assert result['2']['confidence'] == 0.42
    session.post.assert_called_once_with('http://kev.test/v1/systemone', json={
        'model': 'kev-latest', 'state': 'Synthetic report', 'questions': questions}, timeout=15)


@pytest.mark.parametrize('answer', [None, {}, {'1': {'type': 'noul', 'noul': float('nan')}},
                                   {'1': {'type': 'noul', 'noul': True}},
                                   {'1': {'type': 'noul', 'noul': 1.1}}])
def test_invalid_answers_rejected(answer):
    with pytest.raises(ValueError):
        jev.validate_answers(answer, jev.questions_for(QUERIES[:1]))


def test_unknown_choice_and_missing_confidence_rejected():
    for answer in [{'type': 'choice', 'choice': 'elsewhere', 'confidence': .5},
                   {'type': 'choice', 'choice': 'left'}]:
        with pytest.raises(ValueError):
            jev.validate_answers({'1': answer}, jev.questions_for(QUERIES[1:]))


def test_query_validation():
    for queries in [[], QUERIES + QUERIES, [{'name': 'x', 'type': 'score', 'instructions': 'x'}],
                    [{'name': 'x', 'type': 'choice', 'instructions': 'x', 'criteria': {'a': ''}}]]:
        with pytest.raises(ValueError):
            jev.questions_for(queries)


def test_cohort_uses_all_studies_and_preserves_search_filters(app):
    with patch.object(jev, 'solr_fetch', return_value={'numFound': 5000, 'docs': STUDIES}) as fetch:
        response = app.test_client().post('/jev/cohort', json={'search': [
            ['RisReport', 'aneur*'], ['Modality', 'MR'], ['Modality', 'CT'], ['offset', '200']]})
    assert response.status_code == 200
    body = fetch.call_args.args[1]
    assert body['offset'] == 0 and body['limit'] == 5000
    assert body['params']['group'] == 'false'
    assert body['query'] == 'RisReport:(aneur*)'
    assert any('MR OR CT' in f for f in body['filter'])
    with patch.object(jev, 'solr_fetch', return_value={'numFound': 5001, 'docs': []}):
        assert app.test_client().post('/jev/cohort', json={'search': []}).status_code == 400


def batch_payload(studies=STUDIES):
    return {'studies': studies, 'search': [], 'queries': QUERIES}


def test_batch_skips_missing_continues_failures(app):
    docs = [dict(STUDIES[0], RisReport='Synthetic positive report.'),
            dict(STUDIES[1], RisReport='  '), dict(STUDIES[2], RisReport='Synthetic report.')]
    with patch.object(jev, 'solr_fetch', side_effect=[{'numFound': 3}, {'docs': docs}]), \
            patch.object(jev, 'evaluate', side_effect=[ANSWERS, requests.Timeout()]) as evaluate:
        response = app.test_client().post('/jev/batch', json=batch_payload())
    assert response.status_code == 200
    assert [o['status'] for o in response.json['outcomes']] == ['ok', 'missing', 'failed']
    assert response.json['remaining'] == [] and evaluate.call_count == 2
    assert evaluate.call_args_list[0].args[0] == 'Radiology Report: Synthetic positive report.'


def test_batch_bound_and_preflight(app):
    client = app.test_client()
    assert client.post('/jev/batch', json=batch_payload(STUDIES * 34)).status_code == 400
    with patch.object(jev, 'solr_fetch', return_value={'numFound': 5001}), patch.object(jev, 'evaluate') as evaluate:
        assert client.post('/jev/batch', json=batch_payload()).status_code == 400
        evaluate.assert_not_called()


def test_batch_budget_returns_only_unprocessed_studies(app):
    docs = [dict(s, RisReport='Synthetic report') for s in STUDIES]
    with patch.object(jev, 'solr_fetch', side_effect=[{'numFound': 3}, {'docs': docs}]), \
            patch.object(jev.time, 'monotonic', side_effect=[0, 0, 19.5]), \
            patch.object(jev, 'evaluate', return_value=ANSWERS) as evaluate:
        response = app.test_client().post('/jev/batch', json=batch_payload())
    assert len(response.json['outcomes']) == 1
    assert response.json['remaining'] == STUDIES[1:]
    assert evaluate.call_count == 1


def test_solr_failure_is_sanitized(app):
    with patch.object(jev, 'solr_fetch', side_effect=requests.ConnectionError('sensitive detail')):
        response = app.test_client().post('/jev/cohort', json={'search': []})
    assert response.status_code == 502
    assert 'sensitive detail' not in response.text


def completed_run():
    return {'name': 'Synthetic pipeline', 'model': 'kev-latest', 'started': '2026-01-01', 'elapsed': 1.2,
            'search': [['RisReport', '*']], 'queries': QUERIES, 'history': ['Completed'],
            'outcomes': [dict(STUDIES[0], status='ok', answers=ANSWERS),
                         dict(STUDIES[1], status='missing', reason='No report text.'),
                         dict(STUDIES[2], status='failed', reason='Model request timed out.')]}


def test_excel_aligns_ids_keeps_zero_and_blank_failures():
    df = pd.DataFrame([STUDIES[2], STUDIES[0], STUDIES[1]])
    out = io.BytesIO()
    with pd.ExcelWriter(out, engine='xlsxwriter') as writer:
        annotated = jev.annotate_export(df, completed_run())
        annotated.to_excel(writer, sheet_name='Sheet1', index=False)
        pd.DataFrame({'Kev summary': jev.summary_lines(completed_run())}).to_excel(writer, sheet_name='Kev summary', index=False)
    assert list(annotated.columns[-3:]) == ['Finding — P(Yes)', 'Location — Choice', 'Location — Confidence']
    assert pd.isna(annotated.iloc[0]['Finding — P(Yes)'])
    assert annotated.iloc[1]['Finding — P(Yes)'] == 0
    assert annotated.iloc[1]['Location — Confidence'] == .42
    assert pd.isna(annotated.iloc[2]['Location — Choice'])
    with ZipFile(out) as book:
        assert 'Kev summary' in book.read('xl/workbook.xml').decode()
        assert 'TEST-1' in book.read('xl/sharedStrings.xml').decode()


def test_disabled_independent_of_legacy_llm(app):
    app.config.update(JEV_URL='', SHOW_LLM_ASSISTED_FILTERING=True)
    assert app.test_client().post('/jev/cohort', json={'search': []}).status_code == 404


@pytest.fixture
def web_app():
    from flask.config import Config
    import web.default_config as defaults
    config = dict.fromkeys(('RECEIVER_URL', 'RECEIVER_DASHBOARD_URL', 'RECEIVER_DOWNLOAD_URL',
                            'RECEIVER_TRANSFER_URL', 'SECTRA_UNIVIEW'), '')
    with patch.multiple(defaults, create=True, **config), patch.object(Config, 'from_pyfile', return_value=True):
        from web.app import app
    app.config['TESTING'] = True
    return app


@pytest.mark.parametrize('anonymous', [False, True])
def test_existing_excel_routes_with_and_without_kev(web_app, anonymous):
    from web import views
    df = pd.DataFrame([dict(s, PatientName='SYNTHETIC-NAME', PatientBirthDate=19800101) for s in STUDIES])
    route = '/export_anon' if anonymous else '/export'
    run = completed_run()
    run['search'].append(['PatientName', 'SYNTHETIC-NAME'])
    for payload in ({'data': {'RisReport': '*'}}, {'json': {'search': run['search'], 'jev': run}}):
        with patch.object(views, 'query_all', return_value=df.copy()):
            response = web_app.test_client().post(route, **payload)
        assert response.status_code == 200
        with ZipFile(io.BytesIO(response.data)) as book:
            shared = book.read('xl/sharedStrings.xml').decode()
            workbook = book.read('xl/workbook.xml').decode()
            assert ('SYNTHETIC-NAME' not in shared) == anonymous
            assert ('Kev summary' in workbook) == ('json' in payload)
            if 'json' in payload:
                assert workbook.index('Sheet1') < workbook.index('Kev summary')
                assert 'P(Yes)' in shared and 'Confidence' in shared


def test_large_annotation_export_uses_json_without_form_limit(web_app):
    from web import views
    run = completed_run()
    run['outcomes'] = [dict(STUDIES[0], id=f'synthetic-{i}', AccessionNumber=f'TEST-{i}',
                            status='ok', answers=ANSWERS) for i in range(5000)]
    assert len(json.dumps(run)) > 500000
    rows = pd.DataFrame([{'id': o['id'], 'AccessionNumber': o['AccessionNumber']} for o in run['outcomes']])
    with patch.object(views, 'query_all', return_value=rows):
        response = web_app.test_client().post('/export', json={'search': [], 'jev': run})
    assert response.status_code == 200
