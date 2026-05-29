import json
import logging
import sys
from datetime import datetime
from pathlib import Path

import rq_dashboard

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from common.rq_dashboard_custom import patch_rq_dashboard
from flask import Flask, render_template, request

from receiver.job import download_series, transfer_series, download_series_debug
from receiver.dicomweb import (
    download_series_dicomweb,
    download_series_debug_dicomweb,
    transfer_series_dicomweb,
)
from receiver.executor import run

app = Flask(__name__, instance_relative_config=True)
app.config.from_object("receiver.default_config")
app.config.from_pyfile("config.cfg")
version = app.config["VERSION"] = "1.3.1"

app.config.from_object(rq_dashboard.default_settings)
app.config["RQ_DASHBOARD_REDIS_URL"] = "redis://127.0.0.1:6379"
rq_dashboard.web.setup_rq_connection(app)
patch_rq_dashboard()
app.register_blueprint(rq_dashboard.blueprint, url_prefix="/rq")


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
    return render_template("index.html", version=version)


@app.route("/download_debug", methods=["POST"])
def download_debug():
    """Post to download a single series of images for debugging."""
    app.logger.info("Debug download request received")
    study_uid = request.form.get("study_uid")
    series_uid = request.form.get("series_uid")
    download_folder = request.form.get("download_folder")

    method = app.config.get("RETRIEVE_METHOD", "movescu")
    try:
        if method == "dicomweb":
            code, output = download_series_debug_dicomweb(
                app.config, study_uid, series_uid, download_folder,
            )
        else:
            cmd = download_series_debug(app.config, study_uid, series_uid, download_folder)
            code, output = run(cmd)
            app.logger.info("Running command: %s", cmd)
    except ValueError as exc:
        app.logger.error("Debug download configuration error: %s", exc)
        code, output = 1, str(exc)

    app.logger.info("Output: %s", output)
    app.logger.info("Code: %s", code)

    return render_template("download_debug.html", output=output, code=code)


@app.route("/download", methods=["POST"])
def download():
    """Post to download series of images."""
    app.logger.info("Download request received")
    data = request.get_json(force=True)
    series_list = data.get("data")
    dir_name = data.get("dir")
    image_type = data.get("image_type", "dicom")
    queue_prio = data.get("queue_prio", "queue-medium")
    app.logger.info("download called and saving to %s", dir_name)
    method = app.config.get("RETRIEVE_METHOD", "movescu")
    try:
        if method == "dicomweb":
            length = download_series_dicomweb(
                app.config, series_list, dir_name, image_type, queue_prio,
            )
        else:
            length = download_series(
                app.config, series_list, dir_name, image_type, queue_prio,
            )
    except ValueError as exc:
        app.logger.error("Download configuration error: %s", exc)
        return json.dumps({"status": "error", "message": str(exc)}), 400
    return json.dumps({"status": "OK", "series_length": length})


@app.route("/transfer", methods=["POST"])
def transfer():
    """Post to transfer series of images to another PACS node."""
    app.logger.info("Transfer request received")
    data = request.get_json(force=True)
    target = data.get("target", "")
    series_list = data.get("data", "")
    app.logger.info("transfer called and sending to %s", target)
    method = app.config.get("RETRIEVE_METHOD", "movescu")
    if method == "dicomweb":
        transfer_series_dicomweb(app.config, target, series_list)
    else:
        length, command = transfer_series(app.config, target, series_list)
        app.logger.info("command was:\n %s", command)
        return json.dumps({"status": "OK", "series_length": length})
