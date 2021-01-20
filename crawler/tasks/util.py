from flask import Flask
from luigi.parameter import UnknownParameterException


def load_config():
    app = Flask(__name__)
    app.config.from_pyfile(filename="../instance/config.cfg")
    return app.config


def dict_to_str(parameter_dict):
    return "".join(["{}_{}".format(k, v) for k, v in parameter_dict.items()])