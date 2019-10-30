# PACS settings
AE_TITLE = "AE_TITLE"
AE_CALLED = "AE_CALLED"
PEER_ADDRESS = "127.0.0.1"
PEER_PORT = "104"


# Solr settings
SOLR_UPLOAD_URL = "http://localhost:8983/solr/pacs_crawler/update/json"

# RIS Report settings
REPORT_SHOW_URL = "http://localhost:9000/show?accession_number="
REPORT_USE = True

REPORT_USES_BASIC_AUTH = False
REPORT_USER = ""
REPORT_PWD = ""


# Luigi central scheduler
LUIGI_SCHEDULER = "http://localhost:8082"
