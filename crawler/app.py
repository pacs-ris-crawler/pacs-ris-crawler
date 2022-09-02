import json
import logging
import shlex
import subprocess
from datetime import datetime
import click
from flask.cli import with_appcontext

import luigi
import pandas as pd
from flask import render_template, request, Blueprint, current_app
from flask_assets import Bundle
#from crawler.tasks.ris_pacs_merge_upload import DailyUpConvertedMerged, MergePacsRis

#from crawler.query import query_day_accs

crawler_bp = Blueprint(
    "crawler_bp", __name__, template_folder="templates", static_folder="static"
)
from .flows import query_acc

@crawler_bp.cli.command('acc')
@click.argument('dicom_node')
@click.argument('acc')
@with_appcontext
def import_acc(dicom_node, acc):
    query_acc(dicom_node, acc)

crawler_bundle = {
    "crawler_js": Bundle(
        "js/jquery-3.3.1.min.js",
        "js/bootstrap.bundle.min.js",
        "js/jquery.noty.packaged.min.js",
        "js/intercooler.js",
        "js/script.js",
        filters="jsmin",
        output="gen/packed.js",
    )
}


@crawler_bp.app_template_filter("to_date")
def to_date(date_as_int):
    if date_as_int:
        return datetime.strptime(str(date_as_int), "%Y%m%d").strftime("%d.%m.%Y")
    return ""


@crawler_bp.route("/")
def main():
    luigi_scheduler = current_app.config["LUIGI_SCHEDULER"]
    return render_template(
        "index.html",
        luigi_scheduler=luigi_scheduler,
        dicom_nodes=list(current_app.config["DICOM_NODES"].keys()),
        version=current_app.config["VERSION"],
    )


@crawler_bp.route("/search")
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
                result["search"] = sorted(
                    result["search"],
                    key=lambda k: int(k["SeriesNumber"] or "0"),
                )

        return render_template(
            "result.html",
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


@crawler_bp.route("/upload", methods=["POST"])
def upload():
    data = request.get_json(force=True)
    accession_number = data.get("acc", "")
    day = data.get("day", "")
    logging.debug("Accession number to upload is: {}".format(accession_number))
    if not any([accession_number, day]):
        return "no accession number or day given", 400

    w = luigi.worker.Worker(no_install_shutdown_handler=True)
    if accession_number:
        task = DailyUpConvertedMerged({"acc": accession_number})
    else:
        task = DailyUpConvertedMerged({"day": day})
    w.add(task)
    w.run()
    if task.complete():
        return json.dumps({"status": "ok"})
    else:
        return "Task error", 400


@crawler_bp.route("/batch-upload")
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
            for i in r:
                if "AccessionNumber" in i:
                    acc = i["AccessionNumber"]
                    cmd = f"python -m tasks.ris_pacs_merge_upload DailyUpAccConvertedMerged --acc {acc} --node {dicom_node}"
                    cmds = shlex.split(cmd)
                    subprocess.run(cmds, shell=False, check=False)
        return json.dumps({"status": "ok"})


@crawler_bp.route("/debug")
def debug():
    return render_template("debug.html", version=app.config["VERSION"])


@crawler_bp.route("/acc")
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


@crawler_bp.route("/execute")
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
