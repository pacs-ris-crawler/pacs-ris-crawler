import base64
import io
import json
import logging
import os
from io import BytesIO

import july
import matplotlib

matplotlib.use("Agg")
import pandas as pd
import requests
from flask import render_template, request, send_file
from matplotlib.figure import Figure
from requests import RequestException, get, post

from web.app import (RECEIVER_DASHBOARD_URL, RECEIVER_DOWNLOAD_URL,
                     RECEIVER_TRANSFER_URL, RECEIVER_URL, REPORT_SHOW_URL,
                     RESULT_LIMIT, SHOW_DOWNLOAD_OPTIONS,
                     SHOW_TRANSFER_TARGETS, TRANSFER_TARGETS, VERSION,
                     SECTRA_UNIVIEW, app)
from web.convert import convert
from web.paging import calc
from web.query import query_body, query_indexed_dates
from web.query_all import query_all
from web.solr import solr_url
from web.statistics import calculate
from web.terms import get_terms_data

if __name__ != "__main__":
    gunicorn_logger = logging.getLogger("gunicorn.error")
    app.logger.handlers = gunicorn_logger.handlers
    app.logger.setLevel(gunicorn_logger.level)


@app.route("/")
def main():
    """Renders the initial page."""
    url = query_indexed_dates(solr_url(app.config))
    try:
        response = get(url)
    except RequestException:
        return render_template(
            "search.html",
            params={},
            error="No response from Solr, is it running?",
            trace=solr_url(app.config),
        )
    stats = response.json()["stats"]
    indexed_start_date = stats["stats_fields"]["StudyDate"]["min"]
    indexed_end_date = stats["stats_fields"]["StudyDate"]["max"]

    return render_template(
        "search.html",
        version=VERSION,
        page=0,
        offset=0,
        params={"RisReport": "*"},
        indexed_start_date=indexed_start_date,
        indexed_end_date=indexed_end_date,
        receiver_url=RECEIVER_URL,
        receiver_dashboard_url=RECEIVER_DASHBOARD_URL,
    )


@app.route("/search", methods=["POST", "GET"])
def search():
    """Renders the search results."""
    params = request.form
    payload = query_body(params, RESULT_LIMIT)
    headers = {"content-type": "application/json"}
    try:
        response = get(solr_url(app.config), data=json.dumps(payload), headers=headers)
    except RequestException:
        return render_template(
            "search.html",
            params=params,
            error="No response from Solr, is it running?",
            trace=solr_url(app.config),
        )
    if response.status_code >= 400 and response.status_code < 500:
        logging.error(response.text)
        return render_template(
            "search.html",
            params=params,
            page=0,
            offset=0,
            error=response.reason,
            trace=response.url,
        )
    elif response.status_code >= 500:
        result = response.json()
        error = result["error"]
        msg = result["error"]["msg"]
        trace = error.get("trace", "")
        logging.error(response.text)
        return render_template(
            "search.html",
            params=params,
            page=0,
            offset=0,
            error="Solr failed: " + msg,
            trace=trace,
        )
    else:
        app.logger.debug("Calling Solr with url %s", response.url)
        data = response.json()
        docs = data["grouped"]["PatientID"]
        results = data["grouped"]["PatientID"]["ngroups"]
        studies_result = data["grouped"]["PatientID"]["matches"]
        page = params.get("page", 0)
        offset = params.get("offset", 0)
        paging = calc(results, page, RESULT_LIMIT)
        return render_template(
            "result.html",
            docs=docs,
            results="{:,}".format(results),
            studies_result="{:,}".format(studies_result),
            payload=payload,
            facet_url=request.url,
            params=params,
            paging=paging,
            version=VERSION,
            report_show_url=REPORT_SHOW_URL,
            sectra_uniview=SECTRA_UNIVIEW,
            modalities=params.getlist("Modality"),
            page=page,
            offset=offset,
            show_download_options=SHOW_DOWNLOAD_OPTIONS,
            show_transfer_targets=SHOW_TRANSFER_TARGETS,
            transfer_targets=TRANSFER_TARGETS,
            receiver_url=RECEIVER_URL,
            receiver_dashboard_url=RECEIVER_DASHBOARD_URL,
        )


