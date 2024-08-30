import argparse
import sys

from prefect import task, flow
from prefect.task_runners import ConcurrentTaskRunner

import crawler.writer as w
from crawler.query import query_accession_number, prefetch_accession_number
from prefect.concurrency.sync import concurrency
from tasks.study_uid import study_uid_flow  # Import the Prefect flow
from tasks.util import load_prefetch_node, load_dicom_config


@task
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

@task
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

@flow(task_runner=ConcurrentTaskRunner())
def PrefetchTask(accession_number: str) -> None:
    with concurrency("prefetch_limit", occupy=7):
        study_uid_flow(accession_number, "SECTRA")
        run_prefetch_task(accession_number)

@flow(task_runner=ConcurrentTaskRunner())
def AccessionTask(accession_number: str, dicom_node: str) -> None:
    # python -m tasks.accession AccessionTask --accession-number 1234
    study_uid_flow(accession_number, dicom_node)  # Replace Luigi task with Prefect flow
    run_accession_task(accession_number, dicom_node)


def main():
    parser = argparse.ArgumentParser(description="Run Prefect Task")
    parser.add_argument("task_name", type=str, help="Name of the task to run")
    parser.add_argument("--accession-number", type=str, required=True, help="Accession number")
    parser.add_argument("--dicom-node", type=str, help="DICOM node (required for AccessionTask)", default="SECTRA")

    args = parser.parse_args()

    # Dynamically get the flow function based on the task_name argument
    try:
        flow_function = globals()[args.task_name]
    except KeyError:
        print(f"Task {args.task_name} not found")
        sys.exit(1)

    # Execute the flow with the provided arguments
    if args.task_name == "PrefetchTask":
        flow_function(accession_number=args.accession_number)
    elif args.task_name == "AccessionTask":
        flow_function(accession_number=args.accession_number, dicom_node=args.dicom_node)
    else:
        print(f"Task {args.task_name} not recognized")
        sys.exit(1)

if __name__ == "__main__":
    main()
