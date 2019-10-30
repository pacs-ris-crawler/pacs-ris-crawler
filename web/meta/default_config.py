"""
Default configuration
This can be overwritten with a `instance` folder on the parent level with
a configuration. The configuration file needs to be named 'config.cfg'.
"""

# Application settings
DEBUG = False
RESULT_LIMIT = 100

REPORT_SHOW_URL = 'http://meqpacscrllt01.uhbs.ch:9000/show?accession_number='

# Solr settings
SOLR_HOSTNAME = 'localhost'
SOLR_PORT = '8983'
SOLR_CORE_NAME = 'grouping'

SHOW_DOWNLOAD_OPTIONS = True
SHOW_TRANSFER_TARGETS = True

TRANSFER_TARGETS = [{'AE_TITLE': 'AE_TITLE', 'DISPLAY_NAME': 'Foo'}]

MOVA_DASHBOARD_URL = 'http://localhost:9001/rq'
MOVA_DOWNLOAD_URL = 'http://localhost:9001/download'
MOVA_TRANSFER_URL = 'http://localhost:9001/transfer'

# Zero foot print viewer integration
ZFP_VIEWER = ""