# Production Debugging Commands for Databases (MySQL & PostgreSQL)

> **Critical Context**: Database misconfiguration can cause complete application outage, data corruption, or security breaches. Always test configuration changes in staging first. Enable slow query logs before issues occur. Have verified backups before making changes. Document all modifications with business justification. Use read-only commands first; modify only when necessary.

---

## MySQL Production Debugging

### Scenario: Diagnosing MySQL High CPU and Slow Queries

**Prerequisites**: MySQL running, slow query log enabled, user has SUPER privileges  
**Common Causes**: Large full table scans, missing indexes, lock contention, suboptimal query plan

#### MySQL Connection and Status Diagnostics

```bash
# STEP 1: Check MySQL connectivity
mysql -h <host> -u <user> -p<password> -e "SELECT 1;"
# Shows: Connection successful if returns 1

# STEP 2: Get MySQL version and status
mysql -u <user> -p<password> -e "SELECT VERSION();"
mysql -u <user> -p<password> -e "SHOW STATUS LIKE 'Uptime';"
# Shows: MySQL version, server uptime

# STEP 3: Check current connections
mysql -u <user> -p<password> -e "SHOW PROCESSLIST;"
# Shows: All active connections and queries

# STEP 4: Get thread statistics
mysql -u <user> -p<password> -e "SHOW STATUS LIKE 'Threads%';"
# Shows: Connected, running, cached threads

# STEP 5: Check maximum connections configured
mysql -u <user> -p<password> -e "SHOW VARIABLES LIKE 'max_connections';"
# Compare: With Threads_connected value

# STEP 6: Get current database and user info
mysql -u <user> -p<password> -e "SELECT DATABASE(), USER();"

# STEP 7: List all databases
mysql -u <user> -p<password> -e "SHOW DATABASES;"

# STEP 8: Check database sizes
mysql -u <user> -p<password> -e "
SELECT 
  table_schema,
  ROUND(SUM(data_length + index_length) / 1024 / 1024, 2) as size_mb
FROM information_schema.TABLES
GROUP BY table_schema
ORDER BY size_mb DESC;"

# STEP 9: Check tables in database
mysql -u <user> -p<password> <database> -e "SHOW TABLES;"

# STEP 10: Get table row count and size
mysql -u <user> -p<password> -e "
SELECT 
  TABLE_NAME,
  TABLE_ROWS,
  ROUND((DATA_LENGTH + INDEX_LENGTH) / 1024 / 1024, 2) as size_mb
FROM information_schema.TABLES
WHERE TABLE_SCHEMA = '<database>'
ORDER BY TABLE_ROWS DESC;"

# STEP 11: Check table structure
mysql -u <user> -p<password> <database> -e "DESCRIBE <table_name>;"
# Shows: Columns, types, keys, nullability

# STEP 12: Check current query running for longest time
mysql -u <user> -p<password> -e "
SELECT 
  ID,
  USER,
  HOST,
  TIME,
  COMMAND,
  STATE,
  INFO
FROM INFORMATION_SCHEMA.PROCESSLIST
WHERE TIME > 60 AND COMMAND != 'Sleep'
ORDER BY TIME DESC;"
```

#### MySQL Performance Analysis and Slow Queries

```bash
# STEP 1: Enable slow query log (requires SUPER privilege)
mysql -u <user> -p<password> -e "
SET GLOBAL slow_query_log = 'ON';
SET GLOBAL long_query_time = 2;"
# NOTE: Sets threshold for slow queries (2 seconds)

# STEP 2: Check slow query log location
mysql -u <user> -p<password> -e "SHOW VARIABLES LIKE 'slow_query_log_file';"

# STEP 3: View slow query log (on server)
tail -100 /var/log/mysql/slow.log
# Shows: Last 100 slow queries

# STEP 4: Analyze slow query with EXPLAIN
mysql -u <user> -p<password> <database> -e "EXPLAIN <slow_query>;"
# Shows: Query execution plan

# STEP 5: Get detailed EXPLAIN output
mysql -u <user> -p<password> <database> -e "EXPLAIN FORMAT=JSON <query>;" | jq .

# STEP 6: Check for full table scans
mysql -u <user> -p<password> -e "SHOW STATUS LIKE 'Select_scan%';"
# Compare: With Select_range for index usage

# STEP 7: Analyze query with PROFILING (development/staging)
mysql -u <user> -p<password> <database> -e "
SET PROFILING = 1;
<your_query>;
SHOW PROFILES;
SHOW PROFILE FOR QUERY 1;"

# STEP 8: Check for table locks
mysql -u <user> -p<password> -e "SHOW OPEN TABLES WHERE In_use > 0;"
# Shows: Locked tables

# STEP 9: Get query lock wait statistics
mysql -u <user> -p<password> -e "
SELECT 
  object_schema,
  object_name,
  COUNT_STAR as lock_waits
FROM performance_schema.table_io_waits_summary_by_table
ORDER BY COUNT_STAR DESC LIMIT 10;"

# STEP 10: Check index usage statistics
mysql -u <user> -p<password> -e "
SELECT 
  object_schema,
  object_name,
  index_name,
  count_read,
  count_write,
  count_insert,
  count_update,
  count_delete
FROM performance_schema.table_io_waits_summary_by_index_usage
WHERE object_schema != 'mysql'
ORDER BY count_read DESC LIMIT 20;"

# STEP 11: Find unused indexes
mysql -u <user> -p<password> -e "
SELECT 
  object_schema,
  object_name,
  index_name
FROM performance_schema.table_io_waits_summary_by_index_usage
WHERE count_read = 0 AND count_write = 0
AND index_name != 'PRIMARY';"

# STEP 12: Get query execution statistics
mysql -u <user> -p<password> -e "
SELECT 
  digest_text,
  count_star,
  avg_timer_wait / 1000000000000 as avg_time_sec,
  sum_timer_wait / 1000000000000 as total_time_sec
FROM performance_schema.events_statements_summary_by_digest
ORDER BY sum_timer_wait DESC LIMIT 20;"
```

#### MySQL Resource Utilization and Configuration

