import os
import sqlite3
import time
from datetime import datetime

import requests
import structlog

from crawler.config import get_solr_upload_url
from crawler.convert import convert_pacs_file, merge_pacs_ris
from tasks.accession import accession
from tasks.util import load_config

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


def _get_timing_db_connection():
    """Get SQLite connection with WAL mode enabled for concurrent access"""
    db_path = os.path.join('crawler', 'data', 'timing.db')
    
    # Create data directory if it doesn't exist
    os.makedirs(os.path.join('crawler', 'data'), exist_ok=True)
    
    # Connect to database with timeout for concurrent access
    conn = sqlite3.connect(db_path, timeout=30.0)
    
    # Enable WAL mode for better concurrent performance
    conn.execute('PRAGMA journal_mode=WAL')
    
    # Set other performance optimizations
    conn.execute('PRAGMA synchronous=NORMAL')  # Faster than FULL, still safe with WAL
    conn.execute('PRAGMA cache_size=10000')    # 10MB cache
    conn.execute('PRAGMA temp_store=MEMORY')   # Use memory for temp tables
    
    # Create table if it doesn't exist
    conn.execute('''
        CREATE TABLE IF NOT EXISTS timing_info (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            acc TEXT NOT NULL,
            studydescription TEXT,
            studydate TEXT,
            start_time TEXT NOT NULL,
            end_time TEXT NOT NULL,
            duration_seconds REAL NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # Add StudyDate column if it doesn't exist (for existing databases)
    try:
        conn.execute('ALTER TABLE timing_info ADD COLUMN studydate TEXT')
        conn.commit()
    except sqlite3.OperationalError:
        # Column already exists
        pass
    
    # Create indexes for faster queries
    conn.execute('''
        CREATE INDEX IF NOT EXISTS idx_timing_acc ON timing_info(acc)
    ''')
    
    conn.execute('''
        CREATE INDEX IF NOT EXISTS idx_timing_start_time ON timing_info(start_time)
    ''')
    
    conn.execute('''
        CREATE INDEX IF NOT EXISTS idx_timing_created_at ON timing_info(created_at)
    ''')
    
    conn.commit()
    return conn


def _log_timing_info_sqlite(acc: str, study_description: str, study_date: str, start_time: datetime, end_time: datetime, duration: float):
    """Log timing information to SQLite database with WAL mode for concurrent access"""
    try:
        with _get_timing_db_connection() as conn:
            # Insert timing data
            conn.execute('''
                INSERT INTO timing_info 
                (acc, studydescription, studydate, start_time, end_time, duration_seconds)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (
                acc,
                study_description or '',
                study_date or '',
                start_time.strftime('%Y-%m-%d %H:%M:%S.%f'),
                end_time.strftime('%Y-%m-%d %H:%M:%S.%f'),
                round(duration, 4)
            ))
            
            conn.commit()
            log.debug(f"Logged timing info for {acc}: {duration:.4f}s")
            
    except Exception as e:
        log.error(f"Failed to write timing info to database for {acc}: {e}")


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
    _log_timing_info_sqlite(acc, study_description, study_date, start_datetime, end_datetime, duration)

    return "Upload successful for accession %s" % acc
