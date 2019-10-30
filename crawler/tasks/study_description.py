import json

import luigi
import crawler.writer as w
from crawler.convert import convert_pacs_file, merge_pacs_ris
from crawler.query import query_study_description
from tasks.util import load_config


class StudyDescription(luigi.Task):
    study_description = luigi.Parameter()
    from_date = luigi.Parameter()
    to_date = luigi.Parameter()

    def run(self):
        config = load_config() 
        results = query_study_description(
            config, self.study_description, self.from_date, self.to_date
        )
        with self.output().open('w') as outfile:
            w.write_file(results, outfile)


    def output(self):
        n = "".join(x for x in self.study_description if x.isalnum())
        return luigi.LocalTarget("data/%s-from-%s-to-%s.json" % (n, self.from_date, self.to_date))


if __name__ == "__main__":
    luigi.run()
