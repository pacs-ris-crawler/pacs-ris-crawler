import luigi
from prefect import task, flow

import argparse
import sys

from crawler.query import query_for_study_uid
from tasks.util import load_dicom_config

@task
def fetch_study_uids(accession_number, dicom_node):
    
    dicom_config = load_dicom_config(dicom_node)
    study_uids = query_for_study_uid(dicom_config, accession_number)

    with open(f"data/{accession_number}_accession.txt", "w") as outfile:
        for uid in study_uids:
            outfile.write(uid + "\n")

@flow
def study_uid_flow(accession_number, dicom_node):
    # example run command
    # python -m tasks.study_uid study_uid_flow --accession-number 1234 --dicom-node SECTRA 
    fetch_study_uids(accession_number, dicom_node)


def main():
    parser = argparse.ArgumentParser(description="Run Prefect Task")
    parser.add_argument("task_name", type=str, help="Name of the task to run")
    parser.add_argument("--accession-number", type=str, required=True, help="Accession number")
    parser.add_argument("--dicom-node", type=str, required=False, default="SECTRA", help="DICOM node")

    args = parser.parse_args()

    # Dynamically get the flow function based on the task_name argument
    try:
        flow_function = globals()[args.task_name]
    except KeyError:
        print(f"Task {args.task_name} not found")
        sys.exit(1)

    # Run the flow function with the provided arguments
    flow_function(accession_number=args.accession_number, dicom_node=args.dicom_node)

if __name__ == "__main__":
    main()