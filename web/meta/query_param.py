from urllib.parse import urlencode, parse_qs, urlsplit, urlunsplit


def set_query_parameter(url, param_name, param_value):
    """Given a URL, set or replace a query parameter and return the
    modified URL.

    >>> set_query_parameter('http://example.com?foo=bar', 'foo', 'stuff')
    'http://example.com?foo=stuff'

    """
    scheme, netloc, path, query_string, fragment = urlsplit(url)
    query_params = parse_qs(query_string)

    deleted = False
    for _, value in query_params.items():
        if param_value in value:
            deleted = True

    if deleted:
        query_params.pop(param_name, None)
        clear = True
    if not deleted:
        query_params[param_name] = param_value
        clear = False

    new_query_string = urlencode(query_params, doseq=True)
    url = urlunsplit((scheme, netloc, path, new_query_string, fragment))

    return url, clear


def delete_query_parameter(url, param_name):
    """Given a URL, removes the query parameter and returns the
    modified URL.

    >>> delete_query_parameter('http://example.com?foo=bar', 'foo')
    'http://example.com'

    """
    scheme, netloc, path, query_string, fragment = urlsplit(url)
    query_params = parse_qs(query_string)
    query_params.pop(param_name, None)
    new_query_string = urlencode(query_params, doseq=True)
    url = urlunsplit((scheme, netloc, path, new_query_string, fragment))

    return url
