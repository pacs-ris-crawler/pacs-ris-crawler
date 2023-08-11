import os
from io import BytesIO

import pandas as pd
from dotenv import load_dotenv
from flask import Flask, g, jsonify, render_template, request, send_file
from loguru import logger
from sqlalchemy import create_engine, text
from datetime import datetime
from timeit import default_timer as timer
from rich import print as rprint

app = Flask(__name__)

logger.info("Running pacs crawler directory")
load_dotenv()


def get_db():
    if "db" not in g:
        g.db = create_engine("sqlite+pysqlite:///main.db")
        logger.info("Connection crawler directory")
    return g.db


def close_db(e=None):
    db = g.pop("db", None)

    if db is not None:
        db.close()
        logger.info("Connection closed to crawler directory")


def store(json_data, engine):
    json_data = json_data[0]
    with engine.connect() as conn:
        start = timer()
        patient_values = {
            "patient_id": json_data["PatientID"],
            "patient_birthdate": json_data["PatientBirthDate"],
            "patient_name": json_data["PatientName"],
            "patient_sex": json_data["PatientSex"],
            "now": datetime.now(),
        }
        conn.execute(
            text(
                """
                INSERT OR IGNORE INTO 
                    Patients(PatientID, 
                            PatientName,
                            PatientBirthDate,
                            PatientSex,
                            InsertTimestamp) 
                    Values(:patient_id, 
                        :patient_name, 
                        :patient_birthdate,
                        :patient_sex,
                        :now)"""
            ),
            patient_values,
        )
       
        study_values = {
            "study_instance_uid": json_data.get("StudyInstanceUID") or json_data["_childDocuments_"][0]["StudyInstanceUID"],
            "patient_id": json_data["PatientID"],
            "study_id": json_data.get("StudyID"),
            "accession_number": json_data["AccessionNumber"],
            "study_description": json_data["StudyDescription"],
            "study_date": json_data["StudyDate"],
            "study_time": json_data.get("StudyTime"),
            "modalities_in_study": json_data.get("ModalitiesInStudy"),
            "instution_name": json_data["InstitutionName"],
            "referring_physician_name": json_data["ReferringPhysicianName"],
            "radiology_report": json_data["RisReport"],
            "now": datetime.now(),
        }
        conn.execute(
            text(
                """
                INSERT OR REPLACE INTO 
                    Studies(StudyInstanceUID,
                        PatientID,
                        StudyID,
                        AccessionNumber,
                        StudyDescription,
                        StudyDate,
                        StudyTime,
                        ModalitiesInStudy,
                        InstitutionName,
                        ReferringPhysicianName,
                        RadiologyReport,
                        InsertTimestamp)
                    Values(:study_instance_uid,
                        :patient_id,
                        :study_id,
                        :accession_number,
                        :study_description,
                        :study_date,
                        :study_time,
                        :modalities_in_study,
                        :instution_name,
                        :referring_physician_name,
                        :radiology_report,
                        :now)"""
            ),
            study_values,
        )
        series = json_data["_childDocuments_"]
        for s in series:
            series_values = {
                "series_instance_uid": s["SeriesInstanceUID"],
                "series_description": s["SeriesDescription"],
                "modality": s["Modality"],
                "protocol_name": s.get("ProtocolName"),
                "bodypartexamined": s.get("BodyPartExamined"),
                "series_date": s.get("SeriesDate"),
                "series_time": s.get("SeriesTime"),
                "series_number": s["SeriesNumber"],
                "now": datetime.now(),
            }
            conn.execute(
                text(
                    """
            INSERT OR REPLACE INTO 
                Series(SeriesInstanceUID,
                    SeriesDescription,
                    Modality,
                    ProtocolName,
                    BodyPartExamined,
                    SeriesDate,
                    SeriesTime,
                    SeriesNumber,
                    InsertTimestamp)
                Values(:series_instance_uid,
                    :series_description,
                    :modality,
                    :protocol_name,
                    :bodypartexamined,
                    :series_date,
                    :series_time,
                    :series_number,
                    :now)"""
                ),
                series_values,
            )
        p_time = timer() - start
        rprint(f"Inserting data took {p_time:.2f} seconds")
        conn.commit()
    return "ok"


@app.route("/")
def main():
    return "ok i"


@app.route("/store", methods=["POST"])
def store_to_cdwh():
    engine = get_db()
    return store(request.get_json(), engine)
