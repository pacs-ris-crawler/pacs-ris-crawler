from prefect import flow, task

from .convert import convert_pacs_file, merge_pacs_ris
from .query import query_accession_number, query_for_study_uid
from .tasks.util import load_dicom_config


@task
def _find_study_uids(dicom_node, accession_number):
    dicom_config = load_dicom_config(dicom_node)
    study_uids = query_for_study_uid(dicom_config, accession_number)
    return study_uids


@flow
def query_acc(dicom_node, accession_number):
    config = load_dicom_config(dicom_node)

    uids = _find_study_uids(dicom_node, accession_number)
    if len(uids) > 1:
        results = []
        for _id in uids:
            results.append(query_accession_number(config, _id))
    else:
        results = query_accession_number(config, uids[0])
    converted = convert_pacs_file(results)
    merged = merge_pacs_ris(converted)
    return merged
