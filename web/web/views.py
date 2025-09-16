import base64
import io
import json
import logging
import os

import matplotlib
from plotnine import *

matplotlib.use("Agg")
import pandas as pd
import requests
from flask import render_template, request, send_file, jsonify, current_app
from requests import RequestException, get, post

from web.app import (
    RECEIVER_DASHBOARD_URL,
    RECEIVER_DOWNLOAD_URL,
    RECEIVER_TRANSFER_URL,
    RECEIVER_URL,
    REPORT_SHOW_URL,
    RESULT_LIMIT,
    SECTRA_UNIVIEW,
    SHOW_DOWNLOAD_OPTIONS,
    SHOW_TRANSFER_TARGETS,
    TRANSFER_TARGETS,
    VERSION,
    app,
)
from web.convert import convert
from web.paging import calc
from web.query import query_body, query_indexed_dates
from web.query_all import query_all
from web.solr import solr_url
from web.statistics import calculate
from web.terms import get_terms_data
from web.query_llm import llm_validate

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


@app.route("/llm_query", methods=["POST", "GET"])
def llm_query():
    """Converts human text into proper regex query"""
    params = request.get_json(force=True)
    text_query = params.get("query", "")
    model = current_app.config.get('OLLAMA_MODEL', 'mistral-small3.2:24b-instruct-2506-q8_0')
    if text_query and text_query.strip():
        llm_output = llm_validate(model=model, input_prompt=text_query)

    package = {
        "regexQuery": llm_output.get("bericht_query"),
        "studyDescriptionQuery": llm_output.get("modality_query")
    }
    return package


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
        writer = pd.ExcelWriter(out, engine="xlsxwriter")
        df.to_excel(writer, index=False, sheet_name="Sheet1")
        writer.close()
        out.seek(0)
        return send_file(out, download_name="export.xlsx", as_attachment=True)
    return ("", 204)


@app.route("/export", methods=["POST"])
def export():
    q = request.form
    df = query_all(q, solr_url(app.config))
    if df is not None:
        out = io.BytesIO()
        writer = pd.ExcelWriter(out, engine="xlsxwriter")
        df.to_excel(writer, index=False, sheet_name="Sheet1")
        writer.close()
        out.seek(0)
        return send_file(out, download_name="export.xlsx", as_attachment=True)
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
    month = request.args["month"]
    if not month:
        payload = [
            ("q", "*"),
            ("rows", "1000000"),
            ("fq", ["Category:parent"]),
            ("fq", [f"StudyDate:[{year}0101 TO {year}1231]"]),
            ("fl", "InstitutionName, StudyDate"),
        ]
    else:
        payload = [
            ("q", "*"),
            ("rows", "1000000"),
            ("fq", ["Category:parent"]),
            ("fq", [f"StudyDate:[{year}{month}01 TO {year}{month}31]"]),
            ("fl", "InstitutionName, StudyDate"),
        ]
    headers = {"content-type": "application/json"}
    response = get(solr_url(app.config), payload, headers=headers)
    data = response.json()["response"]["docs"]
    df = pd.DataFrame.from_dict(data)
    df["date"] = pd.to_datetime(df["StudyDate"], format="%Y%m%d")
    df = df.groupby("date").agg(count=('date', 'count')).reset_index()
    df['day_of_week'] = df['date'].dt.weekday  # Monday=0, Sunday=6
    df['day_of_month'] = df['date'].dt.day
    df['month'] = df['date'].dt.month_name()
    df['month_num'] = df['date'].dt.month
    df['year'] = df['date'].dt.year

    # Create an ordered categorical variable for 'month'
    month_order = ['January', 'February', 'March', 'April', 'May', 'June',
                'July', 'August', 'September', 'October', 'November', 'December']
    df['month'] = pd.Categorical(df['month'], categories=month_order, ordered=True)

    # Calculate the first weekday of each month
    df['first_day_of_month'] = df['date'].values.astype('datetime64[M]')
    df['first_weekday'] = pd.to_datetime(df['first_day_of_month']).dt.weekday

    # Calculate week of the month to align with calendar weeks
    df['week_of_month'] = ((df['date'].dt.day + df['first_weekday'] - 1) // 7)

    # 3. Define Dynamic Text Colors Based on Counts for Each Month
    # Calculate the maximum count per month
    df['max_count'] = df.groupby('month')['count'].transform('max')

    # Check the number of unique months in the data
    num_months = len(df['month'].unique())

    # Dynamically adjust figure size
    figure_height = num_months * 2

    p = (ggplot(df, aes(x='day_of_week', y='week_of_month', fill='count'))
        + geom_tile(color='white', show_legend=False)
        # Add count labels in the center of the tile
        + geom_text(aes(label='count'), size=6)
        # Add day labels in the lower right corner
        + geom_text(aes(label='day_of_month'),
                    size=4, position=position_nudge(x=0.37, y=-0.4))
        + scale_x_continuous(
            breaks=range(7),
            labels=['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun']
        )
        + scale_y_reverse()
        + scale_fill_gradient(high="#3e83c8",low="#f6f9fc",)
        + scale_color_identity(labels=None)
        + theme_minimal()
        + labs(title=f'Studies / day for {year}', x='', y='')
        + theme(
            axis_text_x=element_text(rotation=0, hjust=0.5, size=7),
            axis_text_y=element_blank(),  # Hide y-axis labels
            axis_ticks_major_y=element_blank(),
            panel_grid_major=element_blank(),  # Remove major grid lines
            panel_grid_minor=element_blank(),  # Remove minor grid lines
            figure_size=(4, figure_height),  # Adjust figure size
            panel_spacing=0.1,
            strip_text_x=element_text(size=6),
            plot_title=element_text(size=7, ha='center'),
        )
    )
    # Apply facets only if there's more than one month
    if num_months > 1:
        p += facet_wrap('~month', ncol=1)
        
    buf = io.BytesIO()
    p.save(buf, format="png", bbox_inches="tight", pad_inches=0, dpi=300)
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
    payload = [
        ("q", "*"),
        ("rows", "10000000"),
        ("fq", ["Category:parent"]),
        ("fq", [f"StudyDate:[{date}01 TO {date}31]"]),
        ("fl", "InstitutionName, StudyDate"),
    ]
    headers = {"content-type": "application/json"}
    response = get(solr_url(app.config), payload, headers=headers)
    return response.json()


def get_statistics_per_year(year):
    payload = [
        ("q", "*"),
        ("rows", "10000000"),
        ("fq", ["Category:parent"]),
        ("fq", [f"StudyDate:[{year}0101 TO {year}1231]"]),
        ("fl", "InstitutionName, StudyDate"),
    ]
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
