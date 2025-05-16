import json
import logging

import requests

from crawler.config import get_solr_upload_url
from crawler.convert import convert_pacs_file, merge_pacs_ris
from tasks.accession import accession
from tasks.util import dict_to_str, load_config


def convert_pacs_file_task(query: dict) -> str:
    if "acc" in query:
        # Prefect flow run instead of Luigi task dependency
        accession(query["acc"], query["dicom_node"])

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


def index_acc(acc: str):
    query = {"acc": acc, "dicom_node": "SECTRA"}
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