```bash
# STEP 1: Check memory configuration
mysql -u <user> -p<password> -e "
SHOW VARIABLES LIKE 'innodb_buffer_pool_size';
SHOW VARIABLES LIKE 'max_connections';
SHOW VARIABLES LIKE 'tmp_table_size';
SHOW VARIABLES LIKE 'key_buffer_size';"

# STEP 2: Get memory usage statistics
mysql -u <user> -p<password> -e "
SELECT 
  VARIABLE_NAME,
  VARIABLE_VALUE
FROM information_schema.GLOBAL_VARIABLES
WHERE VARIABLE_NAME IN ('innodb_buffer_pool_size', 'query_cache_size', 'max_connections')"

# STEP 3: Check InnoDB buffer pool hit ratio
mysql -u <user> -p<password> -e "
SELECT 
  VARIABLE_VALUE INTO @reads
FROM information_schema.GLOBAL_STATUS
WHERE VARIABLE_NAME = 'Innodb_buffer_pool_reads';

SELECT 
  VARIABLE_VALUE INTO @read_ahead
FROM information_schema.GLOBAL_STATUS
WHERE VARIABLE_NAME = 'Innodb_buffer_pool_read_ahead';

SELECT 
  VARIABLE_VALUE INTO @read_requests
FROM information_schema.GLOBAL_STATUS
WHERE VARIABLE_NAME = 'Innodb_buffer_pool_read_requests';

SELECT 
  (1 - (@reads + @read_ahead) / @read_requests) * 100 as hit_ratio;"
# Should be > 95% for optimal performance

# STEP 4: Monitor disk I/O activity (from OS)
iostat -x 1 5 | grep -E "Device|sda|sdb"
# Shows: Disk read/write rates

# STEP 5: Check InnoDB status and locks
mysql -u <user> -p<password> -e "SHOW ENGINE INNODB STATUS\G" | head -50

# STEP 6: Check thread statistics
mysql -u <user> -p<password> -e "SHOW STATUS LIKE 'Thread%';"

# STEP 7: Check query cache (if enabled)
mysql -u <user> -p<password> -e "SHOW STATUS LIKE 'Qcache%';"

# STEP 8: Verify replication status (if replicating)
mysql -u <user> -p<password> -e "SHOW SLAVE STATUS\G;"
# Shows: Master status, lag, errors

# STEP 9: Check table statistics
mysql -u <user> -p<password> -e "
SELECT 
  TABLE_SCHEMA,
  TABLE_NAME,
  ENGINE,
  TABLE_ROWS,
  AVG_ROW_LENGTH,
  DATA_FREE
FROM information_schema.TABLES
WHERE TABLE_SCHEMA NOT IN ('mysql', 'information_schema', 'performance_schema')
ORDER BY DATA_FREE DESC;"

# STEP 10: Analyze query cost model
mysql -u <user> -p<password> -e "
SELECT * FROM mysql.server_cost;
SELECT * FROM mysql.engine_cost LIMIT 10;"

# STEP 11: Check handler statistics
mysql -u <user> -p<password> -e "SHOW STATUS LIKE 'Handler_%';"

# STEP 12: Monitor long-running queries in real-time
while true; do
  mysql -u <user> -p<password> -e "SELECT TIME, USER, COMMAND, STATE, LEFT(INFO, 50) FROM INFORMATION_SCHEMA.PROCESSLIST WHERE TIME > 5 AND COMMAND != 'Sleep';"
  sleep 2
done
```

#### MySQL Lock and Deadlock Diagnostics

```bash
# STEP 1: Check for locked tables
mysql -u <user> -p<password> -e "SHOW OPEN TABLES WHERE In_use > 0;"

# STEP 2: Get detailed lock information
mysql -u <user> -p<password> -e "
SELECT 
  OBJECT_SCHEMA,
  OBJECT_NAME,
  LOCK_TYPE,
  LOCK_STATUS,
  THREAD_ID,
  PROCESSLIST_ID
FROM performance_schema.table_handles
WHERE OBJECT_SCHEMA != 'mysql';"

# STEP 3: Find blocking transactions
mysql -u <user> -p<password> -e "
SELECT 
  r.trx_id waiting_trx_id,
  r.trx_mysql_thread_id waiting_thread,
  r.trx_query waiting_query,
  b.trx_id blocking_trx_id,
  b.trx_mysql_thread_id blocking_thread,
  b.trx_query blocking_query
FROM information_schema.innodb_lock_waits w
INNER JOIN information_schema.innodb_trx b ON b.trx_id = w.blocking_trx_id
INNER JOIN information_schema.innodb_trx r ON r.trx_id = w.requesting_trx_id;"

# STEP 4: Get lock details per transaction
mysql -u <user> -p<password> -e "
SELECT 
  trx_id,
  trx_state,
  trx_started,
  trx_weight,
  trx_mysql_thread_id,
  trx_query
FROM information_schema.innodb_trx;"

# STEP 5: Check for deadlock incidents
mysql -u <user> -p<password> -e "SHOW ENGINE INNODB STATUS\G" | grep -A 20 "LATEST DEADLOCK"

# STEP 6: Enable deadlock logging (staging/development)
mysql -u <user> -p<password> -e "SET GLOBAL innodb_print_all_deadlocks = 1;"

# STEP 7: Analyze InnoDB lock waits
mysql -u <user> -p<password> -e "
SELECT 
  waiting_trx_id,
  waiting_pid,
  waiting_query,
  blocking_trx_id,
  blocking_pid,
  blocking_query,
  seconds_waiting
FROM sys.innodb_lock_waits;"

# STEP 8: Check for row locks
mysql -u <user> -p<password> -e "
SELECT 
  object_schema,
  object_name,
  index_name,
  lock_type,
  lock_duration,
  lock_data,
  count_star
FROM performance_schema.table_io_waits_summary_by_index_usage
WHERE lock_type != 'NULL'
ORDER BY count_star DESC;"

# STEP 9: Monitor transaction isolation level
mysql -u <user> -p<password> -e "SHOW VARIABLES LIKE 'transaction_isolation';"

# STEP 10: Check lock wait timeout
mysql -u <user> -p<password> -e "SHOW VARIABLES LIKE 'innodb_lock_wait_timeout';"
# Default: 50 seconds; adjust if frequent timeouts

# STEP 11: Kill blocking transaction (use with caution)
# Get blocking thread ID from STEP 1, then:
mysql -u <user> -p<password> -e "KILL <thread_id>;"

# STEP 12: Monitor lock statistics continuously
while true; do
  mysql -u <user> -p<password> -e "SELECT object_schema, object_name, count_star FROM performance_schema.table_io_waits_summary_by_table ORDER BY count_star DESC LIMIT 5;"
  sleep 1
done
```

#### MySQL Replication and HA Troubleshooting

```bash
# STEP 1: Check replication status on replica
mysql -u <user> -p<password> -e "SHOW SLAVE STATUS\G;"
# Key columns: Seconds_Behind_Master, Last_Error

# STEP 2: Check replica SQL thread
mysql -u <user> -p<password> -e "SHOW SLAVE STATUS\G" | grep -E "Slave_IO_Running|Slave_SQL_Running"

# STEP 3: Get binary log position on master
mysql -h <master-host> -u <user> -p<password> -e "SHOW MASTER STATUS\G;"

# STEP 4: Compare replica position with master
# On replica:
mysql -u <user> -p<password> -e "SHOW SLAVE STATUS\G" | grep -E "Master_Log_File|Exec_Master_Log_Pos"

# STEP 5: Check for replication lag
mysql -u <user> -p<password> -e "
SELECT 
  TIMESTAMPDIFF(SECOND, ts, NOW()) as replication_delay_seconds
FROM replication_heartbeat;"

# STEP 6: Skip replicated events (if error)
# WARNING: Only if you understand the implications
mysql -u <user> -p<password> -e "
STOP SLAVE;
SET GLOBAL SQL_SLAVE_SKIP_COUNTER = 1;
START SLAVE;"

# STEP 7: Reset replica (destructive; data will be overwritten)
# ❌ NEVER use in production without backup
mysql -u <user> -p<password> -e "RESET SLAVE;"

# STEP 8: Check binary log status on master
mysql -h <master-host> -u <user> -p<password> -e "SHOW BINARY LOGS;"

# STEP 9: Verify master/replica consistency
# Use pt-table-checksum:
pt-table-checksum \
  --replicate=percona.checksums \
  h=<master-host>,u=<user>,p=<password>

# STEP 10: Monitor replication lag (real-time)
while true; do
  mysql -u <user> -p<password> -e "SHOW SLAVE STATUS\G" | grep "Seconds_Behind_Master"
  sleep 2
done

# STEP 11: Get replication thread metrics
mysql -u <user> -p<password> -e "
SELECT 
  thread_id,
  event_name,
  count_star,
  sum_timer_wait / 1000000000000 as total_time_sec
FROM performance_schema.events_waits_summary_by_thread_by_event_name
WHERE thread_id IN (SELECT thread_id FROM performance_schema.threads WHERE name LIKE '%slave%');"

# STEP 12: Check binary log purging (don't lose logs replica needs)
mysql -h <master-host> -u <user> -p<password> -e "SHOW VARIABLES LIKE 'expire_logs_days';"
```

