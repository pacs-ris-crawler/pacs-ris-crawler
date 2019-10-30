
def solr_url(config):
    """ Returns the solr url.
    Core name and host are taking from configuration which needs to be passed
    in. Can be a simple dictionary.
    """
    return _solr_core_url(config) + 'query'


def solr_terms_url(config):
    """ Returns the solr base url.
    Core name and host are taking from configuration which needs to be passed
    in. Can be a simple dictionary.
    """
    return _solr_core_url(config) + 'terms'


def _solr_core_url(config):
    hostname = config['SOLR_HOSTNAME']
    port = config['SOLR_PORT']
    core_name = config['SOLR_CORE_NAME']
    return 'http://{}:{}/solr/{}/'.format(hostname, port, core_name)
