import json
from datetime import datetime
from timeit import default_timer as timer

import click
from dotenv import load_dotenv
from rich import print as rprint
from rich.progress import track
from sqlalchemy import create_engine, text


@click.option("-i", "--input", type=click.Path(exists=True), help="import file")
@click.command()
def main(input):
    print("fooooo")
    print(len(input))
    
    with open(input) as f:
        patients = json.load(f)

    engine = create_engine("sqlite+pysqlite:///main.db")

    with engine.connect() as conn:
        for p in patients:
            start = timer()
            patient_values = {
                "patient_id": p["patient_id"],
                "patient_birthdate": p["patient_birthdate"],
                "patient_name": p["patient_name"],
                "patient_sex": p["patient_sex"],
                "now": datetime.now()
            }
            conn.execute(text(
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
                        :now)"""),
                patient_values,
            )
            
            studies = p["studies"]
            for s in studies:
                suid =  s["study_uid"]
                if suid is None:
                    suid = s["series"][0]["study_uid"]
                study_values = {
                    "study_instance_uid": suid,
                    "patient_id": p["patient_id"],
                    "study_id": s.get("study_id"),
                    "accession_number": s["accession_number"],
                    "study_description": s["study_description"],
                    "study_date": s["study_date"],
                    "study_time": s.get("study_time"),
                    "modalities_in_study": s.get("modalities_in_study"),
                    "instution_name": s["instution_name"],
                    "referring_physician_name": s["referring_physician_name"],
                    "radiology_report": s["ris_report"],
                    "now": datetime.now()
                }
                
                conn.execute(text(
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
                            :now)"""),
                    study_values,
                )
                
                series = s["series"]
                for s in series:
                    series_values = {
                        "series_instance_uid": s["series_uid"],
                        "series_description": s["series_description"],
                        "modality": s["modality"],
                        "protocol_name": s.get("protocol_name"),
                        "bodypartexamined": s.get("bodypartexamined"),
                        "series_date": s.get("series_date"),
                        "series_time": s.get("series_time"),
                        "series_number": s["series_number"],
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
                            :now)"""),
                    series_values,
                )
        p_time = timer() - start
        rprint(f"Insert patient took {p_time}")
        conn.commit()
                


if __name__ == "__main__":
    load_dotenv()
    main()