#### MySQL Backup and Recovery Procedures

```bash
# STEP 1: Get binary log position for backup
mysql -u <user> -p<password> -e "SHOW MASTER STATUS\G;" > backup-position.txt

# STEP 2: Perform logical backup with mysqldump
mysqldump -u <user> -p<password> \
  --all-databases \
  --single-transaction \
  --lock-tables=false \
  --events \
  --triggers \
  --routines > full-backup-$(date +%Y%m%d-%H%M%S).sql

# STEP 3: Backup specific database
mysqldump -u <user> -p<password> \
  <database_name> > db-backup-$(date +%Y%m%d).sql

# STEP 4: Backup with compression
mysqldump -u <user> -p<password> --all-databases | gzip > full-backup-$(date +%Y%m%d).sql.gz

# STEP 5: Enable binary logging for point-in-time recovery
mysql -u <user> -p<password> -e "SET GLOBAL binlog_format = 'ROW';"

# STEP 6: Verify backup integrity
gzip -t full-backup-*.sql.gz  # Test gzip file
# Or decompress to database in staging

# STEP 7: Restore full backup
# WARNING: This overwrites existing data
mysql -u <user> -p<password> < full-backup-$(date +%Y%m%d).sql

# STEP 8: Restore single database from full backup
mysqldump -u <user> -p<password> --all-databases | mysql -u <user> -p<password> <target_db>

# STEP 9: Restore with Percona XtraBackup (hot backup)
# Backup: xtrabackup --backup --target-dir=./backup
# Prepare: xtrabackup --prepare --target-dir=./backup
# Restore: xtrabackup --copy-back --target-dir=./backup

# STEP 10: Get binary logs for point-in-time recovery
mysqlbinlog <log-file> > recovery.sql
# Apply specific range:
mysqlbinlog <log-file> --start-datetime='2026-01-18 14:00:00' \
  --stop-datetime='2026-01-18 15:00:00' > recovery-window.sql

# STEP 11: Test restore in staging environment
# Create staging instance, restore backup, verify integrity

# STEP 12: Document backup and recovery procedure
# Include: backup location, retention policy, restore time estimate, success criteria
```

#### MySQL Configuration Optimization

```bash
# STEP 1: Get current my.cnf location
mysql -u <user> -p<password> -e "SELECT @@datadir;"

# STEP 2: View all configuration variables
mysql -u <user> -p<password> -e "SHOW VARIABLES;" | wc -l

# STEP 3: Tune InnoDB buffer pool (largest tuning impact)
# Recommendation: 70-80% of available memory
mysql -u <user> -p<password> -e "
SET GLOBAL innodb_buffer_pool_size = 67108864000;"  # 62.5GB example

# STEP 4: Tune max_connections based on load
# Recommendation: Start at 150-200, increase if max_used_connections approaches limit
mysql -u <user> -p<password> -e "
SET GLOBAL max_connections = 300;"

# STEP 5: Optimize query cache (if used; deprecated in MySQL 8.0)
mysql -u <user> -p<password> -e "
SET GLOBAL query_cache_size = 67108864;
SET GLOBAL query_cache_type = 1;"

# STEP 6: Configure innodb_flush_log_at_trx_commit (safety vs performance)
# 0 = speed, but risk of data loss on crash
# 1 = safe, but slower (RECOMMENDED for production)
# 2 = compromise
mysql -u <user> -p<password> -e "SET GLOBAL innodb_flush_log_at_trx_commit = 1;"

# STEP 7: Tune slow query threshold
mysql -u <user> -p<password> -e "SET GLOBAL long_query_time = 2.0;"

# STEP 8: Configure concurrent inserts (InnoDB)
mysql -u <user> -p<password> -e "SET GLOBAL innodb_autoinc_lock_mode = 2;"

# STEP 9: Enable InnoDB file-per-table
mysql -u <user> -p<password> -e "SET GLOBAL innodb_file_per_table = ON;"

# STEP 10: Tune tmp_table_size for in-memory temporary tables
mysql -u <user> -p<password> -e "SET GLOBAL tmp_table_size = 536870912;"  # 512MB

# STEP 11: Verify configuration is persisted
# Add to my.cnf:
cat >> /etc/mysql/my.cnf << EOF
[mysqld]
innodb_buffer_pool_size = 67108864000
max_connections = 300
long_query_time = 2
EOF

# STEP 12: Restart MySQL to apply persistent changes
sudo systemctl restart mysql
# Verify:
mysql -u <user> -p<password> -e "SHOW VARIABLES LIKE 'innodb_buffer_pool_size';"
```

#### MySQL User and Permission Management

```bash
# STEP 1: Create application user with limited privileges
mysql -u <user> -p<password> -e "
CREATE USER 'app_user'@'<app-host>' IDENTIFIED BY '<strong-password>';
GRANT SELECT, INSERT, UPDATE, DELETE ON <database>.* TO 'app_user'@'<app-host>';"

# STEP 2: Create read-only user
mysql -u <user> -p<password> -e "
CREATE USER 'readonly'@'%' IDENTIFIED BY '<password>';
GRANT SELECT ON *.* TO 'readonly'@'%';"

# STEP 3: Create user with replication privileges
mysql -u <user> -p<password> -e "
CREATE USER 'repl'@'<replica-host>' IDENTIFIED BY '<password>';
GRANT REPLICATION SLAVE ON *.* TO 'repl'@'<replica-host>';"

# STEP 4: List all users
mysql -u <user> -p<password> -e "SELECT user, host FROM mysql.user;"

# STEP 5: Check user privileges
mysql -u <user> -p<password> -e "SHOW GRANTS FOR 'app_user'@'<app-host>';"

# STEP 6: Revoke privileges
mysql -u <user> -p<password> -e "
REVOKE INSERT, UPDATE, DELETE ON <database>.* FROM 'app_user'@'<app-host>';"

# STEP 7: Force user password change
mysql -u <user> -p<password> -e "
ALTER USER 'app_user'@'<app-host>' IDENTIFIED BY '<new-password>';"

# STEP 8: Check user connection limits
mysql -u <user> -p<password> -e "
SELECT user, host, max_connections, max_user_connections FROM mysql.user
WHERE user != 'root';"

# STEP 9: Set connection limit per user
mysql -u <user> -p<password> -e "
CREATE USER 'limited_user'@'%' IDENTIFIED BY '<password>'
WITH MAX_CONNECTIONS_PER_HOUR 1000
  MAX_QUERIES_PER_HOUR 10000;"

# STEP 10: Remove inactive users
mysql -u <user> -p<password> -e "DROP USER 'old_user'@'<host>';"

# STEP 11: Create administrative user with all privileges (use sparingly)
mysql -u <user> -p<password> -e "
CREATE USER 'admin'@'<admin-host>' IDENTIFIED BY '<password>';
GRANT ALL PRIVILEGES ON *.* TO 'admin'@'<admin-host>' WITH GRANT OPTION;"

# STEP 12: Audit user activity (query logs)
mysql -u <user> -p<password> -e "
SET GLOBAL general_log = 'ON';
# WARNING: Generates heavy I/O; disable after collecting samples
SET GLOBAL general_log = 'OFF';"
```

