import unittest
from meta.solr import solr_url, solr_terms_url


class TestSolr(unittest.TestCase):

    def test_url(self):
        config = {'SOLR_CORE_NAME': 'foo',
                  'SOLR_PORT': '8983',
                  'SOLR_HOSTNAME': 'http://localhost'}
        self.assertEqual('http://http://localhost:8983/solr/foo/query',
                         solr_url(config))

    def test_terms_url(self):
        config = {'SOLR_CORE_NAME': 'foo',
                  'SOLR_PORT': '8983',
                  'SOLR_HOSTNAME': 'http://localhost'}
        self.assertEqual('http://http://localhost:8983/solr/foo/terms',
                         solr_terms_url(config))
