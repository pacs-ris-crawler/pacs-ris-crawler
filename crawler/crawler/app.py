import json
import logging
import shlex
import subprocess
from datetime import datetime

import luigi
import pandas as pd
from flask import Flask, render_template, request
from flask_assets import Bundle, Environment
from tasks.ris_pacs_merge_upload import DailyUpConvertedMerged, MergePacsRis
from pathlib import Path
from crawler.query import query_day_accs

app = Flask(__name__, instance_relative_config=True)
app.config.from_object("default_config")
app.config.from_pyfile("config.cfg")
version = app.config["VERSION"] = "1.3.1"

luigi_scheduler = app.config["LUIGI_SCHEDULER"]

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
        luigi_scheduler=luigi_scheduler,
        dicom_nodes=list(app.config["DICOM_NODES"].keys()),
        version=app.config["VERSION"],
    )


@app.route("/search")
def search():
    accession_number = request.args.get("accession_number", "")
    dicom_node = request.args.get("dicom_node", "")
    day = request.args.get("day", "")
    if not any([accession_number, day]):
        return "no accession number or day given", 400
    w = luigi.worker.Worker(no_install_shutdown_handler=True)
    if accession_number:
        task = MergePacsRis({"acc": accession_number, "dicom_node": dicom_node})
    elif day:
        task = MergePacsRis({"day": day})
    w.add(task)
    w.run()
    if task.complete():
        with task.output().open("r") as r:
            results = json.load(r)
            for result in results:
                result["_childDocuments_"] = sorted(
                    result["_childDocuments_"],
                    key=lambda k: int(k["SeriesNumber"] or "0"),
                )
        command = ""
        if Path(f"data/{accession_number}_command.txt").exists():        
            with open(f"data/{accession_number}_command.txt", "r") as f:
                command = " ".join(y.strip() for y in f.read().splitlines())
        return render_template(
            "result.html",
            command=command,
            accession_number=accession_number,
            day=day,
            luigi_scheduler=luigi_scheduler,
            dicom_nodes=list(app.config["DICOM_NODES"].keys()),
            dicom_node=dicom_node,
            version=app.config["VERSION"],
            results=results,
        )
    else:
        return render_template(
            "error.html",
            accession_number=accession_number,
            day=day,
            luigi_scheduler=luigi_scheduler,
            dicom_nodes=list(app.config["DICOM_NODES"].keys()),
            version=app.config["VERSION"],
            results={},
        )


@app.route("/upload", methods=["POST"])
def upload():
    data = request.get_json(force=True)
    accession_number = data.get("acc", "")
    day = data.get("day", "")
    logging.debug("Accession number to upload is: {}".format(accession_number))
    if not any([accession_number, day]):
        return "no accession number or day given", 400

    w = luigi.worker.Worker(no_install_shutdown_handler=True)
    if accession_number:
        task = DailyUpConvertedMerged({"acc": accession_number, "dicom_node": "SECTRA"})
    else:
        task = DailyUpConvertedMerged({"day": day})
    w.add(task)
    w.run()
    if task.complete():
        return json.dumps({"status": "ok"})
    else:
        return "Task error", 400


@app.route("/prefetch")
def prefetch():
    accession_number = request.args.get("accession_number")
    if accession_number:
        logging.info(f"cleaning data dir for acc: {accession_number}")
        files = list(Path("data").glob(f"*{accession_number}*"))
        print(f"Found {len(files)} for cleaning")
        for f in files:
            f.unlink()
        logging.info(f"cleaned successfull for acc: {accession_number}")
        logging.info(f"Running prefetch for acc {accession_number}")
        cmd = f'python -m tasks.accession PrefetchTask --accession-number {accession_number}'
        cmds = shlex.split(cmd)
        r = subprocess.run(cmds, shell=False, check=False)
        print(r)
        return json.dumps({"status": "ok"})
    else:
        return json.dumps({"status": "error, no accession number given"})


@app.route("/batch-upload")
def batch():
    from_date = request.args.get("from-date", "")
    to_date = request.args.get("to-date", "")
    accession_number = request.args.get("accession_number")
    dicom_node = request.args.get("dicom_node")
    if accession_number:
        logging.debug(f"Running upload for acc {accession_number}")
        cmd = f'python -m tasks.ris_pacs_merge_upload DailyUpConvertedMerged --query \'{{"acc": "{accession_number}", "dicom_node": "{dicom_node}"}}\''
        cmds = shlex.split(cmd)
        subprocess.run(cmds, shell=False, check=False)
        return json.dumps({"status": "ok"})
    else:
        if not (any([from_date, to_date])):
            return "From date or to date is missing", 400
        from_date_as_date = datetime.strptime(from_date, "%Y-%m-%d")
        to_date_as_date = datetime.strptime(to_date, "%Y-%m-%d")
        range = pd.date_range(from_date_as_date, to_date_as_date)
        for day in range:
            r = query_day_accs(app.config["DICOM_NODES"][dicom_node], day)
            logging.info(f"Got {len(r)} accession numbers for day: {day}")
            for i in r:
                if "AccessionNumber" in i:
                    acc = i["AccessionNumber"] 
                    cmd = f'python -m tasks.ris_pacs_merge_upload DailyUpAccConvertedMerged --acc {acc} --node {dicom_node}'
                    cmds = shlex.split(cmd)
                    subprocess.run(cmds, shell=False, check=False)
        return json.dumps({"status": "ok"})


@app.route("/debug")
def debug():
    return render_template("debug.html", version=app.config["VERSION"])


@app.route("/acc")
def acc():
    acc = request.args.get("acc")
    cmd = "python -m tasks.accession AccessionTask --accession-number  %s" % acc

    result = subprocess.run(
        cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE
    )
    return render_template(
        "execute-result.html",
        stdout=result.stdout.decode("latin-1"),
        stderr=result.stderr.decode("latin-1"),
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
