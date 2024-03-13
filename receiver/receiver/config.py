"""All configuration options
can be accessed from here.
"""

from collections import namedtuple
from flask import Flask

PacsConfig = namedtuple(
    "PacsConfig",
    ["ae_title", "ae_called", "peer_address", "peer_port", "incoming_port"],
)

DcmtkConfig = namedtuple("DcmtkConfig", ["dcmtk_bin", "dcmin"])


def new_pacs():
    """Returns the new pacs configuration parameters."""
    app = Flask(__name__)
    app.config.from_pyfile(filename="../instance/config.cfg")
    node = app.config["DICOM_NODES"]["SECTRA"]
    return f'-aec {node["AE_CALLED"]} {node["PEER_ADDRESS"]} {node["PEER_PORT"]} -aet {node["AE_TITLE"]} +P {node["INCOMING_PORT"]}'


def transfer_pacs():
    """Returns the new pacs configuration parameters."""
    app = Flask(__name__)
    app.config.from_pyfile(filename="../instance/config.cfg")
    node = app.config["TRANSFER_NODE"]
    return f'-aec {node["AE_CALLED"]} {node["PEER_ADDRESS"]} {node["PEER_PORT"]} -aet {node["AE_TITLE"]} +P {node["INCOMING_PORT"]}'


def pacs_config(config):
    """Returns the pacs configuration parameters."""
    return PacsConfig(
        config["AE_TITLE"],
        config["AE_CALLED"],
        config["PEER_ADDRESS"],
        config["PEER_PORT"],
        config["INCOMING_PORT"],
    )


def dcmtk_config(config):
    """Returns the dcmtk configuration."""
    return DcmtkConfig(config["DCMTK_BIN"], config["DCMIN"])
