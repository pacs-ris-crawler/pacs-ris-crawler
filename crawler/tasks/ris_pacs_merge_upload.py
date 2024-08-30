import json
import logging

from prefect import task, flow
from prefect.task_runners import ConcurrentTaskRunner
import requests

from crawler.config import get_solr_upload_url
from crawler.convert import convert_pacs_file, merge_pacs_ris
from tasks.accession import AccessionTask
from tasks.util import dict_to_str, load_config

# ConvertPacsFile Task
@task
def convert_pacs_file_task(query: dict) -> str:

    if "acc" in query:
        # Prefect flow run instead of Luigi task dependency
        AccessionTask(query["acc"], query["dicom_node"])

    # Read the input JSON file
    with open(f"data/{query['acc']}_accession.json", "r") as daily:
        json_in = json.load(daily)

    # Convert the PACS file
    json_out = convert_pacs_file(json_in)

    # Write the converted JSON to the output file
    output_path = f"data/{query['acc']}_pacs_converted.json"
    with open(output_path, "w") as my_dict:
        json.dump(json_out, my_dict, indent=4)

    return output_path

# MergePacsRis Task
@task
def merge_pacs_ris_task(query: dict) -> str:
    # Prefect task dependency (run convert_pacs_file_task first)
    pacs_file_path = convert_pacs_file_task(query)

    # Read the converted PACS file
    with open(pacs_file_path, "r") as daily:
        pacs_in = json.load(daily)

    # Merge PACS and RIS
    merged_out = merge_pacs_ris(pacs_in)

    # Write the merged JSON to the output file
    output_path = f"data/{query['acc']}_ris_pacs_merged.json"
    with open(output_path, "w") as my_dict:
        json.dump(merged_out, my_dict, indent=4)

    return output_path

# DailyUpConvertedMerged Task
@task
def daily_up_converted_merged_task(query: dict) -> str:
    # Prefect task dependency (run merge_pacs_ris_task first)
    merged_file_path = merge_pacs_ris_task(query)

    # Load configuration and get the upload URL
    config = load_config()
    upload_url = get_solr_upload_url(config)
    logging.debug("Uploading to url %s", upload_url)

    # Upload the merged JSON file to Solr
    with open(merged_file_path, "r") as in_file:
        file = {"file": (in_file.name, in_file, "application/json")}
        update_response = requests.post(
            url=upload_url, files=file, params={"commit": "true"}
        )
    if not update_response.ok:
        update_response.raise_for_status()
    else:
        output_path = f"data/{query['acc']}_solr_uploaded.txt"
        with open(output_path, "w") as my_file:
            my_file.write("Upload successful")

    return output_path

@flow
def merge_pacs_ris_flow(query: dict):
    return merge_pacs_ris_task(query)

# TriggerTask Flow
@flow(task_runner=ConcurrentTaskRunner())
def trigger_task_flow(acc: str, dicom_node: str):
    # example run command
    # python -m tasks.ris_pacs_merge_upload TriggerTask --acc 1234 --dicom-node SECTRA
    query = {"acc": acc, "dicom_node": dicom_node}
    # Execute the daily_up_converted_merged_task
    daily_up_converted_merged_task(query)
    print("Trigger task completed.")

# Main Function
def main():
    import argparse
    import sys

    parser = argparse.ArgumentParser(description="Run Prefect Task")
    parser.add_argument("task_name", type=str, help="Name of the task to run")
    parser.add_argument("--acc", type=str, required=True, help="Accession number")
    parser.add_argument("--dicom-node", type=str, required=True, help="DICOM node")

    args = parser.parse_args()

    # Dynamically run the correct flow based on task_name argument
    try:
        print(args.task_name)
        if args.task_name == "TriggerTask":
            trigger_task_flow(acc=args.acc, dicom_node=args.dicom_node)
        elif args.task_name == "MergePacsRis":
            # merge_pacs_ris_flow(acc=args.acc, dicom_node=args.dicom_node)
            print(merge_pacs_ris_flow({"acc": args.acc, "dicom_node": args.dicom_node}))

        else:
            print(f"Task {args.task_name} not recognized")
            sys.exit(1)
    except KeyError as e:
        print(f"Task {args.task_name} not found. Error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
