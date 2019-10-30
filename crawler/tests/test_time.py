import unittest

from crawler.ptime import split

INITIAL = '000000-235959'


class TimeSplitterTest(unittest.TestCase):
    def test_simple(self):
        l, r = split(INITIAL)
        self.assertEqual('000000-115959', l)
        self.assertEqual('120000-235959', r)

    def test_second_level(self):
        left, _ = split(INITIAL)
        l1, l2 = split(left)
        self.assertEqual('000000-055959', l1)
        self.assertEqual('060000-115959', l2)

    def test_one_error_case(self):
        l, r = split('060000-115959')
        self.assertEqual('060000-085959', l)
        self.assertEqual('090000-115959', r)

    def test_third_level(self):
        # 0-3, 3-6, 6-9, 9-12
        left, _ = split(INITIAL)
        l, r = split(left)
        ll, lr = split(l)
        rl, rr = split(r)
        self.assertEqual('000000-025959', ll)
        self.assertEqual('030000-055959', lr)
        self.assertEqual('060000-085959', rl)
        self.assertEqual('090000-115959', rr)

    def test_right(self):
        left, _ = split(INITIAL)
        l, _ = split(left)
        ll, _ = split(l)
        lll, rrr = split(ll)
        llll, rrrr = split(lll)
        self.assertEqual('000000-012959', lll)
        self.assertEqual('013000-025959', rrr)
        self.assertEqual('000000-004459', llll)
        self.assertEqual('004500-012959', rrrr)
