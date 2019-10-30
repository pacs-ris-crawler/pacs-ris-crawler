import configparser
from itertools import chain

import luigi
import crawler.writer as w
from crawler.query import query_for_study_uid


class StudyUIDTask(luigi.Task):
    # example run command
    # python -m tasks.accession AccessionTask --accession-number 1234 --local-scheduler
    accession_number = luigi.Parameter()

    def run(self):
        config = configparser.ConfigParser()
        filename = "./instance/config.cfg"
        with open(filename) as fp:
            config.read_file(chain(["[PACS]"], fp), source=filename)
        study_uids = query_for_study_uid(config, self.accession_number)
        with self.output().open("w") as outfile:
            for i in study_uids:
                outfile.write(i + "\n")

    def output(self):
        return luigi.LocalTarget("data/%s_accession.txt" % self.accession_number)


if __name__ == "__main__":
    luigi.run()
