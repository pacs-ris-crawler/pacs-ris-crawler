import luigi
import crawler.writer as w
from crawler.query import query_day_accs
from tasks.util import load_config
from tasks.accession import AccessionTask


class DayTask(luigi.Task):
    # example run command
    # python -m tasks.day DayTask --day 2017-01-01 --local-scheduler
    # day format is yyyy-mm-dd
    day = luigi.DateParameter()

    # timeout in seconds, if is not finished by then, do a timeout
    # 600s = 10min
    worker_timeout = 600

    resources = {"pacs_connection": 1}

    def run(self):
        config = load_config()
        results = query_day_accs(config, self.day)
        for i in results:
            yield AccessionTask(accession_number=i["AccessionNumber"])


if __name__ == "__main__":
    luigi.run()
