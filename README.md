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

## How to start cli
* flask --debug --app app run --port 7777 --reload