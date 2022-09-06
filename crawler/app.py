import json
import logging
import shlex
import subprocess
from datetime import datetime

import click
import luigi
import pandas as pd
from flask import Blueprint, current_app, render_template, request
from flask.cli import with_appcontext
from flask_assets import Bundle

# from crawler.tasks.ris_pacs_merge_upload import DailyUpConvertedMerged, MergePacsRis

# from crawler.query import query_day_accs

crawler_bp = Blueprint(
    "crawler_bp", __name__, template_folder="templates", static_folder="static"
)
from .flows import query_and_upload_acc, upload_acc, query_acc


@crawler_bp.cli.command("acc")
@click.argument("dicom_node")
@click.argument("acc")
@with_appcontext
def import_acc(dicom_node, acc):
    upload_acc(dicom_node, acc)


crawler_bundle = Bundle(
    "crawler_bp/js/jquery-3.3.1.min.js",
    "crawler_bp/js/bootstrap.bundle.min.js",
    "crawler_bp/js/jquery.noty.packaged.min.js",
    "crawler_bp/js/intercooler.js",
    "crawler_bp/js/script.js",
    filters="jsmin",
    output="crawler_bp/gen/crawler_packed.js",
)


@crawler_bp.app_template_filter("to_date")
def to_date(date_as_int):
    if date_as_int:
        return datetime.strptime(str(date_as_int), "%Y%m%d").strftime("%d.%m.%Y")
    return ""


@crawler_bp.route("/")
def main():
    prefect_orion = current_app.config["PREFECT_ORION_URL"]
    return render_template(
        "crawler/index.html",
        prefect_orion=prefect_orion,
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
    if accession_number:
        result = query_acc(dicom_node, accession_number)
    elif day:
        task = MergePacsRis({"day": day})

    print(result)
    return render_template(
        "crawler/result.html",
        accession_number=accession_number,
        day=day,
        dicom_nodes=list(current_app.config["DICOM_NODES"].keys()),
        dicom_node=dicom_node,
        version=current_app.config["VERSION"],
        results=result,
    )


@crawler_bp.route("/upload", methods=["POST"])
def upload():
    """Receiving data from the client is like this:
    ```
    {
        'acc': 12233,
        'dicom_node': 'node'
    }
    ```
    Returns:
        _type_: _description_
    """
    data = request.get_json(force=True)
    accession_number = data.get("acc", "")
    dicom_node = data.get("dicom_node", "")
    logging.debug(
        f"Accession number to upload is: {accession_number} from dicom node: {dicom_node}"
    )
    if not any([accession_number, dicom_node]):
        return "no accession number or dicom node given", 400

    if accession_number:
        res = query_and_upload_acc(dicom_node, accession_number)
        if res:
            return json.dumps({'success':True}), 200, {'ContentType':'application/json'} 

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
