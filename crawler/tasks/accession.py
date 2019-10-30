import luigi
import crawler.writer as w
from crawler.query import query_accession_number
from tasks.study_uid import StudyUIDTask
from tasks.util import load_config


class AccessionTask(luigi.Task):
    # example run command
    # python -m tasks.accession AccessionTask --accession-number 1234 --local-scheduler
    accession_number = luigi.Parameter()

    def requires(self):
        return StudyUIDTask(self.accession_number)

    def run(self):
        config = load_config()
        study_uids = []
        with self.input().open("r") as f:
            for line in f:
                study_uids.append(line.strip())

        results = []
        for study_uid in study_uids:
            results.append(query_accession_number(config, study_uid))
        flat = [item for sublist in results for item in sublist]
        with self.output().open("w") as outfile:
            w.write_file(flat, outfile)

    def output(self):
        return luigi.LocalTarget("data/%s_accession.json" % self.accession_number)


if __name__ == "__main__":
    luigi.run()
