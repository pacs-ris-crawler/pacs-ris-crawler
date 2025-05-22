import crawler.writer as w
from crawler.query import (
    prefetch_accession_number,
    query_accession_number,
    query_for_study_uid,
)
from tasks.util import load_dicom_config, load_prefetch_node

import logging

logger = logging.getLogger(__name__)


def fetch_study_uids(accession_number, dicom_node):
    dicom_config = load_dicom_config(dicom_node)
    study_uids = query_for_study_uid(dicom_config, accession_number)
    return study_uids


def run_prefetch_task(study_uids: list) -> None:
    config = load_prefetch_node()
    cmds = []
    for study_uid in study_uids:
        cmd = prefetch_accession_number(config, study_uid)
        cmds.append(cmd + "\n")
        # for debugging
        logger.debug("Run prefetch command was %s", cmd)


def run_accession_task(dicom_node: str, study_uids: list) -> list:
    config = load_dicom_config(dicom_node)
    results = []
    for study_uid in study_uids:
        result, command = query_accession_number(config, study_uid)
        # for debugging
        logger.debug("Run accession command was %s", command)
        if result and any(result):
            results.append(result)

    flat = [item for sublist in results for item in sublist]
    if results and flat:
        return flat
    return []


def prefetch_task(accession_number: str) -> None:
    study_uids = fetch_study_uids(accession_number, "SECTRA")
    run_prefetch_task(study_uids)


def accession(accession_number: str, dicom_node: str) -> list:
    study_uids = fetch_study_uids(accession_number, dicom_node)
    flat_json = run_accession_task(dicom_node, study_uids)
    return flat_json
