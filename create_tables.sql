-- Hikvision Bridge Database Schema

USE hikvision;

-- Events table: Store all access control events
CREATE TABLE IF NOT EXISTS events (
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
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Bridge status table: Track bridge uptime and status
CREATE TABLE IF NOT EXISTS bridge_status (
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
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Configuration table: Store system configuration
CREATE TABLE IF NOT EXISTS config (
    key_name VARCHAR(100) PRIMARY KEY,
    value TEXT NOT NULL,
    description TEXT,
    category VARCHAR(50),
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Insert default configuration
INSERT INTO config (key_name, value, description, category) VALUES
('device_ip', '192.168.1.128', 'Hikvision device IP address', 'device'),
('device_user', 'admin', 'Device username', 'device'),
('device_id', 'door1', 'Device identifier', 'device'),
('log_level', 'INFO', 'Logging level (DEBUG, INFO, WARNING, ERROR)', 'system'),
('data_retention_days', '90', 'Number of days to keep event data', 'system'),
('auto_backup_enabled', 'true', 'Enable automatic database backups', 'system')
ON DUPLICATE KEY UPDATE updated_at = CURRENT_TIMESTAMP;

-- Create views for quick stats
CREATE OR REPLACE VIEW event_stats_today AS
SELECT 
    COUNT(*) as total_events,
    COUNT(DISTINCT employee_no) as unique_users,
    COUNT(DISTINCT door_no) as doors_accessed,
    MIN(occur_time) as first_event,
    MAX(occur_time) as last_event
FROM events
WHERE DATE(occur_time) = CURDATE();

CREATE OR REPLACE VIEW event_stats_by_hour AS
SELECT 
    DATE(occur_time) as event_date,
    HOUR(occur_time) as event_hour,
    COUNT(*) as event_count,
    COUNT(DISTINCT employee_no) as unique_users
FROM events
WHERE occur_time >= DATE_SUB(NOW(), INTERVAL 7 DAY)
GROUP BY DATE(occur_time), HOUR(occur_time)
ORDER BY event_date DESC, event_hour DESC;

CREATE OR REPLACE VIEW top_users AS
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
LIMIT 20;

-- Show success message
SELECT 'Database schema created successfully!' as Status;
SELECT TABLE_NAME, TABLE_ROWS 
FROM information_schema.TABLES 
WHERE TABLE_SCHEMA = 'hikvision' 
AND TABLE_TYPE = 'BASE TABLE';
