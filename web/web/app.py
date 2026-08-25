import sys
from datetime import datetime
from pathlib import Path
from string import Template

from flask import Flask
from flask_assets import Bundle, Environment

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from common.text import fix_utf8_mojibake

app = Flask(__name__, instance_relative_config=True)
app.config.from_object("web.default_config")
app.config.from_pyfile("config.cfg", silent=True)

# Exposing constants to use

VERSION = app.config["VERSION"] = "1.3.1"
RESULT_LIMIT = app.config["RESULT_LIMIT"]

REPORT_SHOW_URL = app.config["REPORT_SHOW_URL"]

SHOW_DOWNLOAD_OPTIONS = app.config["SHOW_DOWNLOAD_OPTIONS"]
SHOW_TRANSFER_TARGETS = app.config["SHOW_TRANSFER_TARGETS"]
SHOW_LLM_ASSISTED_FILTERING = app.config["SHOW_LLM_ASSISTED_FILTERING"]
TRANSFER_TARGETS = app.config["TRANSFER_TARGETS"]

RECEIVER_URL = app.config["RECEIVER_URL"]
RECEIVER_DASHBOARD_URL = app.config["RECEIVER_DASHBOARD_URL"]
RECEIVER_DOWNLOAD_URL = app.config["RECEIVER_DOWNLOAD_URL"]
RECEIVER_TRANSFER_URL = app.config["RECEIVER_TRANSFER_URL"]
SECTRA_UNIVIEW = app.config["SECTRA_UNIVIEW"]


@app.template_filter("fix_mojibake")
def fix_mojibake_filter(value):
    if value is None:
        return ""
    if not isinstance(value, str):
        return value
    return fix_utf8_mojibake(value)


@app.template_filter("to_date")
def to_date(date_as_int):
    if date_as_int:
        return datetime.strptime(str(date_as_int), "%Y%m%d").strftime("%d.%m.%Y")
    return ""


@app.template_filter("swiss_number")
def swiss_number(value):
    """Format integer with Swiss thousands separator (apostrophe), e.g. 3000 -> 3'000."""
    try:
        n = int(value)
    except (TypeError, ValueError):
        return value
    sign = "-" if n < 0 else ""
    s = str(abs(n))
    if len(s) <= 3:
        return sign + s
    parts = []
    while len(s) > 3:
        parts.insert(0, s[-3:])
        s = s[:-3]
    if s:
        parts.insert(0, s)
    return sign + "'".join(parts)


@app.template_filter("series_num_short")
def series_num_short(value, max_len=4):
    """Display at most the first few digits of a series number (full value in title)."""
    text = str(value).strip() if value is not None else ""
    if len(text) <= max_len:
        return text
    return text[:max_len]


@app.context_processor
def inject_ui_flags():
    return dict(
        show_llm_assisted_filtering=SHOW_LLM_ASSISTED_FILTERING,
    )


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
    "js/theme.js",
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
