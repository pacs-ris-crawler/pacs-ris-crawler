import unittest
from meta.paging import calc


class TestPaging(unittest.TestCase):
    def test_total_pages(self):
        result = calc(100, '0', 10)
        self.assertEqual(5, len(result))

    def test_pages_only_20_shown(self):
        result = calc(550, '10', 10)
        self.assertEqual(9, len(result))

    def test_zero_pages(self):
        result = calc(99 , 0, 100)
        self.assertEqual(0, len(result))

    def test_active_1(self):
        result = calc(200, '0', 100)
        self.assertEqual(2, len(result))
        self.assertEqual(True, result[0][2])

    def test_active_2(self):
        result = calc(1200, '1', 100)
        self.assertEqual(True, result[1][2])
        self.assertEqual(6, len(result))

    def test_active_3(self):
        result = calc(1200, '5', 100)
        self.assertEqual(True, result[4][2])

    def test_last_1(self):
        result = calc(100, '5', 10)
        self.assertEqual(9, len(result))
        self.assertEqual(True, result[0][3])

    def test_last_2(self):
        result = calc(100, '4', 10)
        self.assertEqual(False, result[0][3])
