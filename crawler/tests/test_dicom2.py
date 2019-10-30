import unittest

from crawler.dicom import _is_start_or_end, _get_tag, _get_value, get_results


class DicomTest(unittest.TestCase):
    def test_start(self):
        line = 'W: ---------------------------'
        start = _is_start_or_end(line)
        self.assertEqual(True, start)

    def test_tag(self):
        line = 'W: (0008,0052) CS [STUDY ]'
        tag = _get_tag(line)
        self.assertEqual('QueryRetrieveLevel', tag)

    def test_value(self):
        line = 'W: (0020,000d) UI [9.2.841.113619.6.95.31.0.3.4.1.24.13.6109561]'
        tag = _get_value(line)
        self.assertEqual('9.2.841.113619.6.95.31.0.3.4.1.24.13.6109561', tag)


    def test_all(self):
        with open('tests/test_data2') as f:
            test_data = f.read().splitlines()
        r = get_results(test_data)
        self.assertEqual(1, len(r))
        print(len(r))