import crawler.writer as w
from crawler.query import query_for_study_uid

from crawler.query import prefetch_accession_number, query_accession_number
from tasks.util import load_dicom_config, load_prefetch_node


def fetch_study_uids(accession_number, dicom_node):
    dicom_config = load_dicom_config(dicom_node)
    study_uids = query_for_study_uid(dicom_config, accession_number)

    with open(f"data/{accession_number}_accession.txt", "w") as outfile:
        for uid in study_uids:
            outfile.write(uid + "\n")


def run_prefetch_task(accession_number: str) -> None:
    config = load_prefetch_node()
    study_uids = []
    with open(f"data/{accession_number}_accession.txt", "r") as f:
        for line in f:
            study_uids.append(line.strip())

    cmds = []
    for study_uid in study_uids:
        cmd = prefetch_accession_number(config, study_uid)
        cmds.append(cmd + "\n")

    with open(f"data/{accession_number}_prefetch_command.txt", "w") as f:
        for cmd in cmds:
            f.write(cmd)


def run_accession_task(accession_number: str, dicom_node: str) -> None:
    config = load_dicom_config(dicom_node)
    study_uids = []
    with open(f"data/{accession_number}_accession.txt", "r") as f:
        for line in f:
            study_uids.append(line.strip())

    results = []
    for study_uid in study_uids:
        result, command = query_accession_number(config, study_uid)
        results.append(result)

    flat = [item for sublist in results for item in sublist]
    w.write_file(flat, f"data/{accession_number}_accession.json")

    with open(f"data/{accession_number}_command.txt", "w") as f:
        f.write(command)


def prefetch_task(accession_number: str) -> None:
    fetch_study_uids(accession_number, "SECTRA")
    run_prefetch_task(accession_number)


def accession(accession_number: str, dicom_node: str) -> None:
    fetch_study_uids(accession_number, dicom_node)
    run_accession_task(accession_number, dicom_node)
