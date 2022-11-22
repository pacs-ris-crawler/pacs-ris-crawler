#%% testing
import json

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
    }
    result = conn.execute(
        """
        INSERT INTO 
            Patient(PatientID, 
                    PatientName,
                    PatientBirthDate,
                    PatientSex) 
            Values(:patient_id, 
                   :patient_name, 
                   :patient_birthdate,
                   :patient_sex)""",
        patient_values,
    )
    patient_id = result.lastrowid   
    print(f"last rowid: {patient_id}")
    study_values = {
        "accession_number": data[0]["AccessionNumber"],
        "study_description": data[0]["StudyDescription"],
        "study_date": data[0]["StudyDate"],
        "study_time": data[0]["StudyTime"],
        "modalities_in_study": data[0]["ModalitiesInStudy"],
        "instution_name": data[0]["InstitutionName"],
        "referring_physician_name": data[0]["ReferringPhysicianName"],
        "fk_patient": patient_id
    }
    print(study_values)
    conn.execute(
        """
        INSERT INTO 
            Study(AccessionNumber,
                  StudyDescription,
                  StudyDate,
                  StudyTime,
                  ModalitiesInStudy,
                  InstitutionName,
                  ReferringPhysicianName,
                  FK_Patient_id_Patient)
            Values(:accession_number,
                   :study_description,
                   :study_date,
                   :study_time,
                   :modalities_in_study,
                   :instution_name,
                   :referring_physician_name,
                   :fk_patient)""",
        study_values,
    )
# %%
