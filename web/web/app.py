from datetime import datetime
from string import Template

from flask import Flask
from flask_assets import Bundle, Environment

app = Flask(__name__, instance_relative_config=True)
app.config.from_object("web.default_config")
app.config.from_pyfile("config.cfg", silent=True)

# Exposing constants to use

VERSION = app.config["VERSION"] = "1.3.1"
RESULT_LIMIT = app.config["RESULT_LIMIT"]

REPORT_SHOW_URL = app.config["REPORT_SHOW_URL"]

SHOW_DOWNLOAD_OPTIONS = app.config["SHOW_DOWNLOAD_OPTIONS"]
SHOW_TRANSFER_TARGETS = app.config["SHOW_TRANSFER_TARGETS"]
TRANSFER_TARGETS = app.config["TRANSFER_TARGETS"]

RECEIVER_URL = app.config["RECEIVER_URL"]
RECEIVER_DASHBOARD_URL = app.config["RECEIVER_DASHBOARD_URL"]
RECEIVER_DOWNLOAD_URL = app.config["RECEIVER_DOWNLOAD_URL"]
RECEIVER_TRANSFER_URL = app.config["RECEIVER_TRANSFER_URL"]
SECTRA_UNIVIEW = app.config["SECTRA_UNIVIEW"]


@app.template_filter("to_date")
def to_date(date_as_int):
    if date_as_int:
        return datetime.strptime(str(date_as_int), "%Y%m%d").strftime("%d.%m.%Y")
    return ""


@app.context_processor
def sectra_uniview_url():
    def _sectra_uniview_url(patid, accession_number):
        output_string = patid
        if patid.startswith("USB"):
            output_string = patid[3:]
        elif patid.startswith("FPS"):
            output_string = patid[3:]
        elif patid.startswith("UKBB"):
            output_string = patid[3:]
        return SECTRA_UNIVIEW.format(output_string,accession_number)
    return dict(sectra_uniview_url=_sectra_uniview_url)

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
    "js/intercooler.js",
    "js/script.js",
    filters="jsmin",
    output="gen/packed.js",
)
assets.register("js_all", js)

import web.views
