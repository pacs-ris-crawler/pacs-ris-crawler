#!/usr/bin/env python3
"""
Test script to verify StudyDate functionality in timing database
"""

import csv
import os
import sqlite3
from datetime import datetime


def test_timing_database():
    """Test that StudyDate is properly stored and exported"""
    
    # Import the functions we need to test
    import sys
    sys.path.append('.')
    sys.path.append('..')
    
    from crawler.ris_pacs_merge_upload import (
        _get_timing_db_connection,
        _log_timing_info_sqlite,
    )
    
    # Test data
    test_data = [
        {
            'acc': 'TEST001',
            'study_description': 'CT Head',
            'study_date': '20240101',
            'duration': 45.2345
        },
        {
            'acc': 'TEST002', 
            'study_description': 'MR Brain',
            'study_date': '20240102',
            'duration': 67.8912
        },
        {
            'acc': 'TEST003',
            'study_description': 'X-Ray Chest',
            'study_date': None,  # Test null value
            'duration': 12.3456
        }
    ]
    
    print("Testing StudyDate functionality...")
    
    # Clean up any existing test database
    db_path = os.path.join('data', 'timing.db')
    if os.path.exists(db_path):
        os.remove(db_path)
    for ext in ['-wal', '-shm']:
        if os.path.exists(db_path + ext):
            os.remove(db_path + ext)
    
    # Insert test data
    start_time = datetime.now()
    for i, data in enumerate(test_data):
        end_time = datetime.now()
        _log_timing_info_sqlite(
            acc=data['acc'],
            study_description=data['study_description'],
            study_date=data['study_date'],
            start_time=start_time,
            end_time=end_time,
            duration=data['duration']
        )
        print(f"✓ Inserted {data['acc']} with StudyDate: {data['study_date']}")
    
    # Verify data in database
    with _get_timing_db_connection() as conn:
        cursor = conn.execute('''
            SELECT acc, studydescription, studydate, duration_seconds
            FROM timing_info
            ORDER BY acc
        ''')
        rows = cursor.fetchall()
        
        print(f"\nDatabase contains {len(rows)} records:")
        for row in rows:
            print(f"  {row[0]}: {row[1]}, StudyDate={row[2] or 'NULL'}, Duration={row[3]}s")
    
    # Test CSV export
    from timing_db_utils import export_to_csv
    
    csv_file = export_to_csv('data/test_timing_export.csv')
    print(f"\n✓ Exported data to: {csv_file}")
    
    # Read and verify CSV
    with open(csv_file, 'r') as f:
        reader = csv.DictReader(f)
        csv_rows = list(reader)
        
        print(f"\nCSV contains {len(csv_rows)} records:")
        for row in csv_rows:
            print(f"  {row['acc']}: {row['studydescription']}, StudyDate='{row['studydate']}', Duration={row['duration_seconds']}s")
    
    # Verify StudyDate column exists in CSV
    if 'studydate' in csv_rows[0]:
        print("\n✓ StudyDate column correctly included in CSV export")
    else:
        print("\n✗ StudyDate column missing from CSV export")
        return False
    
    # Verify data integrity
    for i, csv_row in enumerate(csv_rows):
        expected = test_data[i]
        if csv_row['acc'] == expected['acc']:
            if csv_row['studydate'] == (expected['study_date'] or ''):
                print(f"✓ StudyDate for {expected['acc']}: Expected '{expected['study_date']}', Got '{csv_row['studydate']}'")
            else:
                print(f"✗ StudyDate mismatch for {expected['acc']}: Expected '{expected['study_date']}', Got '{csv_row['studydate']}'")
                return False
    
    print("\n🎉 All tests passed! StudyDate functionality is working correctly.")
    
    # Clean up test files
    os.remove(csv_file)
    print("✓ Cleaned up test files")
    
    return True

if __name__ == "__main__":
    try:
        success = test_timing_database()
        exit(0 if success else 1)
    except Exception as e:
        print(f"Test failed with error: {e}")
        import traceback
        traceback.print_exc()
        exit(1) 