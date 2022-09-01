from typing import Dict, List

import pandas as pd

from .command import (accs_per_day, add_study_uid, basic_query, study_uid_query,
                     year_start_end)
from .executor import run


def query_for_study_uid(config, accession_number):
    """There could be different study_uids for a single accession number.
    An example would be GRASP sequences."""
    query = study_uid_query(config, accession_number)
    result = run(query)
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
    result = run(query)
    return result


def get_months_of_year(year: str) -> List[Dict[str, str]]:
    start, end = year_start_end(year)
    # MS is month start frequency
    return [d.strftime("%Y-%m") for d in pd.date_range(start, end, freq="MS")]


def query_day_accs(config, day) -> List[Dict[str, str]]:
    query = accs_per_day(config, day.strftime("%Y%m%d"))
    result = run(query)
    # not wrapping the result in a list is *no* mistake!
    return result