#### Commands to NEVER use in production

```bash
# ❌ NEVER: DROP TABLE <table>;
#    Without backup; data lost forever
# ❌ NEVER: TRUNCATE TABLE without BACKUP;
#    Quick deletion; hard to recover
# ❌ NEVER: ALTER TABLE with LOCK=DEFAULT on large tables
#    Locks table for entire duration; application downtime
# ❌ NEVER: SET GLOBAL <var> without backup my.cnf first
#    Lost on restart; configuration inconsistent
# ❌ NEVER: DISABLE KEYS on production tables
#    Disables foreign key checks; data integrity issues
# ❌ NEVER: Run REPAIR TABLE without backup
#    May corrupt data further
# ❌ NEVER: Set innodb_flush_log_at_trx_commit = 0
#    Crash = data loss
# ❌ NEVER: Share database passwords in code or Git
#    Credentials exposed permanently
```

---

## PostgreSQL Production Debugging

### Scenario: Diagnosing PostgreSQL Performance and Locking Issues

**Prerequisites**: PostgreSQL running, pg_stat_statements extension enabled, user has superuser or appropriate grants  
**Common Causes**: Missing indexes, sequential scans, lock contention, connection pool exhaustion

#### PostgreSQL Connection and Status Diagnostics

```bash
# STEP 1: Check PostgreSQL connectivity
psql -h <host> -U <user> -d <database> -c "SELECT 1;"
# Shows: Connection successful

# STEP 2: Get PostgreSQL version
psql -h <host> -U <user> -d <database> -c "SELECT version();"

# STEP 3: Get server uptime
psql -h <host> -U <user> -d <database> -c "
SELECT 
  now() - pg_postmaster_start_time() as uptime;"

# STEP 4: List all databases and sizes
psql -h <host> -U <user> -d postgres -c "
SELECT 
  datname as database,
  pg_size_pretty(pg_database_size(datname)) as size
FROM pg_database
ORDER BY pg_database_size(datname) DESC;"

# STEP 5: List current connections
psql -h <host> -U <user> -d <database> -c "
SELECT 
  pid,
  usename,
  application_name,
  state,
  query,
  query_start,
  state_change
FROM pg_stat_activity
WHERE pid != pg_backend_pid()
ORDER BY query_start;"

# STEP 6: Check connection limits
psql -h <host> -U <user> -d postgres -c "
SHOW max_connections;
SELECT count(*) FROM pg_stat_activity;"
# Compare: Current connections vs limit

# STEP 7: Get connected users and their session counts
psql -h <host> -U <user> -d postgres -c "
SELECT 
  usename,
  count(*) as connections
FROM pg_stat_activity
GROUP BY usename
ORDER BY connections DESC;"

# STEP 8: Check database roles
psql -h <host> -U <user> -d postgres -c "\du"

# STEP 9: Check running queries and their duration
psql -h <host> -U <user> -d <database> -c "
SELECT 
  pid,
  usename,
  pg_size_pretty(memory) as memory,
  query,
  state,
  EXTRACT(EPOCH FROM (now() - query_start)) as duration_seconds
FROM pg_stat_activity
WHERE state != 'idle'
ORDER BY query_start;"

# STEP 10: Check idle transactions (potential lock holders)
psql -h <host> -U <user> -d <database> -c "
SELECT 
  pid,
  usename,
  state,
  query_start,
  xact_start,
  EXTRACT(EPOCH FROM (now() - xact_start)) as idle_in_transaction_seconds
FROM pg_stat_activity
WHERE state = 'idle in transaction';"

# STEP 11: Identify long-running transactions
psql -h <host> -U <user> -d <database> -c "
SELECT 
  pid,
  usename,
  query,
  EXTRACT(EPOCH FROM (now() - xact_start)) as transaction_duration_seconds
FROM pg_stat_activity
WHERE xact_start IS NOT NULL
  AND xact_start < now() - INTERVAL '1 minute'
ORDER BY xact_start;"

# STEP 12: Get active connections by application
psql -h <host> -U <user> -d postgres -c "
SELECT 
  application_name,
  count(*) as count,
  client_addr,
  state
FROM pg_stat_activity
GROUP BY application_name, client_addr, state
ORDER BY count DESC;"
```

#### PostgreSQL Query Performance and Indexes

```bash
# STEP 1: Enable pg_stat_statements (must be in shared_preload_libraries)
psql -h <host> -U <user> -d <database> -c "
CREATE EXTENSION IF NOT EXISTS pg_stat_statements;"

# STEP 2: Get top slow queries
psql -h <host> -U <user> -d <database> -c "
SELECT 
  query,
  calls,
  total_time,
  mean_time,
  max_time,
  rows
FROM pg_stat_statements
ORDER BY mean_time DESC LIMIT 20;"

# STEP 3: Get top CPU-consuming queries
psql -h <host> -U <user> -d <database> -c "
SELECT 
  query,
  calls,
  total_time,
  mean_time,
  rows
FROM pg_stat_statements
ORDER BY total_time DESC LIMIT 10;"

# STEP 4: Get query with most executions
psql -h <host> -U <user> -d <database> -c "
SELECT 
  query,
  calls,
  mean_time,
  total_time
FROM pg_stat_statements
ORDER BY calls DESC LIMIT 10;"

# STEP 5: Analyze query execution plan
psql -h <host> -U <user> -d <database> -c "EXPLAIN ANALYZE <query>;"
# Shows: Detailed execution plan with actual vs estimated rows

# STEP 6: Get query plan in JSON format
psql -h <host> -U <user> -d <database> -c "EXPLAIN (ANALYZE, FORMAT JSON) <query>;" | jq .

# STEP 7: Find sequential scans (missing indexes)
psql -h <host> -U <user> -d <database> -c "
SELECT 
  schemaname,
  tablename,
  seq_scan,
  seq_tup_read,
  idx_scan,
  idx_tup_fetch
FROM pg_stat_user_tables
WHERE seq_scan > idx_scan
  AND seq_scan > 100
ORDER BY seq_scan DESC;"

# STEP 8: Check index usage
psql -h <host> -U <user> -d <database> -c "
SELECT 
  schemaname,
  tablename,
  indexname,
  idx_scan,
  idx_tup_read,
  idx_tup_fetch
FROM pg_stat_user_indexes
ORDER BY idx_scan DESC;"

# STEP 9: Find unused indexes
psql -h <host> -U <user> -d <database> -c "
SELECT 
  schemaname,
  tablename,
  indexname,
  idx_scan,
  pg_size_pretty(pg_relation_size(indexrelid)) as size
FROM pg_stat_user_indexes
WHERE idx_scan = 0
  AND indexname NOT LIKE '%_pkey'
ORDER BY pg_relation_size(indexrelid) DESC;"

# STEP 10: Check index size and bloat
psql -h <host> -U <user> -d <database> -c "
SELECT 
  schemaname,
  tablename,
  indexname,
  pg_size_pretty(pg_relation_size(indexrelid)) as index_size,
  idx_scan
FROM pg_stat_user_indexes
ORDER BY pg_relation_size(indexrelid) DESC LIMIT 20;"

# STEP 11: Analyze table for query planner
psql -h <host> -U <user> -d <database> -c "ANALYZE <table_name>;"

# STEP 12: Create index for missing scanned column
# After identifying slow queries:
psql -h <host> -U <user> -d <database> -c "
CREATE INDEX CONCURRENTLY idx_<table>_<column> ON <table>(<column>);"
# CONCURRENTLY allows table access during index creation
```

