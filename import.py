#%% testing
import json
from datetime import datetime 
# %%
with open("acc_29271100_ris_pacs_merged.json", "r") as f:
    data = json.loads(f.read())

print(data[0])
# %%
from sqlalchemy import create_engine


engine = create_engine("sqlite+pysqlite:///main.db")

with engine.connect() as con:
    result = con.execute("Select * from Patient")
    print(result.all())
# %%

with engine.connect() as conn:
    patient_values = {
        "patient_id": data[0]["PatientID"],
        "patient_birthdate": data[0]["PatientBirthDate"],
        "patient_name": data[0]["PatientName"],
        "patient_sex": data[0]["PatientSex"],
        "now": datetime.now()
    }
    result = conn.execute(
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
    )
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
    result = conn.execute(
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
    )
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
        conn.execute( 
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
    )
# %%
