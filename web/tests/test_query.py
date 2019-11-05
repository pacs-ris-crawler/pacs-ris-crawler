import unittest
import meta.query
from werkzeug.datastructures import MultiDict


class TestQueryStuff(unittest.TestCase):
    def test_date(self):
        args = MultiDict(
            [("RisReport", "foo"), ("StartDate", "1.1.2016"), ("EndDate", "31.12.2016")]
        )
        result = meta.query.query_body(args)
        self.assertEqual(result["query"], "RisReport:(foo)")

    def test_filter_single(self):
        args = MultiDict(
            [
                ("query", "foo"),
                ("StartDate", "1.1.2016"),
                ("EndDate", "31.12.2016"),
                ("StudyDescription", "lorem ipsum"),
            ]
        )
        result = meta.query.query_body(args)
        self.assertEqual(
            result["filter"],
            ["StudyDescription:(lorem ipsum)", "StudyDate:[20160101 TO 20161231]"],
        )

    def test_filter_multiple(self):
        args = MultiDict(
            [
                ("query", "foo"),
                ("StartDate", "1.1.2016"),
                ("EndDate", "31.12.2016"),
                ("StudyDescription", "lorem ipsum"),
            ]
        )
        result = meta.query.query_body(args)
        self.assertEqual(
            result["filter"],
            ["StudyDescription:(lorem ipsum)", "StudyDate:[20160101 TO 20161231]"],
        )

    def test_filter_all(self):
        args = MultiDict(
            [
                ("query", "foo"),
                ("StartDate", "1.1.2016"),
                ("EndDate", "31.12.2016"),
                ("StudyDescription", "lorem ipsum"),
                ("PatientID", "123"),
                ("PatientName", "Hans Mueller"),
                ("AccessionNumber", "A123456789"),
            ]
        )
        result = meta.query.query_body(args)
        self.assertEqual(
            result["filter"],
            [
                "StudyDescription:(lorem ipsum)",
                "PatientID:(123)",
                "PatientName:(Hans Mueller)",
                "AccessionNumber:(A123456789)",
                "StudyDate:[20160101 TO 20161231]",
            ],
        )

    def test_filter_single_modality(self):
        args = MultiDict(
            [
                ("query", "foo"),
                ("StartDate", "1.1.2016"),
                ("EndDate", "31.12.2016"),
                ("Modality", "CT"),
            ]
        )
        result = meta.query.query_body(args)
        self.assertEqual(
            result["filter"],
            [
                "StudyDate:[20160101 TO 20161231]",
                "{!parent which=Category:parent}(+Modality:(CT))",
            ],
        )

    def test_filter_multiple_modality(self):
        args = MultiDict(
            [
                ("query", "foo"),
                ("StartDate", "1.1.2016"),
                ("EndDate", "31.12.2016"),
                ("Modality", "CT"),
                ("Modality", "MR"),
            ]
        )
        result = meta.query.query_body(args)
        self.assertEqual(
            result["filter"],
            [
                "StudyDate:[20160101 TO 20161231]",
                "{!parent which=Category:parent}(+Modality:(CT OR MR))",
            ],
        )
