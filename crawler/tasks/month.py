import luigi
import crawler.writer as w
from crawler.query import query_month
from tasks.util import load_config


class MonthTask(luigi.Task):
    # month format is yyyy-mm
    month = luigi.Parameter()

    def run(self):
        config = load_config()
        results = query_month(config, self.month)
        with self.output().open('w') as outfile:
            w.write_file(results, outfile)

    def output(self):
        return luigi.LocalTarget('data/%s.json' % self.month)


if __name__ == '__main__':
    luigi.run()
