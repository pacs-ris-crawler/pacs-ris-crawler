# Finds out the time ranges for a given day
import sys
import logging
import datetime as datetime
import pandas as pd

from typing import List, Dict
from crawler.command import (
    basic_query,
    study_uid_query,
    add_study_uid,
    add_time,
    add_day,
    add_day_range,
    add_modality,
    add_study_description,
    year_start_end,
    MODALITIES,
    INITIAL_TIME_RANGE,
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
        "No result found for accession number: {}".format(accession_number)
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


def query_month(config, year_month: str) -> List[Dict[str, str]]:
    start = datetime.datetime.strptime(year_month, "%Y-%m")
    end = start + pd.tseries.offsets.MonthEnd()
    results = []
    for day in pd.date_range(start, end):
        for mod in MODALITIES:
            results.extend(query_day_extended(config, mod, day, INITIAL_TIME_RANGE))
    return results


def query_day(config, day: str) -> List[Dict[str, str]]:
    query_date = datetime.datetime.strptime(day, "%Y-%m-%d")
    results = []
    for mod in MODALITIES:
        results.extend(query_day_extended(config, mod, query_date, INITIAL_TIME_RANGE))
    return results


def query_day_extended(
    config, mod: str, day: datetime.datetime, time_range: str
) -> List[Dict[str, str]]:
    query = prepare_query(config, mod, day, time_range)
    result, size = run(query)

    if size < 500:
        sys.stdout.write(".")
        sys.stdout.flush()
        return [result]
    else:
        sys.stdout.write("|")
        sys.stdout.flush()
        logging.debug(
            "results >= 500 for {} {} {}, splitting".format(mod, day, time_range)
        )
        l, r = split(time_range)
        return query_day_extended(config, mod, day, l) + query_day_extended(
            config, mod, day, r
        )


def prepare_query(config, mod, day, time_range):
    query = add_day(basic_query(config), day)
    query = add_modality(query, mod)
    query = add_time(query, time_range)
    return query

