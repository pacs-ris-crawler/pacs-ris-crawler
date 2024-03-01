from datetime import datetime

from flask import Flask
from sqlalchemy import create_engine, text

engine = create_engine("sqlite+pysqlite:///data/main.db")

def load_config():
    app = Flask(__name__)
    app.config.from_pyfile(filename="../instance/config.cfg")
    return app.config


def load_dicom_config(dicom_node):
    app = Flask(__name__)
    app.config.from_pyfile(filename="../instance/config.cfg")
    node = app.config["DICOM_NODES"][dicom_node]
    return node


def load_prefetch_node():
    app = Flask(__name__)
    app.config.from_pyfile(filename="../instance/config.cfg")
    node = app.config["PREFETCH_NODE"]["SECTRA_PREFETCH"]
    return node

def dict_to_str(parameter_dict):
    return "".join(["{}_{}".format(k, v) for k, v in parameter_dict.items()])


def store_to_sqlite(data):
    with engine.connect() as conn:
        patient_values = {
            "patient_id": data[0]["PatientID"],
            "patient_birthdate": data[0]["PatientBirthDate"],
            "patient_name": data[0]["PatientName"],
            "patient_sex": data[0]["PatientSex"],
            "now": datetime.now()
        }
        result = conn.execute(text(
            """
            INSERT INTO 
                Patients(PatientID, 
                        PatientName,
                        PatientBirthDate,
                        PatientSex,
                        InsertTimestamp) 
                Values(:patient_id, 
                    :patient_name, 
                    :patient_birthdate,
                    :patient_sex,
                    :now)""",
            patient_values,
        ))
        patient_id = result.lastrowid   
        print(f"last rowid: {patient_id}")
        print(data[0]["_childDocuments_"][0]["StudyInstanceUID"])
        study_values = {
            "study_instance_uid": data[0]["_childDocuments_"][0]["StudyInstanceUID"],
            "patient_id": data[0]["PatientID"],
            "study_id": data[0]["StudyID"],
            "accession_number": data[0]["AccessionNumber"],
            "study_description": data[0]["StudyDescription"],
            "study_date": data[0]["StudyDate"],
            "study_time": data[0]["StudyTime"],
            "modalities_in_study": data[0]["ModalitiesInStudy"],
            "instution_name": data[0]["InstitutionName"],
            "referring_physician_name": data[0]["ReferringPhysicianName"],
            "radiology_report": data[0]["RisReport"],
            "now": datetime.now()
        }
        print(study_values)
        result = conn.execute(text(
            """
            INSERT INTO 
                Studies(StudyInstanceUID,
                    PatientsUID,
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
                    :now)""",
            study_values,
        ))
        study_id = result.lastrowid 
        series = data[0]["_childDocuments_"]
        for s in series:
            series_values = {
            "series_instance_uid": s["SeriesInstanceUID"],
            "series_description": s.get("SeriesDescription"),
            "modality": s["Modality"],
            "protocol_name": s.get("ProtcolName"),
            "bodypartexamined": s.get("BodyPartExamined"),
            "series_date": s["SeriesDate"],
            "series_time": s["SeriesTime"],
            "series_number": s["SeriesNumber"],
            "now": datetime.now()
        }
            conn.execute(text(
            """
            INSERT INTO 
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
                    :now)""",
            series_values,
        ))