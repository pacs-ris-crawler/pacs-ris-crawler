# PACS settings
AE_TITLE = "AE_TITLE"
AE_CALLED = "AE_CALLED"
PEER_ADDRESS = "127.0.0.1"
PEER_PORT = "104"

# DCMTK settings - Path to DCMTK binaries
DCMTK_BIN = "/usr/bin"


# Solr settings
SOLR_UPLOAD_URL = "http://localhost:8983/solr/pacs_crawler/update/json"

# RIS Report settings
REPORT_SHOW_URL = "http://localhost:9000/show?accession_number="
REPORT_USE = True

REPORT_USES_BASIC_AUTH = False
REPORT_USER = ""
REPORT_PWD = ""

# Prefect scheduler
PREFECT_SERVER = "http://localhost:4200"


MODALITIES = ['CT', 'MR', 'PT', 'CR', 'XA', 'SR', 'NM', 'MG', 'US', 'DX', 'RF',
              'OT', 'PR', 'KO', 'SC', 'SD', 'PX', 'DR']