@app.route("/export_anon", methods=["POST"])
def export_anon():
    q = request.form
    df = query_all(q, solr_url(app.config))
    if df is not None:
        df = df.drop(["PatientName", "PatientBirthDate"], axis=1)
        out = io.BytesIO()
        writer = pd.ExcelWriter(out)
        df.to_excel(writer, index=False, sheet_name="Sheet1")
        writer.save()
        writer.close()
        out.seek(0)
        return send_file(out, attachment_filename="export.xlsx", as_attachment=True)
    return ("", 204)


@app.route("/export", methods=["POST"])
def export():
    q = request.form
    df = query_all(q, solr_url(app.config))
    if df is not None:
        out = io.BytesIO()
        writer = pd.ExcelWriter(out)
        df.to_excel(writer, index=False, sheet_name="Sheet1")
        writer.save()
        writer.close()
        out.seek(0)
        return send_file(out, attachment_filename="export.xlsx", as_attachment=True)
    return ("", 204)


@app.route("/download-all", methods=["POST"])
def download_all():
    app.logger.info("download all called")
    q = request.form
    df = query_all(q, solr_url(app.config))
    if df is not None:
        data = convert(df)
        download_data = {
            "data": data,
            "dir": q["download-dir"],
            "image_type": q["imageType"],
            "queue_prio": q["queue"]
        }
        return download_or_transfer(RECEIVER_DOWNLOAD_URL, download_data)
    return ("", 204)


@app.route("/download", methods=["POST"])
def download():
    """Ajax post to download series of images."""
    app.logger.info("download called")
    data = request.get_json(force=True)
    return download_or_transfer(RECEIVER_DOWNLOAD_URL, data)


@app.route("/transfer-all", methods=["POST"])
def transfer_all():
    """Ajax post to transfer series of images to <target> PACS node."""
    app.logger.info("transfer all called")
    q = request.form
    df = query_all(q, solr_url(app.config))
    if df is not None:
        data = convert(df)
        target = q["target"]
        transfer_data = {"data": data, "target": q["target"]}
        app.logger.info(f"Transfer called and sending to AE_TITLE {target}")
        t = [t for t in TRANSFER_TARGETS if t["DISPLAY_NAME"] == target]
        if t:
            destination = t[0]["AE_TITLE"]
            transfer_data["target"] = destination
            return download_or_transfer(RECEIVER_TRANSFER_URL, transfer_data)
        else:
            return f"Error: Could not find destination AE_TITLE for {t}"
    return ("", 204)


@app.route("/transfer", methods=["POST"])
def transfer():
    """Ajax post to transfer series of images to <target> PACS node."""
    data = request.get_json(force=True)
    target = data.get("target", "")
    app.logger.info(f"Transfer called and sending to AE_TITLE {target}")
    t = [t for t in TRANSFER_TARGETS if t["DISPLAY_NAME"] == target]
    if t:
        destination = t[0]["AE_TITLE"]
        data["target"] = destination
        return download_or_transfer(RECEIVER_TRANSFER_URL, data)
    else:
        return "Error: Could not find destination AE_TITLE"


def download_or_transfer(url, data):
    headers = {"content-type": "application/json"}
    try:
        response = post(url, json=data, headers=headers)
        if response.status_code == requests.codes.ok:
            return json.dumps(response.json())
        else:
            app.logger.error(f"POST to url {url} failed")
            logging.error(f"Error posting to: {url}")
            logging.error(response.reason)
            return json.dumps({"status": "error", "message": "POST failed"})
    except requests.exceptions.ConnectionError:
        app.logger.error("ConnectionError: Can't connect to receiver")
        return ("Is pacs_ris_crawler-receiver running? Can't get a connection", 400)


