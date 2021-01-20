""" This file contains the tasks to downlad the json files from
    the ris as well as the routines to upload these files to solr
"""
import json
import logging
import os

import requests

import luigi
from crawler.config import get_solr_upload_url
from crawler.convert import convert_pacs_file, merge_pacs_ris
from crawler.query import query_day_accs
from tasks.accession import AccessionTask
from tasks.study_description import StudyDescription
from tasks.util import dict_to_str, load_config


class ConvertPacsFile(luigi.Task):
    query = luigi.DictParameter()

    def requires(self):
        if "acc" in self.query:
            return AccessionTask(self.query["acc"])           
        if "day" in self.query:
            return StudyDescription("", self.query["day"], self.query["day"])
        elif "studydescription" in self.query:
            return StudyDescription(
                self.query["studydescription"],
                self.query["from_date"],
                self.query["to_date"],
            )

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


class DailyUpAccConvertedMerged(luigi.WrapperTask):
    day = luigi.DateParameter()

    def requires(self):
        config = load_config()
        results = query_day_accs(config, self.day)
        logging.debug(f"Got {len(results)} accession number for day: {self.day}")
        for i in results:
            if "AccessionNumber" in i:
                yield DailyUpConvertedMerged({"acc": i["AccessionNumber"]})


# example usage:
# PYTHONPATH='.' luigi --module tasks.ris_pacs_merge_upload DailyUpConvertedMerged --local-scheduler --day yyyy-mm-dd
if __name__ == "__main__":
    luigi.run()