#### PostgreSQL Locking and Blocking Diagnostics

```bash
# STEP 1: Find blocking sessions
psql -h <host> -U <user> -d <database> -c "
SELECT 
  blocking.pid as blocking_pid,
  blocked.pid as blocked_pid,
  blocked.usename as blocked_user,
  blocked.application_name,
  blocked.query,
  blocking.query as blocking_query
FROM pg_stat_activity AS blocked
JOIN pg_stat_activity AS blocking 
  ON blocking.pid = ANY(pg_blocking_pids(blocked.pid))
WHERE blocked.pid != blocking.pid;"

# STEP 2: Get lock information in detail
psql -h <host> -U <user> -d <database> -c "
SELECT 
  pg_stat_activity.pid,
  pg_stat_activity.usename,
  pg_stat_activity.query,
  pg_locks.locktype,
  pg_locks.relation::regclass,
  pg_locks.mode,
  pg_locks.granted
FROM pg_stat_activity
JOIN pg_locks ON pg_locks.pid = pg_stat_activity.pid
WHERE pg_stat_activity.pid != pg_backend_pid()
ORDER BY pg_stat_activity.pid, pg_locks.locktype;"

# STEP 3: Find waiting locks only
psql -h <host> -U <user> -d <database> -c "
SELECT 
  l.pid,
  a.usename,
  a.application_name,
  a.query,
  l.mode,
  l.relation::regclass
FROM pg_locks l
JOIN pg_stat_activity a ON a.pid = l.pid
WHERE NOT l.granted;"

# STEP 4: Identify table locks
psql -h <host> -U <user> -d <database> -c "
SELECT 
  schemaname,
  tablename,
  n_live_tup,
  n_dead_tup,
  n_mod_since_analyze,
  last_vacuum,
  last_autovacuum,
  last_analyze,
  last_autoanalyze
FROM pg_stat_user_tables
ORDER BY n_dead_tup DESC;"

# STEP 5: Check for long-running locks
psql -h <host> -U <user> -d <database> -c "
SELECT 
  a.pid,
  a.usename,
  a.query,
  EXTRACT(EPOCH FROM (now() - a.query_start)) as seconds,
  l.mode,
  l.relation::regclass
FROM pg_stat_activity a
JOIN pg_locks l ON l.pid = a.pid
WHERE a.state != 'idle'
  AND a.query_start < now() - INTERVAL '5 minutes';"

# STEP 6: Kill blocking session (careful!)
psql -h <host> -U <user> -d <database> -c "
SELECT pg_terminate_backend(<blocking_pid>);"

# STEP 7: Check transaction isolation level
psql -h <host> -U <user> -d <database> -c "
SELECT current_transaction_isolation_level;"

# STEP 8: Check active transactions
psql -h <host> -U <user> -d <database> -c "
SELECT 
  pid,
  xmin,
  xmax,
  xvip,
  datname,
  query
FROM pg_stat_activity
WHERE pid != pg_backend_pid()
ORDER BY xmin;"

# STEP 9: View lock statistics
psql -h <host> -U <user> -d <database> -c "
SELECT 
  database,
  numbackends,
  xact_commit,
  xact_rollback,
  conflicts,
  deadlocks
FROM pg_stat_database
WHERE datname = '<database>';"

# STEP 10: Check for index locks
psql -h <host> -U <user> -d <database> -c "
SELECT 
  l.pid,
  a.query,
  i.relname,
  l.mode,
  l.granted
FROM pg_locks l
JOIN pg_class i ON i.oid = l.relation
JOIN pg_stat_activity a ON a.pid = l.pid
WHERE i.relkind = 'i';"

# STEP 11: Monitor blocking in real-time
while true; do
  psql -h <host> -U <user> -d <database> -c "
  SELECT 
    blocking.pid,
    blocked.pid,
    blocked.query
  FROM pg_stat_activity blocked
  JOIN pg_stat_activity blocking ON blocking.pid = ANY(pg_blocking_pids(blocked.pid))
  WHERE blocked.pid != blocking.pid;"
  sleep 2
done

# STEP 12: Review recent deadlock events
psql -h <host> -U <user> -d <database> -c "
SELECT 
  database,
  deadlocks,
  EXTRACT(EPOCH FROM (now() - stats_reset)) as seconds_since_reset
FROM pg_stat_database
WHERE datname = '<database>';"
```

#### PostgreSQL Replication and HA Diagnostics

```bash
# STEP 1: Check if replication is configured
psql -h <host> -U <user> -d postgres -c "SHOW wal_level;"
# Should be: replica or logical

# STEP 2: Get replication slot information (primary)
psql -h <host> -U <user> -d postgres -c "
SELECT 
  slot_name,
  slot_type,
  active,
  restart_lsn,
  confirmed_flush_lsn
FROM pg_replication_slots;"

# STEP 3: Check primary WAL location
psql -h <host> -U <user> -d postgres -c "SELECT pg_current_wal_lsn();"

# STEP 4: Check replica WAL received position
psql -h <replica-host> -U <user> -d postgres -c "SELECT pg_last_wal_receive_lsn();"

# STEP 5: Check replica WAL replayed position
psql -h <replica-host> -U <user> -d postgres -c "SELECT pg_last_wal_replay_lsn();"

# STEP 6: Calculate replication lag
psql -h <replica-host> -U <user> -d postgres -c "
SELECT 
  CASE 
    WHEN pg_last_wal_receive_lsn() = pg_last_wal_replay_lsn() THEN 0
    ELSE EXTRACT(EPOCH FROM now() - pg_last_xact_replay_timestamp())
  END as lag_seconds;"

# STEP 7: Check standby application name
psql -h <primary-host> -U <user> -d postgres -c "
SELECT 
  client_addr,
  application_name,
  state,
  sync_state,
  replay_lag
FROM pg_stat_replication;"

# STEP 8: Check streaming replication status
psql -h <replica-host> -U <user> -d postgres -c "
SELECT 
  pg_is_in_recovery() as in_recovery,
  pg_is_wal_replay_paused() as wal_replay_paused;"

# STEP 9: Pause WAL replay (recovery)
psql -h <replica-host> -U <user> -d postgres -c "SELECT pg_wal_replay_pause();"
# Resume: SELECT pg_wal_replay_resume();

# STEP 10: Check replication lag statistics
psql -h <primary-host> -U <user> -d postgres -c "
SELECT 
  usename,
  application_name,
  client_addr,
  state,
  write_lag,
  flush_lag,
  replay_lag
FROM pg_stat_replication;"

# STEP 11: Create replication slot (for high-availability)
psql -h <primary-host> -U <user> -d postgres -c "
SELECT * FROM pg_create_physical_replication_slot('<slot_name>');"

# STEP 12: Monitor replication continuously
while true; do
  psql -h <primary-host> -U <user> -d postgres -c "
  SELECT 
    client_addr,
    state,
    replay_lag,
    flush_lag
  FROM pg_stat_replication;"
  sleep 5
done
```

