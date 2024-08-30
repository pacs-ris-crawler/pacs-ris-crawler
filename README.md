# PACS / RIS Crawler
![Build status](https://github.com/pacs-ris-crawler/pacs-ris-crawler/workflows/PACS/RIS%20Crawler%20CI/badge.svg)


This is a major revision of the previous [PACS/RIS crawler](https://github.com/joshy/meta/) 
solution developed for the clinic of 
[Radiology & Nuclear Medicine](https://www.unispital-basel.ch/en/ueber-uns/bereiche/medizinische-querschnittsfunktionen/kliniken-institute-abteilungen/radiology-department/kliniken-institute/radiology-nuclear-medicine-clinic/) 
at the  [University Hospital Basel](https://www.unispital-basel.ch/en/).

The documentation can be found at: https://pacs-ris-crawler.github.io/

## Requirements
* python 3.9
* solr 7.7 (for now)

## How is the data populated?
Via cron and root account (that is questionable)
`0 1 * * * /var/www/env3.6_meta/bin/python /var/www/pacs-ris-crawler/crawler/cron-daily-upload.py --host localhost --port 5009 > /var/log/cron-daily-upload.log 2>&1`

## Migration from Luigi to Prefect for Task Scheduling in 08/2024
Steps to be followed:
1) start prefect server (accessible under http://127.0.0.1:4200)
    prefect server start
2) build deployments of flows (visible under http://127.0.0.1:4200/deployments in case already deployed)
    cd crawler
    prefect deployment build -n "PrefetchTask Deployment" tasks/accession.py:PrefetchTask -a
    prefect deployment build -n "AccessionTask Deployment" tasks/accession.py:AccessionTask -a
    prefect deployment build -n "TriggerTask Deployment" tasks/ris_pacs_merge_upload.py:trigger_task_flow -a
    prefect deployment build -n "MergePacsRis Deployment" tasks/ris_pacs_merge_upload.py:merge_pacs_ris_flow -a
3) start prefect agent and set limit for number of concurrent tasks (example n=7 because most magically powerful number)
    prefect agent start -q 'default' --limit 7
4) start pacscrawler and experiment
    python runcrawler.py