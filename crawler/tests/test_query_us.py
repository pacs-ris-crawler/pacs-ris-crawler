from crawler.query import series_to_instance_rows


def test_series_to_instance_rows_skips_duplicates_and_empty_sop():
    series = {
        "Modality": "US",
        "SeriesInstanceUID": "1.2.3.4",
        "SeriesDescription": "Echokardiografische Untersuchung",
        "SeriesNumber": "1",
    }
    instances = [
        {"SOPInstanceUID": "1.2.3.4.5", "InstanceNumber": "1"},
        {"SOPInstanceUID": "1.2.3.4.5", "InstanceNumber": "1"},
        {"SOPInstanceUID": "", "InstanceNumber": "2"},
        {"SOPInstanceUID": "1.2.3.4.6", "InstanceNumber": "3"},
    ]
    rows = series_to_instance_rows(series, instances)
    assert [r["SOPInstanceUID"] for r in rows] == ["1.2.3.4.5", "1.2.3.4.6"]
    assert rows[0]["SeriesDescription"] == "Echokardiografische Untersuchung (#1)"
    assert rows[1]["InstanceNumber"] == "3"
    assert rows[0]["SeriesInstanceUID"] == "1.2.3.4"
