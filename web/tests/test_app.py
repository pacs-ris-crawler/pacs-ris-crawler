import unittest

from meta.app import to_date

class TestToDate(unittest.TestCase):
    def test_empty(self):
        self.assertEqual(to_date(''), '')

    def test_valid_case(self):
        self.assertEqual(to_date(20171231), '31.12.2017')

