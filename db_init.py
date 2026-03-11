"""
Database Auto-Initialization & Seeding
=======================================
Automatically creates the database, tables, views, and seed data
when the system detects they are missing.

Reads connection details from .env — no hardcoded credentials.
Designed to be idempotent: safe to run multiple times.
"""

import os
import logging
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)


def _get_connection_config():
    """Build MySQL connection config from .env variables."""
    config = {
        'host': os.getenv('DB_HOST', 'localhost'),
        'port': int(os.getenv('DB_PORT', 3306)),
        'user': os.getenv('DB_USER', 'root'),
        'password': os.getenv('DB_PASS', 'root'),
        'charset': 'utf8mb4',
        'collation': 'utf8mb4_unicode_ci',
    }
    db_socket = os.getenv('DB_SOCKET', '').strip()
    if db_socket:
        config['unix_socket'] = db_socket
    return config


def _get_db_name():
    return os.getenv('DB_NAME', 'hikvision')


# ─── SQL Definitions ────────────────────────────────────────────────────────

_CREATE_DATABASE = "CREATE DATABASE IF NOT EXISTS `{db}` CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci"

_TABLES = {
    'events': """
        CREATE TABLE IF NOT EXISTS `events` (
            id INT AUTO_INCREMENT PRIMARY KEY,
            device_ip VARCHAR(45) NOT NULL,
            device_id VARCHAR(50) NOT NULL,
            event_type VARCHAR(100) NOT NULL,
            event_state VARCHAR(50),
            occur_time DATETIME NOT NULL,
            employee_no VARCHAR(50),
            name VARCHAR(100),
            card_no VARCHAR(50),
            door_no INT,
            verify_no INT,
            verify_mode VARCHAR(50),
            major_event_type INT,
            sub_event_type INT,
            serial_no INT,
            mac_address VARCHAR(20),
            channel_id VARCHAR(10),
            protocol VARCHAR(20),
            port_no INT,
            device_name VARCHAR(100),
            card_type VARCHAR(50),
            card_reader_kind INT,
            attendance_status VARCHAR(50),
            mask VARCHAR(20),
            helmet VARCHAR(20),
            raw_json JSON,
            json_file_path VARCHAR(255),
            sync_status ENUM('pending', 'synced', 'failed') DEFAULT 'pending',
            sync_attempts INT DEFAULT 0,
            synced_at DATETIME NULL,
            sync_error TEXT NULL,
            webhook_response TEXT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            INDEX idx_occur_time (occur_time),
            INDEX idx_event_type (event_type),
            INDEX idx_employee (employee_no),
            INDEX idx_device (device_id),
            INDEX idx_door (door_no),
            INDEX idx_created (created_at),
            INDEX idx_sync_status (sync_status)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
    """,

    'bridge_status': """
        CREATE TABLE IF NOT EXISTS `bridge_status` (
            id INT AUTO_INCREMENT PRIMARY KEY,
            status ENUM('running', 'stopped', 'error', 'starting') NOT NULL,
            pid INT,
            started_at DATETIME,
            stopped_at DATETIME,
            error_message TEXT,
            uptime_seconds INT,
            events_processed INT DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            INDEX idx_status (status),
            INDEX idx_created (created_at)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
    """,

    'config': """
        CREATE TABLE IF NOT EXISTS `config` (
            key_name VARCHAR(100) PRIMARY KEY,
            value TEXT NOT NULL,
            description TEXT,
            category VARCHAR(50),
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
    """,
}

_VIEWS = {
    'event_stats_today': """
        CREATE OR REPLACE VIEW `event_stats_today` AS
        SELECT
            COUNT(*) as total_events,
            COUNT(DISTINCT employee_no) as unique_users,
            COUNT(DISTINCT door_no) as doors_accessed,
            MIN(occur_time) as first_event,
            MAX(occur_time) as last_event
        FROM events
        WHERE DATE(occur_time) = CURDATE()
    """,

    'event_stats_by_hour': """
        CREATE OR REPLACE VIEW `event_stats_by_hour` AS
        SELECT
            DATE(occur_time) as event_date,
            HOUR(occur_time) as event_hour,
            COUNT(*) as event_count,
            COUNT(DISTINCT employee_no) as unique_users
        FROM events
        WHERE occur_time >= DATE_SUB(NOW(), INTERVAL 7 DAY)
        GROUP BY DATE(occur_time), HOUR(occur_time)
        ORDER BY event_date DESC, event_hour DESC
    """,

    'top_users': """
        CREATE OR REPLACE VIEW `top_users` AS
        SELECT
            employee_no,
            name,
            COUNT(*) as access_count,
            MAX(occur_time) as last_access
        FROM events
        WHERE employee_no IS NOT NULL
          AND occur_time >= DATE_SUB(NOW(), INTERVAL 30 DAY)
        GROUP BY employee_no, name
        ORDER BY access_count DESC
        LIMIT 20
    """,
}

