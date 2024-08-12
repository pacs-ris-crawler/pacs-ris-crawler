from datetime import datetime

from flask import Flask


def load_config():
    app = Flask(__name__)
    app.config.from_pyfile(filename="../instance/config.cfg")
    return app.config


def load_dicom_config(dicom_node):
    app = Flask(__name__)
    app.config.from_pyfile(filename="../instance/config.cfg")
    node = app.config["DICOM_NODES"][dicom_node]
    return node


def load_prefetch_node():
    app = Flask(__name__)
    app.config.from_pyfile(filename="../instance/config.cfg")
    node = app.config["PREFETCH_NODE"]["SECTRA_PREFETCH"]
    return node


def dict_to_str(parameter_dict):
    return "".join(["{}_{}".format(k, v) for k, v in parameter_dict.items()])
