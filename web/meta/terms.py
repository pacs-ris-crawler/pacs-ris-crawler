from operator import itemgetter
from requests import get

from meta.solr import solr_terms_url


def get_terms_data(config):
    params = [('terms.fl', 'StudyDescription'),
              ('terms.fl', 'SeriesDescription'),
              ('terms.fl', 'InstitutionName'),
              ('terms.limit', 1000),
              ('wt', 'json')]

    response = get(solr_terms_url(config), params=params)
    data = response.json()
    terms = data.get('terms', '')
    result = []
    for key, value in terms.items():
        result.append((key, _to_tuple(value)))
    sorted(data, key=itemgetter(0))
    return result


def _to_tuple(data):
    return list((data[pos], data[pos+1]) for pos in range(0, len(data) - 2, 2))
