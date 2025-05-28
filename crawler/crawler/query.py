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
from crawler.util import load_config

log = structlog.get_logger()


def query_for_study_uid(config, accession_number):
    """There could be different study_uids for a single accession number.
    An example would be GRASP sequences."""
    # Load full configuration for DCMTK_BIN and merge with DICOM node config
    full_config = load_config()
    merged_config = {**full_config, **config}
    
    query = study_uid_query(merged_config, accession_number)
    result, _ = run(query)
    ids = []
    if result:
        for r in result:
            ids.append(r["StudyInstanceUID"])
    log.warning(
        f"No result found for accession number: {accession_number}\nQuery was: {query}"
    )
    return ids


def query_accession_number(config, study_uid):
    # Load full configuration for DCMTK_BIN and merge with DICOM node config
    full_config = load_config()
    merged_config = {**full_config, **config}
    
    query = basic_query(merged_config)
    query = add_study_uid(query, study_uid)
    result, _ = run(query)
    return result, query


def prefetch_accession_number(config, study_uid):
    # Load full configuration for DCMTK_BIN and merge with DICOM node config
    full_config = load_config()
    merged_config = {**full_config, **config}
    
    query = prefetch_query(merged_config, study_uid)
    run(query, parse_results=False)
    return query


def get_months_of_year(year: str) -> List[Dict[str, str]]:
    start, end = year_start_end(year)
    # MS is month start frequency
    return [d.strftime("%Y-%m") for d in pd.date_range(start, end, freq="MS")]


def query_day_accs(
    config, day, start_time="0000", end_time="2359"
) -> List[Dict[str, str]]:
    """Query for accession numbers for a given day and time range.
    If the query fails due to too many results:
    1. Split into half days (12 hours)
    2. If that fails, split into 2-hour chunks

    Args:
        config: DICOM configuration
        day: The day to query
        start_time: Start time in HHMM format (default "0000")
        end_time: End time in HHMM format (default "2359")
    """
    # Load full configuration for DCMTK_BIN and merge with DICOM node config
    full_config = load_config()
    merged_config = {**full_config, **config}
    
    query = accs_per_day(merged_config, day.strftime("%Y%m%d"), f"{start_time}-{end_time}")
    try:
        result, _ = run(query)
        return result
    except (DicomQueryError, subprocess.CalledProcessError) as e:
        log.info("splitting_time_range start_time=%s end_time=%s", start_time, end_time)
        # Convert times to integers for calculation
        start = int(start_time)
        end = int(end_time)

        # Calculate period length in hours
        period_length = (end - start) // 100  # Convert to hours

        if period_length >= 12:
            # Split into half days: 0000-1159 and 1200-2359
            first_end = 1159
            second_start = 1200
        elif period_length > 2:
            # Split into 2-hour chunks
            # e.g., 0000-0159, 0200-0359, etc.
            first_end = start + 159
            second_start = start + 200
        else:
            # If period is 2 hours or less, give up
            log.error(
                "time_range_too_small start_time=%s end_time=%s", start_time, end_time
            )
            return []

        # Format split points as 4-digit strings
        first_end_time = f"{first_end:04d}"
        second_start_time = f"{second_start:04d}"

        # Recursively query both halves
        first_half = query_day_accs(config, day, start_time, first_end_time)
        second_half = query_day_accs(config, day, second_start_time, end_time)

        return first_half + second_half
