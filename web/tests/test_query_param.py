import unittest
from meta.query_param import set_query_parameter


class TestQueryParam(unittest.TestCase):
    def test_clearing(self):
        url = 'http://localhost?StudyDescription=foo'
        new_url = set_query_parameter(url, 'StudyDescription', 'foo')
        self.assertEqual(('http://localhost', True), new_url)

    def test_clearing_1(self):
        url = 'http://localhost?StudyDescription=foo&SeriesDescription=a'
        new_url = set_query_parameter(url, 'StudyDescription', 'foo')
        self.assertEqual(
            ('http://localhost?SeriesDescription=a', True), new_url)

    def test_setting(self):
        url = 'http://localhost?StudyDescription=foo'
        new_url = set_query_parameter(url, 'StudyDescription', 'bar')
        self.assertEqual(
            ('http://localhost?StudyDescription=bar', False), new_url)
