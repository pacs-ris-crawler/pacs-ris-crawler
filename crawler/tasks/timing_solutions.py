import csv
import os
from datetime import datetime

import structlog

log = structlog.get_logger()


def log_timing_info_per_process(acc: str, study_description: str, start_time: datetime, 
                               end_time: datetime, duration: float):
    """
    Solution 2: Log timing information to process-specific CSV files
    Each process writes to its own file, avoiding contention entirely
    """
    process_id = os.getpid()
    csv_file_path = os.path.join('crawler', 'data', f'timing_info_{process_id}.csv')
    
    # Check if file exists to determine if we need to write headers
    file_exists = os.path.exists(csv_file_path)
    
    # Create data directory if it doesn't exist
    os.makedirs(os.path.join('crawler', 'data'), exist_ok=True)
    
    try:
        with open(csv_file_path, 'a', newline='') as csvfile:
            fieldnames = ['acc', 'studydescription', 'start_time', 'end_time', 'duration_seconds']
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            
            # Write header if file is new
            if not file_exists:
                writer.writeheader()
            
            # Write timing data
            writer.writerow({
                'acc': acc,
                'studydescription': study_description or '',
                'start_time': start_time.strftime('%Y-%m-%d %H:%M:%S.%f'),
                'end_time': end_time.strftime('%Y-%m-%d %H:%M:%S.%f'),
                'duration_seconds': round(duration, 4)
            })
            
    except Exception as e:
        log.error(f"Failed to write timing info for {acc}: {e}")


def log_timing_info_structured(acc: str, study_description: str, start_time: datetime, 
                              end_time: datetime, duration: float):
    """
    Solution 3: Use structured logging instead of CSV
    Let the logging framework handle concurrency
    """
    log.info(
        "accession_timing",
        acc=acc,
        studydescription=study_description or '',
        start_time=start_time.isoformat(),
        end_time=end_time.isoformat(),
        duration_seconds=round(duration, 4)
    )


def log_timing_info_database(acc: str, study_description: str, start_time: datetime, 
                           end_time: datetime, duration: float):
    """
    Solution 4: Store timing data in database
    Requires adding database connection to your config
    """
    try:
        # This would require your database connection setup
        # Example with SQLite (you could use PostgreSQL, MySQL, etc.)
        import sqlite3
        
        db_path = os.path.join('crawler', 'data', 'timing.db')
        os.makedirs(os.path.join('crawler', 'data'), exist_ok=True)
        
        with sqlite3.connect(db_path) as conn:
            # Create table if it doesn't exist
            conn.execute('''
                CREATE TABLE IF NOT EXISTS timing_info (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    acc TEXT NOT NULL,
                    studydescription TEXT,
                    start_time TEXT NOT NULL,
                    end_time TEXT NOT NULL,
                    duration_seconds REAL NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # Insert timing data
            conn.execute('''
                INSERT INTO timing_info 
                (acc, studydescription, start_time, end_time, duration_seconds)
                VALUES (?, ?, ?, ?, ?)
            ''', (
                acc,
                study_description or '',
                start_time.strftime('%Y-%m-%d %H:%M:%S.%f'),
                end_time.strftime('%Y-%m-%d %H:%M:%S.%f'),
                round(duration, 4)
            ))
            
            conn.commit()
            
    except Exception as e:
        log.error(f"Failed to write timing info to database for {acc}: {e}")


# Utility function to merge process-specific CSV files
def merge_timing_files():
    """
    Utility to merge all process-specific timing files into one
    Run this periodically or at the end of processing
    """
    data_dir = os.path.join('crawler', 'data')
    merged_file = os.path.join(data_dir, 'timing_info_merged.csv')
    
    if not os.path.exists(data_dir):
        return
    
    all_rows = []
    header_written = False
    
    # Find all timing files
    for filename in os.listdir(data_dir):
        if filename.startswith('timing_info_') and filename.endswith('.csv'):
            filepath = os.path.join(data_dir, filename)
            
            try:
                with open(filepath, 'r', newline='') as csvfile:
                    reader = csv.DictReader(csvfile)
                    if not header_written:
                        fieldnames = reader.fieldnames
                        header_written = True
                    
                    for row in reader:
                        all_rows.append(row)
                        
            except Exception as e:
                log.error(f"Failed to read {filepath}: {e}")
    
    # Write merged file
    if all_rows:
        try:
            with open(merged_file, 'w', newline='') as csvfile:
                writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
                writer.writeheader()
                writer.writerows(all_rows)
                
            log.info(f"Merged {len(all_rows)} timing records into {merged_file}")
            
        except Exception as e:
            log.error(f"Failed to write merged file: {e}")


# Export timing data from database to CSV
def export_timing_from_database():
    """
    Export timing data from database to CSV
    """
    try:
        import sqlite3
        
        db_path = os.path.join('crawler', 'data', 'timing.db')
        csv_path = os.path.join('crawler', 'data', 'timing_info_from_db.csv')
        
        if not os.path.exists(db_path):
            log.warning("No timing database found")
            return
            
        with sqlite3.connect(db_path) as conn:
            cursor = conn.execute('''
                SELECT acc, studydescription, start_time, end_time, duration_seconds
                FROM timing_info
                ORDER BY start_time
            ''')
            
            rows = cursor.fetchall()
            
            if rows:
                with open(csv_path, 'w', newline='') as csvfile:
                    fieldnames = ['acc', 'studydescription', 'start_time', 'end_time', 'duration_seconds']
                    writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
                    writer.writeheader()
                    
                    for row in rows:
                        writer.writerow({
                            'acc': row[0],
                            'studydescription': row[1],
                            'start_time': row[2],
                            'end_time': row[3],
                            'duration_seconds': row[4]
                        })
                
                log.info(f"Exported {len(rows)} timing records to {csv_path}")
                
    except Exception as e:
        log.error(f"Failed to export from database: {e}") 