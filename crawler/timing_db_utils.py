#!/usr/bin/env python3
"""
Utility script for managing the SQLite timing database.
Provides functions to export data to CSV, get statistics, and manage the database.
"""

import csv
import os
import sqlite3
from datetime import datetime
from typing import Dict, List, Optional, Tuple

import structlog

log = structlog.get_logger()


def get_timing_db_connection():
    """Get SQLite connection to the timing database"""
    db_path = os.path.join('crawler', 'data', 'timing.db')
    
    if not os.path.exists(db_path):
        raise FileNotFoundError(f"Timing database not found at {db_path}. Run some index_acc operations first to create the database.")
    
    return sqlite3.connect(db_path, timeout=30.0)


def export_to_csv(output_file: Optional[str] = None, limit: Optional[int] = None) -> str:
    """
    Export timing data from SQLite database to CSV file
    
    Args:
        output_file: Path to output CSV file (default: crawler/data/timing_info.csv)
        limit: Maximum number of records to export (default: all)
    
    Returns:
        Path to the created CSV file
    """
    if output_file is None:
        output_file = os.path.join('crawler', 'data', 'timing_info.csv')
    
    try:
        with get_timing_db_connection() as conn:
            # Build query
            query = '''
                SELECT acc, studydescription, studydate, start_time, end_time, duration_seconds
                FROM timing_info
                ORDER BY start_time
            '''
            
            if limit:
                query += f' LIMIT {limit}'
            
            cursor = conn.execute(query)
            rows = cursor.fetchall()
            
            if not rows:
                log.warning("No timing data found in database")
                return output_file
            
            # Write to CSV
            dirname = os.path.dirname(output_file)
            if dirname:  # Only create directories if there's actually a directory path
                os.makedirs(dirname, exist_ok=True)
            
            with open(output_file, 'w', newline='') as csvfile:
                fieldnames = ['acc', 'studydescription', 'studydate', 'start_time', 'end_time', 'duration_seconds']
                writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
                writer.writeheader()
                
                for row in rows:
                    writer.writerow({
                        'acc': row[0],
                        'studydescription': row[1] or '',
                        'studydate': row[2] or '',
                        'start_time': row[3],
                        'end_time': row[4],
                        'duration_seconds': row[5]
                    })
            
            log.info(f"Exported {len(rows)} timing records to {output_file}")
            return output_file
            
    except Exception as e:
        log.error(f"Failed to export timing data: {e}")
        raise


def get_timing_statistics() -> Dict:
    """
    Get comprehensive statistics about timing data
    
    Returns:
        Dictionary containing various timing statistics
    """
    try:
        with get_timing_db_connection() as conn:
            # Basic statistics
            cursor = conn.execute('''
                SELECT 
                    COUNT(*) as total_count,
                    AVG(duration_seconds) as avg_duration,
                    MIN(duration_seconds) as min_duration,
                    MAX(duration_seconds) as max_duration,
                    MIN(start_time) as earliest_record,
                    MAX(start_time) as latest_record
                FROM timing_info
            ''')
            
            basic_stats = cursor.fetchone()
            
            if basic_stats[0] == 0:
                return {'total_count': 0, 'message': 'No timing data found'}
            
            # Study description statistics
            cursor = conn.execute('''
                SELECT studydescription, COUNT(*) as count
                FROM timing_info
                WHERE studydescription IS NOT NULL AND studydescription != ''
                GROUP BY studydescription
                ORDER BY count DESC
                LIMIT 10
            ''')
            
            study_stats = cursor.fetchall()
            
            # Duration percentiles (approximate)
            cursor = conn.execute('''
                SELECT duration_seconds
                FROM timing_info
                ORDER BY duration_seconds
            ''')
            
            durations = [row[0] for row in cursor.fetchall()]
            
            def percentile(data, p):
                """Calculate percentile"""
                if not data:
                    return None
                k = (len(data) - 1) * p / 100
                f = int(k)
                c = k - f
                if f == len(data) - 1:
                    return data[f]
                else:
                    return data[f] * (1 - c) + data[f + 1] * c
            
            stats = {
                'total_count': basic_stats[0],
                'avg_duration': round(basic_stats[1], 4) if basic_stats[1] else 0,
                'min_duration': basic_stats[2],
                'max_duration': basic_stats[3],
                'earliest_record': basic_stats[4],
                'latest_record': basic_stats[5],
                'p50_duration': percentile(durations, 50),
                'p90_duration': percentile(durations, 90),
                'p95_duration': percentile(durations, 95),
                'p99_duration': percentile(durations, 99),
                'top_study_types': study_stats
            }
            
            return stats
            
    except Exception as e:
        log.error(f"Failed to get timing statistics: {e}")
        raise


