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
