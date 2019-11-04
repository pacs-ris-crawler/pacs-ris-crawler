import json
import logging
import os
import time
from datetime import datetime, timedelta
from pathlib import Path

import rq_dashboard
from flask import Flask, jsonify, render_template, request
from flask_assets import Bundle, Environment
from mova.config import dcmtk_config, pacs_config
from mova.job import download_series, transfer_series

app = Flask(__name__, instance_relative_config=True)
app.config.from_object("mova.default_config")
app.config.from_pyfile("config.cfg")
version = app.config["VERSION"] = "1.0.1"

app.config.from_object(rq_dashboard.default_settings)
app.register_blueprint(rq_dashboard.blueprint, url_prefix="/rq")


assets = Environment(app)
js = Bundle(
    "js/jquery-3.3.1.min.js",
    "js/bootstrap.bundle.min.js",
    "js/jquery.noty.packaged.min.js",
    "js/script.js",
    filters="jsmin",
    output="gen/packed.js",
)
assets.register("js_all", js)


@app.route("/")
def main():
    files = list(Path("jobs").glob("*.json"))
    return render_template("index.html", version=version, files=files)


@app.route("/download", methods=["POST"])
def download():
    """ Post to download series of images. """
    app.logger.info("download called")
    data = request.get_json(force=True)
    timestamp = int(time.time())
    with open(f"jobs/{timestamp}_download.json", "w") as f:
        json.dump(data, f)
    series_list = data.get("data")
    dir_name = data.get("dir")
    length = download_series(app.config, series_list, dir_name)
    return json.dumps({"status": "OK", "series_length": length})


@app.route("/transfer", methods=["POST"])
def transfer():
    """ Post to transfer series of images to another PACS node. """
    data = request.get_json(force=True)
    timestamp = int(time.time())
    with open(f"jobs/{timestamp}_transfer.json", "w") as f:
        json.dump(data, f)
    target = data.get("target", "")
    series_list = data.get("data", "")
    app.logger.info("transfer called and sending to %s", target)
    length = transfer_series(app.config, series_list, target)
    return json.dumps({"status": "OK", "series_length": length})
