import time
from datetime import datetime

import requests
import structlog
from sqlalchemy import URL, create_engine, text
from sqlalchemy.exc import SQLAlchemyError

from crawler.config import get_solr_upload_url
from crawler.convert import convert_pacs_file, merge_pacs_ris
from crawler.accession import accession
from crawler.util import load_config

log = structlog.get_logger()


def convert_pacs_file_task(query: dict) -> str:
    if "acc" in query:
        # Run accession task to generate the file
        flat_json = accession(query["acc"], query["dicom_node"])

        if flat_json is None:
            log.warning(
                f"Accession {query['acc']} seems to have no images, skipping"
            )
            return None

        json_out = convert_pacs_file(flat_json)
        return json_out


def merge_pacs_ris_task(query: dict) -> str:
    pacs_json = convert_pacs_file_task(query)

    if pacs_json is None:
        log.warning(f"Accession {query['acc']} seems to have no images, skipping")
        return None

    # Merge PACS and RIS
    merged_out = merge_pacs_ris(pacs_json)

    return merged_out


def _get_db_connection():
    """Get SQLAlchemy engine for MS SQL Server"""
    config = load_config()
    
    
    # Create engine with connection pooling
    connection_string = URL.create(
        "mssql+pyodbc",
        username=config['MSSQL_USERNAME'],
        password=config['MSSQL_PASSWORD'],
        host=config['MSSQL_SERVER'],
        port=config['MSSQL_PORT'],
        database=config['MSSQL_DATABASE'],
        query={
            "driver": "ODBC Driver 18 for SQL Server",
            "TrustServerCertificate": "yes",
        },
    )
    engine = create_engine(
        connection_string,
        pool_pre_ping=True,
        pool_recycle=3600,
        pool_size=5,
        max_overflow=10
    )
    
    return engine


def _log_timing_info_sqlite(acc: str, study_description: str, study_date: str, start_time: datetime, end_time: datetime, duration: float, merged_json: str = None):
    """Log timing information to MS SQL Server database using upsert operation"""
    engine = None
    try:
        engine = _get_db_connection()
        
        with engine.connect() as conn:
            # Use MERGE for upsert operation
            conn.execute(text('''
                MERGE pacscrawler_studydata AS target
                USING (SELECT :acc AS acc) AS source
                ON target.acc = source.acc
                WHEN MATCHED THEN
                    UPDATE SET 
                        studydescription = :study_description,
                        studydate = :study_date,
                        start_time = :start_time,
                        end_time = :end_time,
                        duration_seconds = :duration,
                        merged_json = :merged_json,
                        created_at = GETDATE()
                WHEN NOT MATCHED THEN
                    INSERT (acc, studydescription, studydate, start_time, end_time, duration_seconds, merged_json)
                    VALUES (:acc, :study_description, :study_date, :start_time, :end_time, :duration, :merged_json);
            '''), {
                'acc': acc,
                'study_description': study_description or '',
                'study_date': study_date or '',
                'start_time': start_time,
                'end_time': end_time,
                'duration': round(duration, 4),
                'merged_json': merged_json
            })
            
            conn.commit()
            log.debug(f"Upserted study data for {acc}: {duration:.4f}s")
            
    except SQLAlchemyError as e:
        log.error(f"Failed to upsert study data to database for {acc}: {e}")
    finally:
        if engine is not None:
            engine.dispose()


def index_acc(acc: str):
    start_time = time.time()
    start_datetime = datetime.now()
    
    query = {"acc": acc, "dicom_node": "SECTRA"}
    merged_json = merge_pacs_ris_task(query)

    # Load configuration and get the upload URL
    config = load_config()
    upload_url = get_solr_upload_url(config)
    log.debug("Uploading to url %s", upload_url)

    study_description = None
    study_date = None
    if merged_json is None:
        msg = f"Accession {query['acc']} seems to have no images, skipping"
        log.warning(msg)
        return msg

    # Extract study description and study date if available
    if isinstance(merged_json, list) and len(merged_json) > 0:
        study_description = merged_json[0].get('StudyDescription', None)
        study_date = merged_json[0].get('StudyDate', None)
    elif isinstance(merged_json, dict):
        study_description = merged_json.get('StudyDescription', None)
        study_date = merged_json.get('StudyDate', None)

    # Upload the merged JSON file to Solr
    update_response = requests.post(
        url=upload_url, json=merged_json, params={"commit": "true"}, verify=False
    )
    if not update_response.ok:
        update_response.raise_for_status()

    end_time = time.time()
    end_datetime = datetime.now()
    duration = end_time - start_time
    
    # Log timing information to SQLite database
    _log_timing_info_sqlite(acc, study_description, study_date, start_datetime, end_datetime, duration, str(merged_json))

    return merged_json
