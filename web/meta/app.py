from datetime import datetime
from string import Template

from flask import Flask, g
from flask_assets import Bundle, Environment

from meta.config import dcmtk_config, pacs_config

app = Flask(__name__, instance_relative_config=True)
app.config.from_object("meta.default_config")
app.config.from_pyfile("config.cfg", silent=True)

# Exposing constants to use

VERSION = app.config["VERSION"] = "2.8.1"
RESULT_LIMIT = app.config["RESULT_LIMIT"]

REPORT_SHOW_URL = app.config["REPORT_SHOW_URL"]

SHOW_DOWNLOAD_OPTIONS = app.config["SHOW_DOWNLOAD_OPTIONS"]
SHOW_TRANSFER_TARGETS = app.config["SHOW_TRANSFER_TARGETS"]
TRANSFER_TARGETS = app.config["TRANSFER_TARGETS"]

MOVA_DASHBOARD_URL = app.config["MOVA_DASHBOARD_URL"]
MOVA_DOWNLOAD_URL = app.config["MOVA_DOWNLOAD_URL"]
MOVA_TRANSFER_URL = app.config["MOVA_TRANSFER_URL"]
ZFP_VIEWER = app.config["ZFP_VIEWER"]

@app.template_filter("to_date")
def to_date(date_as_int):
    if date_as_int:
        return datetime.strptime(str(date_as_int), "%Y%m%d").strftime("%d.%m.%Y")
    else:
        return ""


@app.template_filter("zfp_url")
def create_zfp_url(accession_number):
     s = Template(ZFP_VIEWER)
     x = s.substitute(accession_number=accession_number)
     return x

# JS Assets part
assets = Environment(app)
js = Bundle(
    "js/jquery-3.1.0.min.js",
    "js/tether.min.js",
    "js/popper.min.js",
    "js/bootstrap.min.js",
    "js/moment.min.js",
    "js/pikaday.js",
    "js/pikaday.jquery.js",
    "js/jquery.noty.packaged.min.js",
    "js/jszip.min.js",
    "js/FileSaver.js",
    "js/script.js",
    filters="jsmin",
    output="gen/packed.js",
)
assets.register("js_all", js)

import meta.views
