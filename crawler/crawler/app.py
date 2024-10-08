import json
import logging
import shlex
import subprocess
from datetime import datetime
from pathlib import Path


import pandas as pd
from flask import Flask, render_template, request
from flask_assets import Bundle, Environment


from crawler.query import query_day_accs

app = Flask(__name__, instance_relative_config=True)
app.config.from_object("default_config")
app.config.from_pyfile("config.cfg")
version = app.config["VERSION"] = "1.3.1"

prefect_server = app.config["PREFECT_SERVER"]

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
        prefect_server=prefect_server,  # Replaced luigi_scheduler with prefect_server
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
    try:
        # Trigger the Prefect deployment or flow
        if accession_number:
            result = subprocess.run(shlex.split(f'python -m tasks.ris_pacs_merge_upload "MergePacsRis" --acc "{accession_number}" --dicom-node "{dicom_node}"'), capture_output=True)
        elif day:
            result = subprocess.run(shlex.split(f'prefect deployment run "merge-pacs-ris-flow/MergePacsRis Deployment" --params \'{{"query": {{"day": "{day}"}}}}\''), capture_output=True, text=True)
        output_path = result.stdout.decode('utf-8').strip().splitlines()[-1]

        # Verify that the output file exists
        if not Path(output_path).exists():
            return f"Output file {output_path} not found", 500
        
        # Read and load the JSON results from the output file
        with open(output_path, "r") as merged_file:
            results = json.load(merged_file)

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
            prefect_server=prefect_server,
            dicom_nodes=list(app.config["DICOM_NODES"].keys()),
            dicom_node=dicom_node,
            version=app.config["VERSION"],
            results=results,
        )
    except Exception as e:
        app.logger.error(f"Task error: {e}")
        return render_template(
            "error.html",
            accession_number=accession_number,
            day=day,
            prefect_server=prefect_server,
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

    try:
        if accession_number:
            subprocess.run(shlex.split(f'prefect deployment run "trigger-task-flow/TriggerTask Deployment" --params \'{{"acc": "{accession_number}", "dicom_node": "SECTRA"}}\''))
        else:
            subprocess.run(shlex.split(f'prefect deployment run "trigger-task-flow/TriggerTask Deployment" --params \'{{"day": "{day}"}}\''))

        return json.dumps({"status": "ok"})
    except Exception as e:
        logging.error(f"Task error: {e}")
        return "Task error", 400


@app.route("/prefetch")
def prefetch():
    accession_number = request.args.get("accession_number")
    if accession_number:
        app.logger.info(f"Cleaning data dir for acc: {accession_number}")
        files = list(Path("data").glob(f"*{accession_number}*"))
        for f in files:
            f.unlink()
        app.logger.info(f"Cleaned successfully for acc: {accession_number}")
        subprocess.run(shlex.split(f"prefect deployment run \"PrefetchTask/PrefetchTask Deployment\" --params '{{\"accession_number\": \"{accession_number}\"}}'"))
        return json.dumps({"status": "ok"})
    else:
        return json.dumps({"status": "error, no accession number given"})


@app.route("/batch-upload")
def batch():
    from_date = request.args.get("from-date", "")
    to_date = request.args.get("to-date", "")
    app.logger.debug(f"Got date params: {from_date} to {to_date}")
    accession_number = request.args.get("accession_number")
    dicom_node = request.args.get("dicom_node", "SECTRA")

    if accession_number:
        app.logger.debug(f"Running upload for acc {accession_number}")
        
        subprocess.run(shlex.split(f'prefect deployment run "trigger-task-flow/TriggerTask Deployment" --params \'{{"acc": "{accession_number}", "dicom_node": "{dicom_node}"}}\''))
        
        return json.dumps({"status": "ok"})
    else:
        if not (any([from_date, to_date])):
            return "From date or to date is missing", 400
        
        from_date_as_date = datetime.strptime(from_date, "%Y-%m-%d")
        to_date_as_date = datetime.strptime(to_date, "%Y-%m-%d")
        range = pd.date_range(from_date_as_date, to_date_as_date)
        
        for day in range:
            r = query_day_accs(app.config["DICOM_NODES"][dicom_node], day)
            app.logger.info(f"Got {len(r)} accession numbers for day: {day}")
            for i in r:
                if "AccessionNumber" in i:
                    acc = i["AccessionNumber"]
                    subprocess.run(shlex.split(f'prefect deployment run "trigger-task-flow/TriggerTask Deployment" --params \'{{"acc": "{acc}", "dicom_node": "{dicom_node}"}}\''))
        
        return json.dumps({"status": "ok"})


@app.route("/debug")
def debug():
    return render_template("debug.html", version=app.config["VERSION"])


@app.route("/acc")
def acc():
    accession_number = request.args.get("acc")
    subprocess.run(shlex.split(f"prefect deployment run \"AccessionTask/AccessionTask Deployment\" --params '{{\"accession_number\": \"{accession_number}\"}}'"))

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
