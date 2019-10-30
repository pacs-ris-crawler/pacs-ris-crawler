import unittest
from mova.job import base_command, transfer_command
from mova.config import dcmtk_config, pacs_config

DCMTK_CONFIG = dcmtk_config({
    'DCMTK_BIN': '/usr/local/bin',
    'DCMIN': '/opt/dcm.in'
})

PACS_CONFIG = pacs_config({
    'AE_TITLE': 'AE_TITLE',
    'AE_CALLED': 'AE_CALLED',
    'PEER_ADDRESS': '127.0.0.1',
    'PEER_PORT': 104,
    'INCOMING_PORT': 11110
})


class TestCommand(unittest.TestCase):
    def test_base_command(self):
        expected = '/usr/local/bin/movescu -v -S -k QueryRetrieveLevel=SERIES -aet AE_TITLE -aec AE_CALLED 127.0.0.1 104 +P 11110'
        self.assertEqual(expected, base_command(DCMTK_CONFIG, PACS_CONFIG))

    def test_tranfer(self):
        expected = '/usr/local/bin/movescu -v -S -aem syngo -aet AE_TITLE -aec AE_CALLED 127.0.0.1 104 -k StudyInstanceUID=12345 -k SeriesInstanceUID=999 /opt/dcm.in'
        self.assertEqual(expected,
                         transfer_command(DCMTK_CONFIG, PACS_CONFIG, 'syngo',
                                          '12345', '999'))
