""" All configuration options
    can be accessed from here.
"""
from collections import namedtuple

PacsConfig = namedtuple(
    'PacsConfig',
    ['ae_title', 'ae_called', 'peer_address', 'peer_port', 'incoming_port'])

DcmtkConfig = namedtuple('DcmtkConfig', ['dcmtk_bin', 'dcmin'])


def pacs_config(config):
    """ Returns the pacs configuration parameters. """
    return PacsConfig(config['AE_TITLE'], config['AE_CALLED'],
                      config['PEER_ADDRESS'], config['PEER_PORT'],
                      config['INCOMING_PORT'])


def dcmtk_config(config):
    """ Returns the dcmtk configuration. """
    return DcmtkConfig(config['DCMTK_BIN'], config['DCMIN'])
