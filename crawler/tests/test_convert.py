import unittest
from pathlib import Path
import json
import pandas as pd

from unittest.mock import MagicMock, patch

from crawler.convert import convert_pacs_file, fetch_ris_report, merge_pacs_ris

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


def test_instance_child_uses_sop_as_id():
    raw = [
        {
            "AccessionNumber": "33043305",
            "PatientID": "USB0002312888",
            "PatientBirthDate": "19800101",
            "StudyDate": "20260721",
            "Modality": "US",
            "StudyInstanceUID": "1.2.3",
            "SeriesInstanceUID": "1.2.3.4",
            "SOPInstanceUID": "1.2.3.4.5",
            "SeriesNumber": "1",
            "InstanceNumber": "7",
            "SeriesDescription": "Echokardiografische Untersuchung (#7)",
        },
        {
            "AccessionNumber": "33043305",
            "PatientID": "USB0002312888",
            "PatientBirthDate": "19800101",
            "StudyDate": "20260721",
            "Modality": "US",
            "StudyInstanceUID": "1.2.3",
            "SeriesInstanceUID": "1.2.3.4",
            "SOPInstanceUID": "1.2.3.4.6",
            "SeriesNumber": "1",
            "InstanceNumber": "8",
            "SeriesDescription": "Echokardiografische Untersuchung (#8)",
        },
    ]
    converted = convert_pacs_file(raw)
    children = converted[0]["_childDocuments_"]
    assert len(children) == 2
    assert children[0]["id"] == "1.2.3.4.5"
    assert children[0]["SOPInstanceUID"] == "1.2.3.4.5"
    assert children[0]["InstanceNumber"] == "7"
    assert children[1]["id"] == "1.2.3.4.6"


def _response(status_code, text=""):
    response = MagicMock()
    response.status_code = status_code
    response.text = text
    if status_code >= 400:
        response.raise_for_status.side_effect = Exception(f"HTTP {status_code}")
    return response


@patch("crawler.convert.get")
def test_fetch_ris_report_treats_502_as_empty(mock_get):
    mock_get.return_value = _response(502, "Bad Gateway")
    assert fetch_ris_report("https://report.example/sectra?accession_number=33043305") == ""
    mock_get.return_value.raise_for_status.assert_not_called()


@patch("crawler.convert.get")
def test_fetch_ris_report_treats_empty_body_as_empty(mock_get):
    mock_get.return_value = _response(200, "  \n")
    assert fetch_ris_report("https://report.example/sectra?accession_number=33043305") == ""


@patch("crawler.convert.get")
def test_fetch_ris_report_returns_text(mock_get):
    mock_get.return_value = _response(200, "Findings: normal")
    assert fetch_ris_report("https://report.example/show?accession_number=1") == "Findings: normal"


@patch("crawler.convert.load_config")
@patch("crawler.convert.get_report_show_url")
@patch("crawler.convert.get")
def test_merge_pacs_ris_indexes_when_sectra_returns_502(mock_get, mock_url, mock_config):
    mock_config.return_value = {
        "REPORT_USES_BASIC_AUTH": False,
        "REPORT_USE": True,
        "REPORT_USER": "",
        "REPORT_PWD": "",
    }
    mock_url.return_value = "https://report.example/sectra?accession_number="
    mock_get.return_value = _response(502, "Bad Gateway")
    pacs = [{"AccessionNumber": "33043305", "PatientID": "USB0002312888"}]
    merged = merge_pacs_ris(pacs)
    assert len(merged) == 1
    assert merged[0]["RisReport"] == ""
    assert merged[0]["AccessionNumber"] == "33043305"

