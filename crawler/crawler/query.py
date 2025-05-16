import subprocess
from typing import Dict, List

import pandas as pd
import structlog

from crawler.command import (
    accs_per_day,
    add_study_uid,
    basic_query,
    prefetch_query,
    study_uid_query,
    year_start_end,
)
from crawler.dicom import DicomQueryError
from crawler.executor import run

log = structlog.get_logger()


def query_for_study_uid(config, accession_number):
    """There could be different study_uids for a single accession number.
    An example would be GRASP sequences."""
    query = study_uid_query(config, accession_number)
    result, _ = run(query)
    if result:
        ids = []
        for r in result:
            ids.append(r["StudyInstanceUID"])
        return ids
    raise LookupError(
        f"No result found for accession number: {accession_number}\nQuery was: {query}"
    )


def query_accession_number(config, study_uid):
    query = basic_query(config)
    query = add_study_uid(query, study_uid)
    result, _ = run(query)
    return [result], query


def prefetch_accession_number(config, study_uid):
    query = prefetch_query(config, study_uid)
    run(query, parse_results=False)
    return query


def get_months_of_year(year: str) -> List[Dict[str, str]]:
    start, end = year_start_end(year)
    # MS is month start frequency
    return [d.strftime("%Y-%m") for d in pd.date_range(start, end, freq="MS")]


def query_day_accs(config, day) -> List[Dict[str, str]]:
    # needed to split because it was too many results for sectra, e.g. day = 2022-09-13
    query_am = accs_per_day(config, day.strftime("%Y%m%d"), "0000-0800")
    result_am1, _ = run(query_am)
    
    query_am = accs_per_day(config, day.strftime("%Y%m%d"), "0800-1000")
    result_am2, _ = run(query_am)

    query_am = accs_per_day(config, day.strftime("%Y%m%d"), "1001-1159")
    result_am3, _ = run(query_am)

    query_pm = accs_per_day(config, day.strftime("%Y%m%d"), "1200-1400")
    result_pm1, _ = run(query_pm)

    query_pm = accs_per_day(config, day.strftime("%Y%m%d"), "1401-1600")
    result_pm2, _ = run(query_pm)

    query_pm = accs_per_day(config, day.strftime("%Y%m%d"), "1601-1800")
    result_pm3, _ = run(query_pm)

    query_pm = accs_per_day(config, day.strftime("%Y%m%d"), "1801-2359")
    result_pm4, _ = run(query_pm)
    return result_am1 + result_am2 + result_am3 + result_pm1 + result_pm2 + result_pm3 + result_pm4