#### PostgreSQL Backup and Recovery

```bash
# STEP 1: Get database backup start point
psql -h <host> -U <user> -d postgres -c "SELECT pg_start_backup('backup_label');"
# Note: Old method; use pg_basebackup instead

# STEP 2: Perform basebackup (modern method)
pg_basebackup \
  -h <host> \
  -U <user> \
  -D ./backup \
  -Ft \
  -z \
  -v \
  -P

# STEP 3: Backup specific database with pg_dump
pg_dump \
  -h <host> \
  -U <user> \
  -d <database> \
  -Fc > backup-$(date +%Y%m%d).dump
# -Fc: Custom format (compressed, faster restore)

# STEP 4: Backup all databases
pg_dumpall \
  -h <host> \
  -U <user> \
  | gzip > full-backup-$(date +%Y%m%d).sql.gz

# STEP 5: Backup specific schema only
pg_dump \
  -h <host> \
  -U <user> \
  -d <database> \
  -n <schema> \
  -Fc > schema-backup-$(date +%Y%m%d).dump

# STEP 6: Parallel backup (faster)
pg_dump \
  -h <host> \
  -U <user> \
  -d <database> \
  -j 4 \
  -Fd \
  -f ./backup
# -j 4: Use 4 parallel jobs
# -Fd: Directory format

# STEP 7: Test backup integrity
pg_restore \
  --list backup-file.dump | head -20
# Shows: What would be restored

# STEP 8: Restore full backup
pg_restore \
  -h <host> \
  -U <user> \
  -d <database> \
  backup-$(date +%Y%m%d).dump

# STEP 9: Restore with verbose logging
pg_restore \
  -h <host> \
  -U <user> \
  -d <database> \
  -v \
  --single-transaction \
  backup.dump

# STEP 10: Point-in-time recovery (PITR)
# Requires: wal_level = replica, continuous archiving enabled
# Edit recovery.conf:
cat > /var/lib/postgresql/14/main/recovery.conf << EOF
restore_command = 'cp /path/to/wal_archive/%f %p'
recovery_target_timeline = 'latest'
recovery_target_name = 'my_backup_point'
recovery_target_inclusive = true
EOF

# STEP 11: Resume WAL archiving after recovery
psql -U postgres -c "SELECT pg_wal_replay_resume();"

# STEP 12: Verify restore completion
psql -h <host> -U <user> -d <database> -c "
SELECT 
  datname,
  count(*) as table_count
FROM pg_tables
WHERE schemaname NOT IN ('pg_catalog', 'information_schema')
GROUP BY datname;"
```

#### PostgreSQL Configuration Tuning

```bash
# STEP 1: Get all configuration parameters
psql -h <host> -U <user> -d postgres -c "SHOW ALL;"

# STEP 2: Tune shared_buffers (25% of system memory)
psql -h <host> -U <user> -d postgres -c "
ALTER SYSTEM SET shared_buffers = '16GB';"
# Requires restart

# STEP 3: Tune effective_cache_size (50-75% of system memory)
psql -h <host> -U <user> -d postgres -c "
ALTER SYSTEM SET effective_cache_size = '48GB';"

# STEP 4: Tune work_mem (for complex queries)
psql -h <host> -U <user> -d postgres -c "
ALTER SYSTEM SET work_mem = '256MB';"

# STEP 5: Tune maintenance_work_mem (for VACUUM, ANALYZE)
psql -h <host> -U <user> -d postgres -c "
ALTER SYSTEM SET maintenance_work_mem = '4GB';"

# STEP 6: Tune max_wal_size (for faster recovery)
psql -h <host> -U <user> -d postgres -c "
ALTER SYSTEM SET max_wal_size = '10GB';"

# STEP 7: Enable parallel query execution
psql -h <host> -U <user> -d postgres -c "
ALTER SYSTEM SET max_parallel_workers_per_gather = 4;
ALTER SYSTEM SET max_parallel_workers = 8;"

# STEP 8: Configure vacuum settings
psql -h <host> -U <user> -d postgres -c "
ALTER SYSTEM SET autovacuum = on;
ALTER SYSTEM SET autovacuum_naptime = '10s';
ALTER SYSTEM SET autovacuum_vacuum_threshold = 50;
ALTER SYSTEM SET autovacuum_analyze_threshold = 50;"

# STEP 9: Set query planning timeout (prevent long-running plans)
psql -h <host> -U <user> -d postgres -c "
ALTER SYSTEM SET statement_timeout = '300000';"  # 5 minutes

# STEP 10: Configure logging
psql -h <host> -U <user> -d postgres -c "
ALTER SYSTEM SET log_statement = 'all';
ALTER SYSTEM SET log_duration = on;
ALTER SYSTEM SET log_min_duration_statement = 1000;"  # Log queries > 1 second

# STEP 11: Apply configuration changes
pg_ctl reload -D /var/lib/postgresql/14/main
# Or full restart if required

# STEP 12: Verify configuration applied
psql -h <host> -U <user> -d postgres -c "SHOW shared_buffers;"
```

#### PostgreSQL User and Permissions Management

```bash
# STEP 1: Create database user with login
psql -h <host> -U <user> -d postgres -c "
CREATE USER app_user WITH PASSWORD '<strong-password>';"

# STEP 2: Create read-only user
psql -h <host> -U <user> -d postgres -c "
CREATE USER readonly WITH PASSWORD '<password>';"

# STEP 3: Grant database privileges
psql -h <host> -U <user> -d postgres -c "
GRANT CONNECT ON DATABASE <database> TO app_user;
GRANT USAGE ON SCHEMA public TO app_user;
GRANT SELECT ON ALL TABLES IN SCHEMA public TO app_user;"

# STEP 4: Create replication user
psql -h <host> -U <user> -d postgres -c "
CREATE USER repl_user WITH REPLICATION ENCRYPTED PASSWORD '<password>';"

# STEP 5: List all users and roles
psql -h <host> -U <user> -d postgres -c "\du"

# STEP 6: Check user privileges on database
psql -h <host> -U <user> -d postgres -c "
SELECT * FROM information_schema.table_privileges
WHERE grantee = 'app_user';"

# STEP 7: Grant table-specific privileges
psql -h <host> -U <user> -d <database> -c "
GRANT SELECT, INSERT, UPDATE, DELETE ON <table> TO app_user;"

# STEP 8: Create role with inheritance
psql -h <host> -U <user> -d postgres -c "
CREATE ROLE developer INHERIT;
GRANT developer TO app_user;"

# STEP 9: Revoke privileges
psql -h <host> -U <user> -d postgres -c "
REVOKE INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public FROM app_user;"

# STEP 10: Set default privileges for future tables
psql -h <host> -U <user> -d <database> -c "
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT SELECT ON TABLES TO readonly;"

# STEP 11: Force password change
psql -h <host> -U <user> -d postgres -c "
ALTER USER app_user WITH PASSWORD '<new-password>' VALID UNTIL '2026-12-31';"

# STEP 12: Audit user activity
psql -h <host> -U <user> -d postgres -c "
SELECT 
  usename,
  usesuper,
  usecreatedb,
  usecanlogin,
  valuntil
FROM pg_user
ORDER BY usename;"
```

