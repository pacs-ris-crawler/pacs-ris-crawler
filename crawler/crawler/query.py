import subprocess
from typing import Dict, List

import pandas as pd
import structlog

from crawler.command import (
    accs_per_day,
    add_series_uid,
    add_study_uid,
    basic_query,
    image_query,
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


US_EXPAND_MODALITIES = {"US"}


def query_series_instances(config, study_uid, series_uid):
    """IMAGE C-FIND for all instances in one series."""
    full_config = load_config()
    merged_config = {**full_config, **config}
    query = add_series_uid(add_study_uid(image_query(merged_config), study_uid), series_uid)
    result, _ = run(query)
    return result, query


def series_to_instance_rows(series, instances):
    """Copy series metadata onto each IMAGE result that has a SOPInstanceUID."""
    rows = []
    seen = set()
    series_desc = (series.get("SeriesDescription") or "").strip()
    for inst in instances:
        sop = (inst.get("SOPInstanceUID") or "").strip()
        if not sop or sop in seen:
            continue
        seen.add(sop)
        row = series.copy()
        row["SOPInstanceUID"] = sop
        instance_number = (inst.get("InstanceNumber") or "").strip()
        if instance_number:
            row["InstanceNumber"] = instance_number
            suffix = f" (#{instance_number})"
            if series_desc and suffix not in series_desc:
                row["SeriesDescription"] = f"{series_desc}{suffix}"
            elif not series_desc:
                row["SeriesDescription"] = f"Instance {instance_number}"
        rows.append(row)
    return rows


def expand_us_series_to_instances(config, series_results):
    """Replace multi-instance US series with one row per SOPInstanceUID."""
    if not series_results:
        return series_results
    expanded = []
    for series in series_results:
        if series.get("Modality") not in US_EXPAND_MODALITIES:
            expanded.append(series)
            continue
        study_uid = series.get("StudyInstanceUID")
        series_uid = series.get("SeriesInstanceUID")
        if not study_uid or not series_uid:
            expanded.append(series)
            continue
        try:
            instances, image_query_cmd = query_series_instances(
                config, study_uid, series_uid
            )
        except (DicomQueryError, subprocess.CalledProcessError) as exc:
            log.warning(
                "us_image_query_failed study_uid=%s series_uid=%s error=%s",
                study_uid,
                series_uid,
                exc,
            )
            expanded.append(series)
            continue
        rows = series_to_instance_rows(series, instances or [])
        if len(rows) <= 1:
            log.debug(
                "us_series_kept_as_series series_uid=%s instance_count=%s query=%s",
                series_uid,
                len(rows),
                image_query_cmd,
            )
            expanded.append(series)
            continue
        log.info(
            "us_series_expanded series_uid=%s instances=%s",
            series_uid,
            len(rows),
        )
        expanded.extend(rows)
    return expanded


def query_accession_number(config, study_uid):
    # Load full configuration for DCMTK_BIN and merge with DICOM node config
    full_config = load_config()
    merged_config = {**full_config, **config}
    
    query = basic_query(merged_config)
    query = add_study_uid(query, study_uid)
    result, _ = run(query)
    result = expand_us_series_to_instances(config, result)
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
