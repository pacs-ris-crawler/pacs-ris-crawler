import json
from math import ceil

import pandas as pd
from requests import RequestException, get
from werkzeug.datastructures import MultiDict

from meta.query import query_body
from meta.solr import solr_url


def query_all(search_params: MultiDict, solr_url: str):
    limit = search_params.get('Limit', 100)
    query = query_body(search_params, limit=limit)
    query['params']['group'] = False
    query, docs, results_size = _query(query, solr_url)
    requests_needed = ceil(results_size / limit)
    offsets = [x*limit for x in range(0, requests_needed)]
    result = []
    for i in offsets:
        query['offset'] = i
        _, docs, results_size = _query(query, solr_url)
        result.append(pd.DataFrame.from_dict(docs))
    if result:
        # otherwise reload of the search results after export to excel
        # was not working because group=False even if query object is copied
        # I really don't understand what is going on.
        query['params']['group'] = True
        return pd.concat(result)
    else:
        return pd.DataFrame()


def _query(query, solr_url):
    headers = {'content-type': "application/json"}
    try:
        response = get(solr_url, data=json.dumps(query), headers=headers)
        data = response.json()
        docs = data['response']['docs']
        results = data['response']['numFound']
        return query, docs, results
    except RequestException as e:
        print(e)