#### PostgreSQL Maintenance and Optimization

```bash
# STEP 1: Run VACUUM (reclaim space, update statistics)
psql -h <host> -U <user> -d <database> -c "VACUUM ANALYZE <table>;"

# STEP 2: Aggressive VACUUM (more I/O intensive)
psql -h <host> -U <user> -d <database> -c "VACUUM FULL <table>;"

# STEP 3: Analyze query planner statistics
psql -h <host> -U <user> -d <database> -c "ANALYZE <table>;"

# STEP 4: Reindex table (maintenance)
psql -h <host> -U <user> -d <database> -c "REINDEX TABLE <table>;"

# STEP 5: Check table bloat
psql -h <host> -U <user> -d <database> -c "
SELECT 
  schemaname,
  tablename,
  pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) as total_size,
  pg_size_pretty(pg_relation_size(schemaname||'.'||tablename)) as table_size,
  pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename) - pg_relation_size(schemaname||'.'||tablename)) as index_size
FROM pg_tables
WHERE schemaname NOT IN ('pg_catalog', 'information_schema')
ORDER BY pg_total_relation_size(schemaname||'.'||tablename) DESC
LIMIT 20;"

# STEP 6: Monitor autovacuum activity
psql -h <host> -U <user> -d <database> -c "
SELECT 
  schemaname,
  relname,
  last_vacuum,
  last_autovacuum,
  n_dead_tup
FROM pg_stat_user_tables
ORDER BY n_dead_tup DESC;"

# STEP 7: Check disk space usage
psql -h <host> -U <user> -d postgres -c "
SELECT 
  datname,
  pg_size_pretty(pg_database_size(datname)) as size
FROM pg_database
ORDER BY pg_database_size(datname) DESC;"

# STEP 8: Cluster table by index (improves performance)
# WARNING: Locks table; use during maintenance window
psql -h <host> -U <user> -d <database> -c "CLUSTER <table> USING <index>;"

# STEP 9: Monitor table statistics
psql -h <host> -U <user> -d <database> -c "
SELECT 
  schemaname,
  tablename,
  seq_scan,
  seq_tup_read,
  idx_scan,
  n_tup_ins,
  n_tup_upd,
  n_tup_del
FROM pg_stat_user_tables
ORDER BY seq_scan DESC;"

# STEP 10: Check extension status
psql -h <host> -U <user> -d <database> -c "SELECT * FROM pg_extension;"

# STEP 11: Install contrib extensions for advanced monitoring
psql -h <host> -U <user> -d <database> -c "
CREATE EXTENSION IF NOT EXISTS pg_stat_statements;
CREATE EXTENSION IF NOT EXISTS pgstattuple;
CREATE EXTENSION IF NOT EXISTS pg_trgm;"

# STEP 12: Monitor long-running autovacuum
psql -h <host> -U <user> -d postgres -c "
SELECT 
  pid,
  usename,
  query,
  query_start,
  state
FROM pg_stat_activity
WHERE query LIKE '%autovacuum%';"
```

#### Commands to NEVER use in production

```bash
# ❌ NEVER: DROP TABLE <table>;
#    Permanent data loss; hard to recover
# ❌ NEVER: TRUNCATE TABLE without backup
#    Fast removal; recovery dependent on WAL
# ❌ NEVER: VACUUM FULL in production during business hours
#    Locks entire table; application downtime
# ❌ NEVER: ALTER TABLE ALTER COLUMN TYPE on huge tables
#    Table-wide rewrite; very slow operation
# ❌ NEVER: DROP DATABASE without backup
#    Complete data loss; unrecoverable
# ❌ NEVER: pg_ctl stop -m immediate
#    Potential data corruption; use smart or fast
# ❌ NEVER: Change wal_level without restart and testing
#    Replication breaks; data inconsistency
# ❌ NEVER: Edit postgresql.conf and forget to reload
#    Settings not applied; debugging nightmare
# ❌ NEVER: Share database passwords in code/Git
#    Credentials exposed; compromised forever
```

---

## Database Comparison and Selection Guide

### MySQL vs PostgreSQL Production Considerations

| Factor | MySQL | PostgreSQL |
|--------|-------|------------|
| **Reliability** | Good; InnoDB ACID compliant | Excellent; full ACID, stronger consistency |
| **Performance** | Fast for reads; good for web apps | Strong for complex queries; better at scale |
| **Replication** | Simple binary log replication | Logical/physical streaming replication |
| **Backup** | mysqldump, Percona XtraBackup | pg_basebackup, pg_dump |
| **Locking** | Table-level (MyISAM), row-level (InnoDB) | Row-level, MVCC |
| **Query Optimization** | Good for simple queries | Excellent query planner; complex queries |
| **Extensions** | Limited | Rich extension ecosystem |
| **JSON Support** | Basic | Advanced (JSONB) |
| **Full-Text Search** | Built-in | Built-in; more features |
| **Administration** | Simpler; fewer tuning options | More complex; more control |
| **Community** | Larger; more hosting providers | Smaller but very dedicated; growing |
| **Licensing** | Open-source (GPL) | Open-source (PostgreSQL License) |

### Database Sizing and Resource Planning

```
Estimate Resources Based On:
1. Data size: 1TB = 2-3TB disk (with indexes, logs)
2. Connections: Formula = (CPU_cores × 4) + buffer
3. Memory: MySQL buffer_pool 70-80%, PostgreSQL shared_buffers 25%
4. CPU: I/O-bound vs compute-bound workload assessment
5. Disk I/O: SSD recommended; 3x write throughput needed
6. Replication lag: Function of write rate, network, CPU
```

---

## Critical Database Debugging Principles

### Database Operations Best Practices

1. **Read-Only First**: Always start with read-only diagnostics
2. **Backup Before Change**: Verify backup before any modifications
3. **Test in Staging**: All configuration changes tested first
4. **Monitor Baseline**: Establish normal performance metrics
5. **Document Changes**: Every change logged with business reason
6. **Gradual Tuning**: Tune one variable at a time; measure impact
7. **Slow Query Logging**: Always enabled in production
8. **Replication Monitoring**: Watch lag, errors continuously
9. **Capacity Planning**: Plan for 2-3x current growth
10. **Disaster Recovery**: Tested, documented, executable procedures

### Database Incident Response Checklist

```
Initial Assessment:
- [ ] Assess impact: all users, single app, read-only vs writes
- [ ] Check error logs for root cause indication
- [ ] Verify recent changes (deployments, config, data loads)
- [ ] Confirm backup availability and integrity

Diagnostics:
- [ ] Connection count vs limits
- [ ] Query performance: slow log analysis
- [ ] Lock status: active locks and waits
- [ ] Replication status: lag, errors
- [ ] Disk space: disk usage, WAL size
- [ ] Memory pressure: swap usage, buffer pool
- [ ] I/O metrics: read/write rates, latency

Mitigation:
- [ ] Kill long-running queries
- [ ] Resolve lock contention
- [ ] Increase resources if capacity issue
- [ ] Failover if primary unavailable
- [ ] Apply urgent patches if security issue

Recovery:
- [ ] Monitor after mitigation
- [ ] Verify data consistency
- [ ] Test replication catch-up
- [ ] Document incident and lessons learned
```