# Default config seed — values from .env override device_ip / device_user etc.
_SEED_CONFIG = [
    ('device_ip',           os.getenv('DEVICE_IP', '192.168.1.128'), 'Hikvision device IP address', 'device'),
    ('device_user',         os.getenv('DEVICE_USER', 'admin'),       'Device username',              'device'),
    ('device_id',           os.getenv('DEVICE_ID', 'door1'),         'Device identifier',            'device'),
    ('log_level',           os.getenv('LOG_LEVEL', 'INFO'),          'Logging level',                'system'),
    ('data_retention_days', '90',                                    'Days to keep event data',      'system'),
    ('auto_backup_enabled', 'true',                                  'Enable automatic backups',     'system'),
]


# ─── Public API ──────────────────────────────────────────────────────────────

def ensure_database():
    """
    Check if the database and all required tables exist.
    Creates anything that is missing. Idempotent — safe to call every startup.

    Returns:
        True if database is ready, False if initialisation failed.
    """
    import mysql.connector
    from mysql.connector import Error

    db_name = _get_db_name()
    config = _get_connection_config()

    # ── Step 1: Ensure the DATABASE itself exists ────────────────────────
    try:
        conn = mysql.connector.connect(**config)
        cursor = conn.cursor()
        cursor.execute(_CREATE_DATABASE.format(db=db_name))
        conn.commit()
        cursor.close()
        conn.close()
        logger.info(f"Database '{db_name}' verified/created")
    except Error as e:
        logger.error(f"Failed to create database '{db_name}': {e}")
        return False

    # ── Step 2: Connect to the target database ───────────────────────────
    try:
        config['database'] = db_name
        conn = mysql.connector.connect(**config)
        cursor = conn.cursor()
    except Error as e:
        logger.error(f"Cannot connect to database '{db_name}': {e}")
        return False

    try:
        # ── Step 3: Get existing tables ──────────────────────────────────
        cursor.execute("SHOW TABLES")
        existing_tables = {row[0] for row in cursor.fetchall()}

        created_tables = []
        for table_name, ddl in _TABLES.items():
            if table_name not in existing_tables:
                try:
                    cursor.execute(ddl)
                    conn.commit()
                    created_tables.append(table_name)
                    logger.info(f"Created table: {table_name}")
                except Error as e:
                    logger.error(f"Failed to create table '{table_name}': {e}")
                    return False

        # ── Step 4: Create/refresh views ─────────────────────────────────
        for view_name, ddl in _VIEWS.items():
            try:
                cursor.execute(ddl)
                conn.commit()
            except Error as e:
                logger.warning(f"Could not create view '{view_name}': {e}")

        # ── Step 5: Seed config (only for newly created config table) ────
        if 'config' in created_tables:
            _seed_config(cursor, conn)

        # ── Step 6: Report ───────────────────────────────────────────────
        if created_tables:
            logger.info(f"Database initialized — created tables: {', '.join(created_tables)}")
        else:
            logger.info("Database schema is up to date")

        return True

    except Error as e:
        logger.error(f"Database initialization error: {e}")
        return False
    finally:
        try:
            cursor.close()
            conn.close()
        except Exception:
            pass


def _seed_config(cursor, conn):
    """Insert default configuration rows (only when config table is freshly created)."""
    from mysql.connector import Error

    sql = """
        INSERT INTO config (key_name, value, description, category)
        VALUES (%s, %s, %s, %s)
        ON DUPLICATE KEY UPDATE updated_at = CURRENT_TIMESTAMP
    """
    seeded = 0
    for key_name, value, description, category in _SEED_CONFIG:
        try:
            cursor.execute(sql, (key_name, value, description, category))
            seeded += 1
        except Error as e:
            logger.warning(f"Could not seed config '{key_name}': {e}")

    # Also seed webhook config from .env if present
    webhook_url = os.getenv('WEBHOOK_URL', '').strip()
    if webhook_url:
        try:
            cursor.execute(sql, ('webhook_url', webhook_url, 'EHRMS webhook endpoint', 'webhook'))
            seeded += 1
        except Error:
            pass

    webhook_key = os.getenv('WEBHOOK_API_KEY', '').strip()
    if webhook_key:
        try:
            cursor.execute(sql, ('webhook_api_key', webhook_key, 'Webhook API key', 'webhook'))
            seeded += 1
        except Error:
            pass

    conn.commit()
    logger.info(f"Seeded {seeded} config entries")


# ─── Standalone usage ────────────────────────────────────────────────────────

if __name__ == '__main__':
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    print("\n  EHRMS Device Bridge — Database Initialization")
    print("  " + "=" * 48)
    print(f"  Host:     {os.getenv('DB_HOST', 'localhost')}")
    print(f"  Database: {_get_db_name()}")
    print(f"  User:     {os.getenv('DB_USER', 'root')}")
    print()

    ok = ensure_database()
    if ok:
        print("  ✓ Database is ready.\n")
    else:
        print("  ✗ Database initialization failed. Check logs above.\n")
        exit(1)
