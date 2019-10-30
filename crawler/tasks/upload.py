import logging
import os

import requests

import luigi
from tasks.day import DayTask
from tasks.month import MonthTask


class UploadDayTask(luigi.Task):
    url = luigi.Parameter()
    day = luigi.Parameter()

    def requires(self):
        return DayTask(day=self.day)

    def run(self):
        logging.debug("Uploading to url %s", self.url)
        headers = {"content-type": "application/json"}
        params = {"commit": "true"}
        payload = self.input().open("rb").read()
        r = requests.post(self.url, data=payload, params=params, headers=headers)
        if r.status_code == requests.codes.ok:
            with self.output().open("w") as outfile:
                outfile.write("DONE")
        else:
            r.raise_for_status()

    def output(self):
        month_file = os.path.basename(self.input().path)
        return luigi.LocalTarget("data/%s.uploaded" % month_file)


class UploadMonthTask(luigi.Task):
    # Example run command
    # env PYTHONPATH='.' luigi --module tasks.upload UploadDayTask
    # --local-scheduler
    # --url http://meqpacscrllt01.uhbs.ch:8983/solr/grouping/update/json/docs
    # --day 2017-11-09
    url = luigi.Parameter()
    month = luigi.Parameter()

    def requires(self):
        return MonthTask(month=self.month)

    def run(self):
        logging.debug("Uploading to url %s", self.url)
        headers = {"content-type": "application/json"}
        params = {"commit": "true"}
        payload = self.input().open("rb").read()
        r = requests.post(self.url, data=payload, params=params, headers=headers)
        if r.status_code == requests.codes.ok:
            with self.output().open("w") as outfile:
                outfile.write("DONE")
        else:
            r.raise_for_status()

    def output(self):
        month_file = os.path.basename(self.input().path)
        return luigi.LocalTarget("data/%s.uploaded" % month_file)


if __name__ == "__main__":
    luigi.run()