### Common Database Issues Quick Reference

| Issue | MySQL Diagnosis | PostgreSQL Diagnosis | Quick Fix |
|-------|-----------------|----------------------|-----------|
| Slow queries | EXPLAIN, slow log | EXPLAIN ANALYZE, pg_stat_statements | Add index, optimize query |
| High CPU | SHOW PROCESSLIST, iostat | pg_stat_activity, pg_stat_statements | Kill query, increase resources |
| Lock timeout | SHOW ENGINE INNODB STATUS | pg_locks, pg_stat_activity | Kill blocking query, increase timeout |
| Replication lag | SHOW SLAVE STATUS | pg_stat_replication | Scale replica, optimize queries |
| Connection pool exhaustion | SHOW STATUS LIKE 'Threads%' | SELECT count(*) FROM pg_stat_activity | Add connection pooling |
| Disk space | df -h, show table sizes | pg_database_size() | Vacuum/cleanup old logs, add disk |
| Memory pressure | SHOW STATUS LIKE '%buffer%' | pg_statio_user_tables | Tune buffer/cache sizes |
| Backup failure | Check backup logs, size | Check pg_basebackup errors | Verify disk space, network |

---

## Performance Benchmarking Tools

### Load Testing Databases

```bash
# MySQL Load Testing
# Using mysqlslap:
mysqlslap \
  --host=<host> \
  --user=<user> \
  --password=<password> \
  --concurrency=50 \
  --number-of-queries=10000 \
  --iterations=5 \
  --create-schema=<database>

# PostgreSQL Load Testing
# Using pgbench:
pgbench -i -s 10 -d <database> -U <user> -h <host>
pgbench \
  -c 50 \
  -j 10 \
  -T 300 \
  -d <database> \
  -U <user> \
  -h <host>

# Generic: Apache JMeter with database plugin
jmeter -n -t test.jmx -l results.jtl
```

---

## Database Internals: Must-Know Commands (Prod Safe Defaults)

### MySQL InnoDB + Performance Schema

```bash
# Top statements by total time (Performance Schema)
mysql -e "SELECT digest_text, ROUND(SUM_TIMER_WAIT/1e6,2) AS total_ms, COUNT_STAR AS execs \
FROM performance_schema.events_statements_summary_by_digest \
ORDER BY SUM_TIMER_WAIT DESC LIMIT 10\G"

# Current locks / blockers
mysql -e "SHOW ENGINE INNODB STATUS\G" | egrep -i "LATEST DETECTED DEADLOCK|WAITING|WE ROLL BACK"

# Thread + connection pressure
mysql -e "SHOW GLOBAL STATUS WHERE Variable_name IN ('Threads_running','Threads_connected','Max_used_connections')\G"

# Replication health (primary/replica)
mysql -e "SHOW REPLICA STATUS\G"  # MySQL 8+
# Legacy:
mysql -e "SHOW SLAVE STATUS\G"

# Binary log retention + size
mysql -e "SHOW BINARY LOGS;"
mysql -e "SHOW VARIABLES LIKE 'binlog_expire_logs_seconds';"
```

### PostgreSQL Internals (pg_stat*)

```bash
# Long-running + blocked queries
psql -c "SELECT pid, now()-query_start AS runtime, wait_event_type, wait_event, state, query \
FROM pg_stat_activity WHERE state <> 'idle' ORDER BY runtime DESC LIMIT 15;"

# Lock graph (who blocks whom)
psql -c "SELECT bl.pid AS blocked_pid, a.usename AS blocked_user, kl.pid AS blocking_pid, ka.query AS blocking_query \
FROM pg_locks bl JOIN pg_stat_activity a ON bl.pid = a.pid \
JOIN pg_locks kl ON bl.locktype = kl.locktype AND bl.database = kl.database AND bl.relation = kl.relation AND bl.pid <> kl.pid \
JOIN pg_stat_activity ka ON kl.pid = ka.pid WHERE NOT bl.granted;"

# Statement stats (requires pg_stat_statements)
psql -c "SELECT query, calls, total_time/1000 AS total_s, mean_time AS avg_ms \
FROM pg_stat_statements ORDER BY total_time DESC LIMIT 10;"

# WAL and replication lag
psql -c "SELECT pg_size_pretty(pg_xlog_location_diff(pg_current_wal_lsn(), replay_lsn)) AS replication_lag \
FROM pg_stat_replication;"
psql -c "SELECT * FROM pg_stat_wal LIMIT 10;"

# Buffer/cache pressure
psql -c "SELECT checkpoints_req, buffers_checkpoint, buffers_clean, buffers_backend FROM pg_stat_bgwriter;"
```

### Performance-Safe EXPLAIN and Observability

```bash
# Postgres: execution plan with buffers
psql -c "EXPLAIN (ANALYZE, BUFFERS) <QUERY>;"

# MySQL: json format for clarity
mysql -e "EXPLAIN FORMAT=JSON <QUERY>\G"

# Capture query sample for offline review
pt-query-digest /var/log/mysql/slow.log --output slowlog > /tmp/slowlog.digest
```

### Security + Hardening Checks

```bash
# MySQL: check users without passwords / with wildcard hosts
mysql -e "SELECT user, host, plugin, password_last_changed FROM mysql.user WHERE authentication_string='';"
mysql -e "SELECT user, host FROM mysql.user WHERE host = '%';"

# Postgres: roles with superuser or replication
psql -c "SELECT rolname, rolsuper, rolreplication FROM pg_roles WHERE rolsuper OR rolreplication;"

# TLS / auth posture (MySQL example)
mysql -e "SHOW VARIABLES LIKE 'require_secure_transport';"
mysql -e "SHOW GLOBAL VARIABLES LIKE 'validate_password%';"
```

---

## Documentation and References

**MySQL Official**
- Server Documentation: https://dev.mysql.com/doc/
- Reference Manual: https://dev.mysql.com/doc/refman/8.0/en/
- Performance Tuning: https://dev.mysql.com/doc/refman/8.0/en/optimization.html

**PostgreSQL Official**
- Server Documentation: https://www.postgresql.org/docs/
- Query Performance: https://www.postgresql.org/docs/current/using-explain.html
- Monitoring: https://www.postgresql.org/docs/current/monitoring.html

**Tools and Extensions**
- Percona XtraBackup: https://www.percona.com/mysql-backup-tools/percona-xtrabackup
- pg_stat_statements: https://www.postgresql.org/docs/current/pgstatstatements.html
- Percona Monitoring: https://www.percona.com/

**Replication and HA**
- MySQL Replication: https://dev.mysql.com/doc/refman/8.0/en/replication.html
- PostgreSQL Replication: https://www.postgresql.org/docs/current/warm-standby.html
- pgBackRest: https://pgbackrest.org/

---

**Last Updated**: January 2026  
**Databases Covered**: MySQL 5.7+, 8.0+ | PostgreSQL 12+, 14+, 15+  
**Severity Level**: Production Critical  
**Review Frequency**: Monthly (with database release cycles)
