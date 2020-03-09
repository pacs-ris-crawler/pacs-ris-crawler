# Finds out the time ranges for a given day
import datetime as datetime
import logging
import sys
from typing import Dict, List

import pandas as pd

from crawler.command import (
    add_day,
    add_day_range,
    add_modality,
    add_study_description,
    add_study_uid,
    add_time,
    basic_query,
    study_uid_query,
    year_start_end,
    accs_per_day,
)
from crawler.executor import run


def query_for_study_uid(config, accession_number):
    """ There could be different study_uids for a single accession number.
    An example would be GRASP sequences."""
    query = study_uid_query(config, accession_number)
    result, _ = run(query)
    if result:
        ids = []
        for r in result:
            ids.append(r["StudyInstanceUID"])
        return ids
    raise LookupError(
        "No result found for accession number: {}\nQuery was: {}".format(
            accession_number, query
        )
    )


def query_study_description(config, study_description, from_date, to_date):
    query = basic_query(config)
    query = add_study_description(query, study_description)
    query = add_day_range(query, from_date, to_date)
    result, _ = run(query)
    return [result]


def query_accession_number(config, study_uid):
    query = basic_query(config)
    query = add_study_uid(query, study_uid)
    result, _ = run(query)
    return [result]


def get_months_of_year(year: str) -> List[Dict[str, str]]:
    start, end = year_start_end(year)
    # MS is month start frequency
    return [d.strftime("%Y-%m") for d in pd.date_range(start, end, freq="MS")]


def query_day_accs(config, day) -> List[Dict[str, str]]:
    query = accs_per_day(config, day.strftime("%Y%m%d"))
    result, _ = run(query)
    return result

