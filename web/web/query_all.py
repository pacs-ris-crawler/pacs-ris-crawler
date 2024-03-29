import json
from math import ceil

import pandas as pd
from requests import RequestException, get
from werkzeug.datastructures import MultiDict

from web.query import query_body


def query_all(search_params: MultiDict, solr_url: str):
    limit = search_params.get("Limit", 100)
    query = query_body(search_params, limit=limit)
    query["params"]["group"] = "false"
    query, docs, results_size = _query(query, solr_url)
    requests_needed = ceil(results_size / limit)
    offsets = [x * limit for x in range(0, requests_needed)]
    result = []
    for i in offsets:
        query["offset"] = i
        _, docs, results_size = _query(query, solr_url)
        result.append(pd.DataFrame.from_dict(docs))
    if len(result) > 0:
        return pd.concat(result)
    return None


def _query(query, solr_url):
    headers = {"content-type": "application/json"}
    try:
        response = get(solr_url, data=json.dumps(query), headers=headers)
        data = response.json()
        docs = data["response"]["docs"]
        results = data["response"]["numFound"]
        return query, docs, results
    except RequestException as e:
        print(e)
