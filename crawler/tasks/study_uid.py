import luigi
from crawler.query import query_for_study_uid
from tasks.util import load_dicom_config

class StudyUIDTask(luigi.Task):
    # example run command
    # python -m tasks.study_uid StudyUIDTask --accession-number 1234 --local-scheduler
    accession_number = luigi.Parameter()
    dicom_node = luigi.Parameter()

    def run(self):
        dicom_config = load_dicom_config(self.dicom_node)
        study_uids = query_for_study_uid(dicom_config, self.accession_number)
        with self.output().open("w") as outfile:
            for i in study_uids:
                outfile.write(i + "\n")

    def output(self):
        return luigi.LocalTarget("data/%s_accession.txt" % self.accession_number)


if __name__ == "__main__":
    luigi.run()
