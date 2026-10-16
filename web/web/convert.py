import ast
import logging

import pandas as pd


def _value(record, key, default=""):
    """Keep pandas missing values out of the receiver's JSON payload."""
    value = record.get(key)
    return default if pd.isna(value) else value


def convert(df):
    """Convert the query all dataframe to a download json structure"""
    data = []
    for _, row in df.iterrows():
        parent = {
            "patient_id": _value(row, "PatientID"),
            "patient_birth_date": _value(row, "PatientBirthDate"),
            "study_description": _value(row, "StudyDescription"),
            "study_date": _value(row, "StudyDate"),
            "accession_number": _value(row, "AccessionNumber"),
        }
        children = row["_childDocuments_"]
        if isinstance(children, str):
            children = ast.literal_eval(children)

        for s in children:
            p = parent.copy()
            # Important: Newer versions of the crawler has the StudyInstanceUID
            # on the series level (because of GRASP e.g.) Now if the series level
            # is empty it should  use the one from the study level
            p["study_uid"] = _value(s, "StudyInstanceUID") or _value(row, "StudyInstanceUID")
            p["series_uid"] = s["SeriesInstanceUID"]
            p["series_description"] = _value(s, "SeriesDescription")
            p["series_number"] = _value(s, "SeriesNumber", 9999)
            p["sop_instance_uid"] = _value(s, "SOPInstanceUID")
            p["instance_number"] = _value(s, "InstanceNumber")
            if not bool(p.get("study_uid")):
                logging.error(
                    "Following serie not in download because of missing StudyInstanceUID, need to reindex solr"
                )
            else:
                data.append(p)
    return data
