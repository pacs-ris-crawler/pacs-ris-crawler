import os

from flask import Flask

from crawler import config
from crawler.config import get_dcmtk_bin_path, pacs_settings


def test_simple():
    app = Flask(__name__)
    app.config.from_pyfile("config.cfg")
    settings = config.pacs_settings(app.config)
    assert "-aec AE_CALLED 127.0.0.1 104 -aet AE_TITLE" == settings


def test_dcmtk_bin_path():
    app = Flask(__name__)
    app.config.from_pyfile("config.cfg")
    dcmtk_bin = get_dcmtk_bin_path(app.config)
    assert dcmtk_bin == "/usr/bin"


def test_dcmtk_bin_path_default():
    # Test default value when DCMTK_BIN is not set
    config_dict = {}
    dcmtk_bin = get_dcmtk_bin_path(config_dict)
    assert dcmtk_bin == "/usr/bin"


def test_modalities():
    app = Flask(__name__)
    app.config.from_pyfile("config.cfg")
    assert len(app.config["MODALITIES"]) == 18


def test_series_limit():
    app = Flask(__name__)
    app.config.from_pyfile("config.cfg")
    assert app.config["SERIES_LIMIT"] == 499
