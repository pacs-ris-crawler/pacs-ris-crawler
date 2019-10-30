import unittest

from crawler.dicom import _is_start_or_end, _get_tag, _get_value, get_results


class DicomTest(unittest.TestCase):
    def test_start(self):
        line = 'I: ---------------------------'
        start = _is_start_or_end(line)
        self.assertEqual(True, start)

    def test_tag(self):
        line = 'I: (0008,0060) CS [MR] #   2, 1 Modality'
        tag = _get_tag(line)
        self.assertEqual('Modality', tag)

    def test_value(self):
        line = 'I: (0008,0060) CS [MR] #   2, 1 Modality'
        tag = _get_value(line)
        self.assertEqual('MR', tag)


    def test_all(self):
        with open('tests/test_data') as f:
            test_data = f.read().splitlines()
        r = get_results(test_data)
        self.assertEqual(2, len(r))
        print(len(r))