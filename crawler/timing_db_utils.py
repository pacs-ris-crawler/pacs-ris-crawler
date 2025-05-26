#!/usr/bin/env python3
"""
Utility script for managing the MS SQL Server study data database.
Provides functions to export data to CSV, get statistics, and manage the database.
"""

import csv
import os
from typing import Dict,  Optional

import structlog
from sqlalchemy import URL, create_engine, text
from sqlalchemy.exc import SQLAlchemyError
from tasks.util import load_config

log = structlog.get_logger()


def get_db_connection():
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


def export_to_csv(output_file: Optional[str] = None, limit: Optional[int] = None) -> str:
    """
    Export study data from MS SQL Server database to CSV file
    
    Args:
        output_file: Path to output CSV file (default: crawler/data/study_data.csv)
        limit: Maximum number of records to export (default: all)
    
    Returns:
        Path to the created CSV file
    """
    if output_file is None:
        output_file = os.path.join('crawler', 'data', 'study_data.csv')
    
    try:
        engine = get_db_connection()
        
        with engine.connect() as conn:
            # Build query
            query = text('''
                SELECT acc, studydescription, studydate, start_time, end_time, duration_seconds
                FROM pacscrawler_studydata
                ORDER BY start_time
            ''')
            
            if limit:
                query = text(f'''
                    SELECT TOP {limit} acc, studydescription, studydate, start_time, end_time, duration_seconds
                    FROM pacscrawler_studydata
                    ORDER BY start_time
                ''')
            
            result = conn.execute(query)
            rows = result.fetchall()
            
            if not rows:
                log.warning("No study data found in database")
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
            
            log.info(f"Exported {len(rows)} study records to {output_file}")
            return output_file
            
    except SQLAlchemyError as e:
        log.error(f"Failed to export study data: {e}")
        raise
    finally:
        engine.dispose()


def get_timing_statistics() -> Dict:
    """
    Get comprehensive statistics about study data
    
    Returns:
        Dictionary containing various timing statistics
    """
    try:
        engine = get_db_connection()
        
        with engine.connect() as conn:
            # Basic statistics
            result = conn.execute(text('''
                SELECT 
                    COUNT(*) as total_count,
                    AVG(duration_seconds) as avg_duration,
                    MIN(duration_seconds) as min_duration,
                    MAX(duration_seconds) as max_duration,
                    MIN(start_time) as earliest_record,
                    MAX(start_time) as latest_record
                FROM pacscrawler_studydata
            '''))
            
            basic_stats = result.fetchone()
            
            if basic_stats[0] == 0:
                return {'total_count': 0, 'message': 'No study data found'}
            
            # Study description statistics
            result = conn.execute(text('''
                SELECT TOP 10 studydescription, COUNT(*) as count
                FROM pacscrawler_studydata
                WHERE studydescription IS NOT NULL AND studydescription != ''
                GROUP BY studydescription
                ORDER BY count DESC
            '''))
            
            study_stats = result.fetchall()
            
            # Duration percentiles
            result = conn.execute(text('''
                SELECT 
                    PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY duration_seconds) OVER () as p50,
                    PERCENTILE_CONT(0.9) WITHIN GROUP (ORDER BY duration_seconds) OVER () as p90,
                    PERCENTILE_CONT(0.95) WITHIN GROUP (ORDER BY duration_seconds) OVER () as p95,
                    PERCENTILE_CONT(0.99) WITHIN GROUP (ORDER BY duration_seconds) OVER () as p99
                FROM pacscrawler_studydata
            '''))
            
            percentiles = result.fetchone()
            
            stats = {
                'total_count': basic_stats[0],
                'avg_duration': round(basic_stats[1], 4) if basic_stats[1] else 0,
                'min_duration': basic_stats[2],
                'max_duration': basic_stats[3],
                'earliest_record': basic_stats[4],
                'latest_record': basic_stats[5],
                'p50_duration': percentiles[0],
                'p90_duration': percentiles[1],
                'p95_duration': percentiles[2],
                'p99_duration': percentiles[3],
                'top_study_types': study_stats
            }
            
            return stats
            
    except SQLAlchemyError as e:
        log.error(f"Failed to get study statistics: {e}")
        raise
    finally:
        engine.dispose()


def print_timing_summary():
    """Print a formatted summary of study statistics"""
    try:
        stats = get_timing_statistics()
        
        if stats.get('total_count', 0) == 0:
            print("No study data found in database")
            return
        
        print("\n" + "="*60)
        print("STUDY DATA STATISTICS SUMMARY")
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
        print(f"Error getting study summary: {e}")


def cleanup_old_records(days: int = 30) -> int:
    """
    Remove study records older than specified number of days
    
    Args:
        days: Number of days to keep (default: 30)
    
    Returns:
        Number of records deleted
    """
    try:
        engine = get_db_connection()
        
        with engine.connect() as conn:
            # Delete old records
            result = conn.execute(text('''
                DELETE FROM pacscrawler_studydata
                WHERE created_at < DATEADD(day, -:days, GETDATE())
            '''), {'days': days})
            
            deleted_count = result.rowcount
            conn.commit()
            
            log.info(f"Deleted {deleted_count} study records older than {days} days")
            return deleted_count
            
    except SQLAlchemyError as e:
        log.error(f"Failed to cleanup old records: {e}")
        raise
    finally:
        engine.dispose()


def get_database_info() -> Dict:
    """Get information about the database"""
    try:
        engine = get_db_connection()
        
        with engine.connect() as conn:
            # Get database size and other info
            result = conn.execute(text('''
                SELECT 
                    DB_NAME() as database_name,
                    (SELECT SUM(size * 8.0 / 1024) FROM sys.database_files) as size_mb,
                    (SELECT COUNT(*) FROM pacscrawler_studydata) as record_count,
                    (SELECT MIN(created_at) FROM pacscrawler_studydata) as earliest_record,
                    (SELECT MAX(created_at) FROM pacscrawler_studydata) as latest_record
            '''))
            
            info = result.fetchone()
            
            return {
                'database_name': info[0],
                'size_mb': round(info[1], 2),
                'record_count': info[2],
                'earliest_record': info[3],
                'latest_record': info[4]
            }
            
    except SQLAlchemyError as e:
        log.error(f"Failed to get database info: {e}")
        return {'error': str(e)}
    finally:
        engine.dispose()


def optimize_database():
    """Optimize the database by updating statistics"""
    try:
        engine = get_db_connection()
        
        with engine.connect() as conn:
            log.info("Running database optimization...")
            
            # Update table statistics
            conn.execute(text('UPDATE STATISTICS pacscrawler_studydata WITH FULLSCAN'))
            
            log.info("Database optimization completed")
            
    except SQLAlchemyError as e:
        log.error(f"Failed to optimize database: {e}")
        raise
    finally:
        engine.dispose()


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
            if 'error' not in info:
                print(f"Database: {info['database_name']}")
                print(f"Size: {info['size_mb']} MB")
                print(f"Records: {info['record_count']:,}")
                print(f"Time range: {info['earliest_record']} to {info['latest_record']}")
            else:
                print(f"Error: {info['error']}")
                
        elif command == "optimize":
            optimize_database()
            print("Database optimization completed")
            
        else:
            print(f"Unknown command: {command}")
            sys.exit(1)
            
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)