@app.route("/terms")
def terms():
    """Renders a page about term information. Only internal use."""
    data = get_terms_data(app.config)
    return render_template("terms.html", terms=data)


@app.route("/statistics")
def statistics():
    return render_template("statistics.html")


@app.route("/statistics/month")
def month_statistics():
    data = get_statistics_per_month(request.args["month"])
    df = pd.DataFrame.from_dict(data["response"]["docs"])
    df["date"] = pd.to_datetime(df["StudyDate"], format="%Y%m%d")
    df = df.groupby("date").agg("count").reset_index()
    df.to_csv("test.csv", index=False)
    return df.to_json(orient="records")


@app.route("/stats_per_year", methods=["GET"])
def stats_per_year():
    year = request.args["year"]
    payload = {
        "q": "*",
        "rows": "1000000",
        "fq": ["Category:parent"],
        "fq": [f"StudyDate:[{year}0101 TO {year}1231]"],
        "fl": "InstitutionName, StudyDate",
    }
    headers = {"content-type": "application/json"}
    response = get(solr_url(app.config), payload, headers=headers)
    data = response.json()["response"]["docs"]
    df = pd.DataFrame.from_dict(data)
    df["date"] = pd.to_datetime(df["StudyDate"], format="%Y%m%d")
    df = df.groupby("date").agg("count").reset_index()
    fig = Figure(figsize=(13, 6))
    ax = fig.subplots()
    july.heatmap(
        df["date"],
        df["StudyDate"],
        value_label=True,
        fontsize=6,
        fontfamily="monospace",
        title="Yearly studies",
        month_grid=True,
        horizontal=True,
        colorbar=True,
        cmap="summer_r",
        dpi=100,
        ax=ax,
    )
    buf = BytesIO()
    fig.savefig(buf, format="png", bbox_inches="tight", pad_inches=0)
    data = base64.b64encode(buf.getbuffer()).decode("ascii")
    return f"<img src='data:image/png;base64,{data}'/>"


@app.route("/statistics/data.csv")
def statistics_data():
    years = ["2011", "2012", "2013", "2014", "2015", "2016", "2017", "2018", "2019"]
    for year in years:
        if not os.path.exists(f"institute_statistics_{year}.csv"):
            data = get_statistics_per_year(year)
            df = pd.DataFrame.from_dict(data["response"]["docs"])
            if df.empty:
                df = pd.DataFrame.from_dict(
                    {
                        "year": [year],
                        "institution_type": ["Main"],
                        "InstitutionName": [1],
                        "StudyDate": [1],
                    }
                )
            else:
                df = calculate(df)
            df.to_csv(f"institute_statistics_{year}.csv", index=False)

    df = pd.concat([pd.read_csv(f"institute_statistics_{year}.csv") for year in years])
    return df.to_csv()


def get_statistics_per_month(date):
    payload = {
        "q": "*",
        "rows": "10000000",
        "fq": ["Category:parent"],
        "fq": [f"StudyDate:[{date}01 TO {date}31]"],
        "fl": "InstitutionName, StudyDate",
    }
    headers = {"content-type": "application/json"}
    response = get(solr_url(app.config), payload, headers=headers)
    return response.json()


def get_statistics_per_year(year):
    payload = {
        "q": "*",
        "rows": "10000000",
        "fq": ["Category:parent"],
        "fq": [f"StudyDate:[{year}0101 TO {year}1231]"],
        "fl": "InstitutionName, StudyDate",
    }
    headers = {"content-type": "application/json"}
    response = get(solr_url(app.config), payload, headers=headers)
    return response.json()


def get_statistics():
    payload = {
        "q": "*",
        "rows": "10000000",
        "fq": ["Category:parent"],
        "fl": "InstitutionName, StudyDate",
    }
    headers = {"content-type": "application/json"}
    response = get(solr_url(app.config), payload, headers=headers)
    return response.json()
