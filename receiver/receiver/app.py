import json
import logging
import os
import time
from datetime import datetime
from pathlib import Path

import rq_dashboard
from flask import Flask, render_template, request
from flask_assets import Bundle, Environment

from receiver.job import download_series, transfer_series

app = Flask(__name__, instance_relative_config=True)
app.config.from_object("receiver.default_config")
app.config.from_pyfile("config.cfg")
version = app.config["VERSION"] = "1.3.1"

app.config.from_object(rq_dashboard.default_settings)
app.register_blueprint(rq_dashboard.blueprint, url_prefix="/rq")


assets = Environment(app)
js = Bundle(
    "js/jquery-3.3.1.min.js",
    "js/bootstrap.bundle.min.js",
    "js/jquery.noty.packaged.min.js",
    "js/intercooler.js",
    "js/script.js",
    filters="jsmin",
    output="gen/packed.js",
)
assets.register("js_all", js)

if not os.path.exists("jobs"):
    os.makedirs("jobs")


if __name__ != "__main__":
    gunicorn_logger = logging.getLogger("gunicorn.error")
    app.logger.handlers = gunicorn_logger.handlers
    app.logger.setLevel(gunicorn_logger.level)


@app.template_filter("to_date")
def to_date(timestamp):
    if timestamp:
        return datetime.fromtimestamp(int(timestamp)).strftime("%d.%m.%Y %H:%M:%S")
    return ""


@app.route("/")
def main():
    files = [i.stem for i in Path("jobs").glob("*.json")]
    return render_template("index.html", version=version, files=files)


@app.route("/show")
def show():
    filename = request.args.get("filename")
    with app.open_resource(f"../jobs/{filename}.json") as f:
        content = json.load(f)
    return render_template(
        "show.html",
        version=version,
        filename=filename,
        content=json.dumps(content, indent=4),
    )


@app.route("/resend")
def resend():
    filename = request.args.get("filename")
    parts = filename.split("_")
    with app.open_resource(f"../jobs/{filename}.json") as f:
        data = json.load(f)
    if parts[1] == "download":
        series_list = data.get("data")
        dir_name = data.get("dir")
        app.logger.info("download called and saving to %s", dir_name)
        length = download_series(app.config, series_list, dir_name)
        return render_template("success.html")
    elif parts[1] == "transfer":
        target = data.get("target", "")
        series_list = data.get("data", "")
        app.logger.info("transfer called and sending to %s", target)
        length, _ = transfer_series(app.config, series_list, target)
        return render_template("success.html")
    else:
        return render_template("success.html")


@app.route("/download", methods=["POST"])
def download():
    """Post to download series of images."""
    app.logger.info("Download request received")
    data = request.get_json(force=True)
    timestamp = int(time.time())
    with open(f"jobs/{timestamp}_download.json", "w") as f:
        json.dump(data, f)
    series_list = data.get("data")
    dir_name = data.get("dir")
    image_type = data.get("image_type", "dicom")
    app.logger.info("download called and saving to %s", dir_name)
    length = download_series(app.config, series_list, dir_name, image_type)
    return json.dumps({"status": "OK", "series_length": length})


@app.route("/transfer", methods=["POST"])
def transfer():
    """Post to transfer series of images to another PACS node."""
    app.logger.info("Transfer request received")
    data = request.get_json(force=True)
    timestamp = int(time.time())
    with open(f"jobs/{timestamp}_transfer.json", "w") as f:
        json.dump(data, f)
    target = data.get("target", "")
    series_list = data.get("data", "")
    app.logger.info("transfer called and sending to %s", target)
    length, command = transfer_series(app.config, series_list, target)
    app.logger.info("command was:\n {command}")
    return json.dumps({"status": "OK", "series_length": length})