def print_timing_summary():
    """Print a formatted summary of timing statistics"""
    try:
        stats = get_timing_statistics()
        
        if stats.get('total_count', 0) == 0:
            print("No timing data found in database")
            return
        
        print("\n" + "="*60)
        print("TIMING STATISTICS SUMMARY")
        print("="*60)
        
        print(f"Total accessions processed: {stats['total_count']:,}")
        print(f"Time range: {stats['earliest_record']} to {stats['latest_record']}")
        print()
        
        print("Duration Statistics (seconds):")
        print(f"  Average: {stats['avg_duration']:.4f}")
        print(f"  Minimum: {stats['min_duration']:.4f}")
        print(f"  Maximum: {stats['max_duration']:.4f}")
        print(f"  Median (P50): {stats['p50_duration']:.4f}")
        print(f"  P90: {stats['p90_duration']:.4f}")
        print(f"  P95: {stats['p95_duration']:.4f}")
        print(f"  P99: {stats['p99_duration']:.4f}")
        print()
        
        if stats['top_study_types']:
            print("Top 10 Study Types:")
            for study, count in stats['top_study_types']:
                print(f"  {study}: {count:,}")
        print()
        
    except Exception as e:
        print(f"Error getting timing summary: {e}")


def cleanup_old_records(days: int = 30) -> int:
    """
    Remove timing records older than specified number of days
    
    Args:
        days: Number of days to keep (default: 30)
    
    Returns:
        Number of records deleted
    """
    try:
        with get_timing_db_connection() as conn:
            # Delete old records
            cursor = conn.execute('''
                DELETE FROM timing_info
                WHERE created_at < datetime('now', '-{} days')
            '''.format(days))
            
            deleted_count = cursor.rowcount
            conn.commit()
            
            # Vacuum to reclaim space
            conn.execute('VACUUM')
            
            log.info(f"Deleted {deleted_count} timing records older than {days} days")
            return deleted_count
            
    except Exception as e:
        log.error(f"Failed to cleanup old records: {e}")
        raise


def get_database_info() -> Dict:
    """Get information about the database file and WAL mode status"""
    try:
        db_path = os.path.join('crawler', 'data', 'timing.db')
        
        if not os.path.exists(db_path):
            return {'exists': False, 'path': db_path}
        
        # Get file size
        file_size = os.path.getsize(db_path)
        
        with get_timing_db_connection() as conn:
            # Check WAL mode
            cursor = conn.execute('PRAGMA journal_mode')
            journal_mode = cursor.fetchone()[0]
            
            # Get page count and page size
            cursor = conn.execute('PRAGMA page_count')
            page_count = cursor.fetchone()[0]
            
            cursor = conn.execute('PRAGMA page_size')
            page_size = cursor.fetchone()[0]
            
            # Check if WAL file exists
            wal_file = db_path + '-wal'
            wal_exists = os.path.exists(wal_file)
            wal_size = os.path.getsize(wal_file) if wal_exists else 0
            
            return {
                'exists': True,
                'path': db_path,
                'file_size': file_size,
                'journal_mode': journal_mode,
                'page_count': page_count,
                'page_size': page_size,
                'wal_exists': wal_exists,
                'wal_size': wal_size,
                'total_size': file_size + wal_size
            }
            
    except Exception as e:
        log.error(f"Failed to get database info: {e}")
        return {'error': str(e)}


def optimize_database():
    """Optimize the database by running ANALYZE and VACUUM"""
    try:
        with get_timing_db_connection() as conn:
            log.info("Running database optimization...")
            
            # Update table statistics
            conn.execute('ANALYZE')
            
            # Reclaim unused space
            conn.execute('VACUUM')
            
            # Checkpoint WAL file
            conn.execute('PRAGMA wal_checkpoint(FULL)')
            
            log.info("Database optimization completed")
            
    except Exception as e:
        log.error(f"Failed to optimize database: {e}")
        raise


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) < 2:
        print("Usage:")
        print("  python timing_db_utils.py export [output_file] [limit]")
        print("  python timing_db_utils.py stats")
        print("  python timing_db_utils.py cleanup [days]")
        print("  python timing_db_utils.py info")
        print("  python timing_db_utils.py optimize")
        sys.exit(1)
    
    command = sys.argv[1]
    
    try:
        if command == "export":
            output_file = sys.argv[2] if len(sys.argv) > 2 else None
            limit = int(sys.argv[3]) if len(sys.argv) > 3 else None
            result_file = export_to_csv(output_file, limit)
            print(f"Data exported to: {result_file}")
            
        elif command == "stats":
            print_timing_summary()
            
        elif command == "cleanup":
            days = int(sys.argv[2]) if len(sys.argv) > 2 else 30
            deleted = cleanup_old_records(days)
            print(f"Deleted {deleted} records older than {days} days")
            
        elif command == "info":
            info = get_database_info()
            if info.get('exists'):
                print(f"Database path: {info['path']}")
                print(f"File size: {info['file_size']:,} bytes")
                print(f"Journal mode: {info['journal_mode']}")
                print(f"WAL file exists: {info['wal_exists']}")
                if info['wal_exists']:
                    print(f"WAL file size: {info['wal_size']:,} bytes")
                print(f"Total size: {info['total_size']:,} bytes")
            else:
                print(f"Database does not exist at: {info['path']}")
                
        elif command == "optimize":
            optimize_database()
            print("Database optimization completed")
            
        else:
            print(f"Unknown command: {command}")
            sys.exit(1)
            
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)