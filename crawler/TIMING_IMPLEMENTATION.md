# Timing Implementation with SQLite WAL Mode

This document describes the implementation of timing data collection for the `index_acc` function using SQLite with WAL (Write-Ahead Logging) mode for concurrent access.

## Overview

The timing system collects the following data for each successful accession processing:
- **acc**: Accession number
- **studydescription**: Study description (from StudyDescription field)
- **studydate**: Study date (from StudyDate field) 
- **start_time**: Start timestamp with microsecond precision
- **end_time**: End timestamp with microsecond precision
- **duration_seconds**: Duration in seconds (4 decimal places)
- **created_at**: Database insertion timestamp

## Database Schema

```sql
CREATE TABLE timing_info (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    acc TEXT NOT NULL,
    studydescription TEXT,
    studydate TEXT,
    start_time TEXT NOT NULL,
    end_time TEXT NOT NULL,
    duration_seconds REAL NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Indexes for performance
CREATE INDEX idx_timing_acc ON timing_info(acc);
CREATE INDEX idx_timing_start_time ON timing_info(start_time);
CREATE INDEX idx_timing_created_at ON timing_info(created_at);
```

## SQLite WAL Mode Benefits

✅ **Concurrent Access**: Multiple processes can read while one writes  
✅ **Non-blocking**: Readers don't block writers and vice versa  
✅ **ACID Transactions**: Full data integrity guarantees  
✅ **Automatic Recovery**: Database handles crashes gracefully  
✅ **Better Performance**: Optimized for concurrent workloads  
✅ **No File Locking Issues**: WAL mode handles contention internally  

## Performance Optimizations

The implementation includes several SQLite performance optimizations:

```sql
PRAGMA journal_mode=WAL;           -- Enable WAL mode
PRAGMA synchronous=NORMAL;         -- Faster than FULL, still safe with WAL  
PRAGMA cache_size=10000;           -- 10MB cache
PRAGMA temp_store=MEMORY;          -- Use memory for temp tables
```

Connection timeout is set to 30 seconds to handle concurrent access gracefully.

## Files Modified/Created

### Core Implementation
- **`crawler/tasks/ris_pacs_merge_upload.py`**: Main implementation with timing collection
- **`crawler/timing_db_utils.py`**: Database management and CSV export utilities

### Test Files
- **`crawler/test_studydate.py`**: Test script to verify StudyDate functionality

## Usage Examples

### Export Data to CSV
```bash
# Export all data to default location (crawler/data/timing_info.csv)
python crawler/timing_db_utils.py export

# Export to custom file
python crawler/timing_db_utils.py export /path/to/timing.csv

# Export latest 1000 records
python crawler/timing_db_utils.py export timing_recent.csv 1000
```

### View Statistics
```bash
# View comprehensive timing statistics
python crawler/timing_db_utils.py stats
```

### Database Management
```bash
# Get database information (including WAL mode status)
python crawler/timing_db_utils.py info

# Cleanup records older than 30 days
python crawler/timing_db_utils.py cleanup 30

# Optimize database performance
python crawler/timing_db_utils.py optimize
```

### Test Implementation
```bash
# Test StudyDate functionality
python crawler/test_studydate.py
```

## CSV Output Format

The exported CSV contains the following columns:
- `acc`: Accession number
- `studydescription`: Study description (empty if not available)
- `studydate`: Study date (empty if not available)
- `start_time`: Start timestamp (YYYY-MM-DD HH:MM:SS.ffffff)
- `end_time`: End timestamp (YYYY-MM-DD HH:MM:SS.ffffff)
- `duration_seconds`: Duration in seconds (4 decimal places)

Example CSV content:
```csv
acc,studydescription,studydate,start_time,end_time,duration_seconds
ACC001,CT Head,20240101,2024-01-15 10:30:15.123456,2024-01-15 10:31:00.567890,45.4444
ACC002,MR Brain,20240102,2024-01-15 10:31:15.789012,2024-01-15 10:32:23.234567,67.4456
```

## Data Flow

1. **`index_acc()`** starts timing and processes accession
2. **Extract metadata**: StudyDescription and StudyDate from merged JSON
3. **Upload to Solr**: Process the actual upload
4. **Log timing**: Call `_log_timing_info_sqlite()` with all timing data
5. **Database storage**: Insert record with WAL mode for concurrent safety

## Error Handling

- Database connection failures are logged but don't stop processing
- Missing StudyDescription/StudyDate are stored as empty strings
- 30-second timeout prevents hanging on database locks
- WAL mode ensures data integrity even with process crashes

## Concurrent Access

The implementation is designed for production environments with multiple concurrent processes:

- **WAL Mode**: Allows concurrent reads and non-blocking writes
- **Timeout Handling**: 30-second connection timeout prevents deadlocks
- **Error Isolation**: Database errors don't affect main processing flow
- **Automatic Retry**: SQLite handles temporary locks automatically

## Monitoring

Use the utility commands to monitor the system:
```bash
# Check database health and WAL status
python crawler/timing_db_utils.py info

# View recent performance statistics  
python crawler/timing_db_utils.py stats
```

## Maintenance

Regular maintenance tasks:
```bash
# Clean up old records (keep last 30 days)
python crawler/timing_db_utils.py cleanup 30

# Optimize database performance
python crawler/timing_db_utils.py optimize
```

The optimization command runs:
- `ANALYZE`: Updates table statistics for better query planning
- `VACUUM`: Reclaims unused space
- `PRAGMA wal_checkpoint(FULL)`: Checkpoints WAL file

## Migration from Previous Implementations

The database automatically handles migrations:
- New installations create the full schema with StudyDate
- Existing databases get StudyDate column added via `ALTER TABLE`
- No data loss during migration

This ensures backward compatibility with existing timing databases. 