import json

import luigi
import requests

from tasks.accession import AccessionTask
from tasks.util import load_config

class AccessionStoreTask(luigi.Task):

    # example run command
    # python -m tasks.cdwh_store AccessionStoreTask --accession-number 1234 --local-scheduler
    accession_number = luigi.Parameter()

    def requires(self):
        return AccessionTask(self.accession_number)

    def run(self):
        config = load_config()
        post_url = config.get("CDWH_STORE_URL", "")
        if not post_url:
            print("No CDWH_STORE_ULR configured in instance/config.cfg, exiting.")
            exit(1)
        with self.input().open("r") as daily:
            json_in = json.load(daily)

        r = requests.post(post_url, json=json_in)
        r.raise_for_status()
        with self.output().open("w") as o:
            o.write("done")
    
    def output(self):
        return luigi.LocalTarget("data/%s_cdwh.json" % self.accession_number)


if __name__ == "__main__":
    luigi.run()
