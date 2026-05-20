DEBUG=False

## Location of where the image data should be donwloaded to (Full path!)
IMAGE_FOLDER = '/home/foo/image_data'

# DCMTK settings
DCMIN = '/Applications/dcmtk/dcm.in'
DCMTK_BIN = '/Applications/dcmtk/dcmtk-3.6.0-mac-i686-dynamic/bin/'

# Pacs self identification
AE_TITLE = 'SCHWARZHORN'

# Remote PACS settings
AE_TITLE = 'MOVESCU'
AE_CALLED = 'ORTHANC'
PEER_ADDRESS = '127.0.0.1'
PEER_PORT = 4242
INCOMING_PORT = 11110

# Retrieve method: 'movescu' (DIMSE C-MOVE) or 'dicomweb' (WADO-RS)
RETRIEVE_METHOD = 'movescu'

# DICOMweb settings (only used when RETRIEVE_METHOD = 'dicomweb')
DICOMWEB_QIDO_BASE_URL = ''
DICOMWEB_WADO_BASE_URL = ''
DICOMWEB_TOKEN = ''
DICOMWEB_USER = ''
DICOMWEB_PASSWORD = ''
DICOMWEB_VERIFY_SSL = True
DICOMWEB_MAX_WORKERS = 4
