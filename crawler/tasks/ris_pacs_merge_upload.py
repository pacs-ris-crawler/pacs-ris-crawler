""" This file contains the tasks to downlad the json files from
    the ris as well as the routines to upload these files to solr
"""
import json
import logging

import luigi
import requests
from crawler.config import get_solr_upload_url
from crawler.convert import convert_pacs_file, merge_pacs_ris

from tasks.accession import AccessionTask
from tasks.util import dict_to_str, load_config


class ConvertPacsFile(luigi.Task):
    query = luigi.DictParameter()

    def requires(self):
        if "acc" in self.query:
            return AccessionTask(self.query["acc"], self.query["dicom_node"])

    def run(self):
        with self.input().open("r") as daily:
            json_in = json.load(daily)

        json_out = convert_pacs_file(json_in)

        with self.output().open("w") as my_dict:
            json.dump(json_out, my_dict, indent=4)

    def output(self):
        name = dict_to_str(self.query)
        return luigi.LocalTarget("data/%s_pacs_converted.json" % name)


class MergePacsRis(luigi.Task):
    query = luigi.DictParameter()

    def requires(self):
        return ConvertPacsFile(self.query)

    def run(self):
        with self.input().open("r") as daily:
            pacs_in = json.load(daily)
        merged_out = merge_pacs_ris(pacs_in)

        with self.output().open("w") as my_dict:
            json.dump(merged_out, my_dict, indent=4)

    def output(self):
        name = dict_to_str(self.query)
        return luigi.LocalTarget("data/%s_ris_pacs_merged.json" % name)


class DailyUpConvertedMerged(luigi.Task):
    query = luigi.DictParameter()

    def requires(self):
        return MergePacsRis(self.query)

    def run(self):
        config = load_config()
        upload_url = get_solr_upload_url(config)
        logging.debug("Uploading to url %s", upload_url)
        with self.input().open("r") as in_file:
            file = {"file": (in_file.name, in_file, "application/json")}
            update_response = requests.post(
                url=upload_url, files=file, params={"commit": "true"}
            )
        if not update_response.ok:
            update_response.raise_for_status()
        else:
            with self.output().open("w") as my_file:
                my_file.write("Upload successful")

    def output(self):
        name = dict_to_str(self.query)
        return luigi.LocalTarget("data/%s_solr_uploaded.txt" % name)


# example usage:
# PYTHONPATH='.' luigi --module tasks.ris_pacs_merge_upload DailyUpConvertedMerged --local-scheduler --day yyyy-mm-dd
if __name__ == "__main__":
    luigi.run()
