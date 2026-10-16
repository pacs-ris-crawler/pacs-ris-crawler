import json
import unittest

import pandas as pd
from requests import Request

from web.convert import convert


class TestConvert(unittest.TestCase):
    def study(self, **overrides):
        study = {
            "PatientID": "synthetic-patient",
            "PatientBirthDate": 19800101,
            "StudyDescription": "Synthetic study",
            "StudyDate": 20250101,
            "AccessionNumber": "synthetic-accession",
            "StudyInstanceUID": "1.2.3",
            "_childDocuments_": [{"SeriesInstanceUID": "1.2.3.4"}],
        }
        study.update(overrides)
        return study

    def test_missing_metadata_in_bulk_payload(self):
        incomplete = self.study()
        del incomplete["PatientBirthDate"]
        del incomplete["StudyDescription"]
        df = pd.DataFrame([self.study(), incomplete])
        data = convert(df)
        self.assertEqual(len(data), 2)
        self.assertEqual(data[1]["patient_birth_date"], "")
        self.assertEqual(data[1]["study_description"], "")
        self.assertEqual(data[0]["study_description"], "Synthetic study")
        # Prepare a real requests payload without contacting any service.
        for options in ({"dir": "test", "image_type": "dicom", "queue_prio": "low"},
                        {"target": "test"}):
            payload = {"data": data, **options}
            prepared = Request("POST", "http://receiver.invalid/", json=payload).prepare()
            self.assertEqual(json.loads(prepared.body), payload)

    def test_absent_columns_and_nullable_values(self):
        for missing in (None, float("nan"), pd.NA, pd.NaT):
            with self.subTest(missing=repr(missing)):
                study = self.study(PatientBirthDate=missing)
                del study["StudyDescription"]
                data = convert(pd.DataFrame([study]))
                self.assertEqual(data[0]["patient_birth_date"], "")
                self.assertEqual(data[0]["study_description"], "")
                json.dumps(data, allow_nan=False)

    def test_missing_series_metadata_uses_defaults(self):
        child = {"SeriesInstanceUID": "1.2.3.4", "StudyInstanceUID": float("nan"),
                 "SeriesDescription": float("nan"), "SeriesNumber": float("nan"),
                 "SOPInstanceUID": None, "InstanceNumber": pd.NA}
        data = convert(pd.DataFrame([self.study(_childDocuments_=[child])]))
        self.assertEqual(data[0]["study_uid"], "1.2.3")
        self.assertEqual(data[0]["series_number"], 9999)
        self.assertEqual(data[0]["series_description"], "")
        self.assertEqual(data[0]["sop_instance_uid"], "")
        self.assertEqual(data[0]["instance_number"], "")
        json.dumps(data, allow_nan=False)

    def test_series_study_uid_takes_precedence(self):
        child = {"SeriesInstanceUID": "1.2.3.4", "StudyInstanceUID": "1.2.5"}
        data = convert(pd.DataFrame([self.study(_childDocuments_=[child])]))
        self.assertEqual(data[0]["study_uid"], "1.2.5")

    def test_missing_study_uid_is_skipped_without_logging_patient_data(self):
        with self.assertLogs(level="ERROR") as logs:
            data = convert(pd.DataFrame([self.study(StudyInstanceUID=float("nan"))]))
        self.assertEqual(data, [])
        self.assertNotIn("synthetic-patient", " ".join(logs.output))
        self.assertNotIn("synthetic-accession", " ".join(logs.output))

    def test_string_children_still_supported(self):
        study = self.study()
        study["_childDocuments_"] = repr(study["_childDocuments_"])
        data = convert(pd.DataFrame([study]))
        self.assertEqual(data[0]["series_uid"], "1.2.3.4")
