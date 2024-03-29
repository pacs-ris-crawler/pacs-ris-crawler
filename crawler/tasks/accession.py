import crawler.writer as w
import luigi
from crawler.query import query_accession_number, prefetch_accession_number

from tasks.study_uid import StudyUIDTask
from tasks.util import load_prefetch_node, load_dicom_config


class PrefetchTask(luigi.Task):
    # example run command
    # python -m tasks.accession PrefetchTask --accession-number 1234 --local-scheduler
    accession_number = luigi.Parameter()

    def requires(self):
        return StudyUIDTask(self.accession_number, "SECTRA")

    def run(self):
        config = load_prefetch_node()
        study_uids = []
        with self.input().open("r") as f:
            for line in f:
                study_uids.append(line.strip())

        for study_uid in study_uids:
            cmd = prefetch_accession_number(config, study_uid)
        with self.output().open("w") as f:
            f.write(cmd)

    def output(self):
        return luigi.LocalTarget("data/%s_prefetch_command.txt" % self.accession_number)

class AccessionTask(luigi.Task):
    # example run command
    # python -m tasks.accession AccessionTask --accession-number 1234 --local-scheduler
    accession_number = luigi.Parameter()
    dicom_node = luigi.Parameter()

    def requires(self):
        return StudyUIDTask(self.accession_number, self.dicom_node)

    def run(self):
        config = load_dicom_config(self.dicom_node)
        study_uids = []
        with self.input().open("r") as f:
            for line in f:
                study_uids.append(line.strip())

        results = []
        for study_uid in study_uids:
            result, command = query_accession_number(config, study_uid)
            results.append(result)
        flat = [item for sublist in results for item in sublist]
        w.write_file(flat, self.output().path)
        #with self.output().open("w") as outfile:
        #   w.write_file(flat, outfile)
        if self.output().exists():
            with open("data/%s_command.txt" % self.accession_number, "w") as f:
                f.write(command)
            

    def output(self):
        return luigi.LocalTarget("data/%s_accession.json" % self.accession_number)


if __name__ == "__main__":
    luigi.run()
