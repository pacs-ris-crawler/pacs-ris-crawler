import json
import logging
import subprocess
from datetime import datetime
from pathlib import Path

import pandas as pd
import rq_dashboard
import structlog
from flask import Flask, render_template, request
from flask_assets import Bundle, Environment
from redis import Redis
from rq import Queue
from crawler.accession import prefetch_task
from crawler.ris_pacs_merge_upload import index_acc

from crawler.query import query_day_accs

# Configure logging
logging.getLogger("werkzeug").setLevel(logging.WARNING)
logging.getLogger("rq.dashboard.web").setLevel(logging.WARNING)
logger = structlog.get_logger()


def create_app(test_config=None):
    app = Flask(__name__, instance_relative_config=True)

    # Load default configuration
    app.config.from_object("default_config")

    if test_config is None:
        # Load instance config when not testing
        app.config.from_pyfile("config.cfg", silent=True)
    else:
        # Load test config if passed in
        app.config.update(test_config)

    # Set version
    app.config["VERSION"] = "1.3.1"

    # Configure RQ Dashboard
    app.config.from_object(rq_dashboard.default_settings)
    app.config["RQ_DASHBOARD_REDIS_URL"] = "redis://127.0.0.1:6379"
    rq_dashboard.web.setup_rq_connection(app)
    app.register_blueprint(rq_dashboard.blueprint, url_prefix="/rq")

    # Initialize Redis queues
    redis_conn = Redis()
    app.queue = Queue("index", connection=redis_conn)
    app.queue_prefetch = Queue("prefetch", connection=redis_conn)

    # Configure assets
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

    # Configure logging for production
    if __name__ != "__main__":
        gunicorn_logger = logging.getLogger("gunicorn.error")
        app.logger.handlers = gunicorn_logger.handlers
        app.logger.setLevel(gunicorn_logger.level)

    @app.template_filter("to_date")
    def to_date(date_as_int):
        if date_as_int:
            return datetime.strptime(str(date_as_int), "%Y%m%d").strftime("%d.%m.%Y")
        return ""

    @app.route("/")
    def main():
        return render_template(
            "index.html",
            dicom_nodes=list(app.config["DICOM_NODES"].keys()),
            version=app.config["VERSION"],
        )

    @app.route("/search")
    def search():
        accession_number = request.args.get("accession_number", "")
        if not accession_number:
            return "no accession number given", 400
        try:
            result = index_acc(accession_number)

            return render_template(
                "result.html",
                accession_number=accession_number,
                version=app.config["VERSION"],
                results=result,
            )
        except Exception as e:
            logger.error("search_error", error=str(e), exc_info=True)
            return render_template(
                "error.html",
                accession_number=accession_number,
                dicom_nodes=list(app.config["DICOM_NODES"].keys()),
                version=app.config["VERSION"],
                results={},
            )

    @app.route("/upload", methods=["POST"])
    def upload():
        data = request.get_json(force=True)
        accession_number = data.get("acc", "")

        logger.debug("upload_request", accession_number=accession_number)
        if not accession_number:
            return "no accession number given", 400

        try:
            app.queue.enqueue(index_acc, accession_number)
            return json.dumps({"status": "ok"})
        except Exception as e:
            logger.error("upload_error", error=str(e))
            return "Task error", 400

    @app.route("/prefetch")
    def prefetch():
        accession_number = request.args.get("accession_number")
        if accession_number:
            logger.info("cleaning_data_directory", accession_number=accession_number)
            files = list(Path("data").glob(f"*{accession_number}*"))
            for f in files:
                f.unlink()
            logger.info("cleaned_successfully", accession_number=accession_number)
            app.queue_prefetch.enqueue(
                prefetch_task, accession_number, job_timeout="12m"
            )
            return json.dumps({"status": "ok"})
        else:
            return json.dumps({"status": "error, no accession number given"})

    @app.route("/batch-upload")
    def batch():
        from_date = request.args.get("from-date", "")
        to_date = request.args.get("to-date", "")
        logger.info("batch_upload_request", from_date=from_date, to_date=to_date)
        accession_number = request.args.get("accession_number")
        dicom_node = request.args.get("dicom_node", "SECTRA")

        if accession_number:
            logger.debug("running_upload", accession_number=accession_number)
            app.queue.enqueue(index_acc, accession_number)
            return json.dumps({"status": "ok"})
        else:
            if not (any([from_date, to_date])):
                return "From date or to date is missing", 400

            from_date_as_date = datetime.strptime(from_date, "%Y-%m-%d")
            to_date_as_date = datetime.strptime(to_date, "%Y-%m-%d")
            range = pd.date_range(from_date_as_date, to_date_as_date)

            for day in range:
                r = query_day_accs(app.config["DICOM_NODES"][dicom_node], day)
                logger.info("got_accession_numbers", day=str(day.date()), count=len(r))
                for i in r:
                    if "AccessionNumber" in i:
                        acc = i["AccessionNumber"]
                        app.queue.enqueue(index_acc, acc)

            return json.dumps({"status": "ok"})

    @app.route("/debug")
    def debug():
        return render_template("debug.html", version=app.config["VERSION"])

    @app.route("/acc")
    def acc():
        accession_number = request.args.get("acc")
        app.queue.enqueue(index_acc, accession_number)
        return render_template(
            "execute-result.html",
            stdout="Execution started successfully",
            stderr="",
        )

    @app.route("/execute")
    def execute():
        command = request.args.get("command")
        result = subprocess.run(
            command, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE
        )
        return render_template(
            "execute-result.html",
            stdout=result.stdout.decode("latin-1"),
            stderr=result.stderr.decode("latin-1"),
        )

    return app
