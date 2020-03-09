import unittest
from pathlib import Path
import json
import pandas as pd

from crawler.convert import convert_pacs_file

sample_json = Path.cwd() / "tests" / "example.json"


class ConvertTest(unittest.TestCase):
    def setUp(self):
        with sample_json.open() as f:
            self.raw_data = json.load(f)
            self.data = convert_pacs_file(self.raw_data)

    def test_setup(self):
        self.assertEqual(17, len(self.raw_data))

    def test_conv(self):
        df_raw = pd.DataFrame.from_dict(self.raw_data)
        acc_example = len(df_raw[df_raw["AccessionNumber"] == "1"])
        study = [d for d in self.data if d["AccessionNumber"] == "1"][0]
        series = study["_childDocuments_"]
        self.assertEqual(acc_example, len(series))

    def test_conv2(self):
        df_raw = pd.DataFrame.from_dict(self.raw_data)
        acc_example = len(df_raw[df_raw["AccessionNumber"] == "2"])
        study = [d for d in self.data if d["AccessionNumber"] == "2"][0]
        series = study["_childDocuments_"]
        self.assertEqual(acc_example, len(series))
        self.assertEqual(
            "Sch\u00e4del sagittal Weichteil", series[0]["SeriesDescription"]
        )

    def test_conv3(self):
        df_raw = pd.DataFrame.from_dict(self.raw_data)
        acc_example = len(df_raw[df_raw["AccessionNumber"] == "3"])
        study = [d for d in self.data if d["AccessionNumber"] == "3"][0]
        series = study["_childDocuments_"]
        self.assertEqual(acc_example, len(series))

    def test_protocolname(self):
        df_raw = pd.DataFrame.from_dict(self.raw_data)
        study = [d for d in self.data if d["AccessionNumber"] == "1"]
        self.assertEqual(1, len(study))
        self.assertEqual("P_1;P_2", study[0]["ProtocolName"])
        
    def test_protocolname_second_series_contains_protocolname(self):
        df_raw = pd.DataFrame.from_dict(self.raw_data)
        study = [d for d in self.data if d["AccessionNumber"] == "3"]
        self.assertEqual(1, len(study))
        self.assertEqual("P_3", study[0]["ProtocolName"])

