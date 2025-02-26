-- PulsarNet Database Schema

-- Clean up if exists (for development)
-- DROP TABLE IF EXISTS devices;
-- DROP TABLE IF EXISTS device_groups;
-- DROP TABLE IF EXISTS backups;
-- DROP TABLE IF EXISTS schedules;
-- DROP TABLE IF EXISTS logs;
-- DROP TABLE IF EXISTS settings;
-- DROP TABLE IF EXISTS device_templates;
-- DROP TABLE IF EXISTS audit_logs;
-- DROP TABLE IF EXISTS performance_metrics;

-- Devices table
CREATE TABLE IF NOT EXISTS devices (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL UNIQUE,
    ip_address TEXT NOT NULL,
    device_type TEXT NOT NULL,
    username TEXT,
    password TEXT,
    enable_password TEXT,
    connection_type TEXT DEFAULT 'ssh',
    port INTEGER DEFAULT 22,
    use_jump_server BOOLEAN DEFAULT 0,
    jump_server TEXT,
    jump_username TEXT,
    jump_password TEXT,
    backup_enabled BOOLEAN DEFAULT 1,
    verify_backup BOOLEAN DEFAULT 1,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_backup_time TIMESTAMP,
    last_backup_status TEXT,
    last_backup_path TEXT,
    notes TEXT
);

-- Device Groups table
CREATE TABLE IF NOT EXISTS device_groups (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL UNIQUE,
    description TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Device Group Mappings table (many-to-many)
CREATE TABLE IF NOT EXISTS device_group_mappings (
    device_id INTEGER NOT NULL,
    group_id INTEGER NOT NULL,
    PRIMARY KEY (device_id, group_id),
    FOREIGN KEY (device_id) REFERENCES devices(id) ON DELETE CASCADE,
    FOREIGN KEY (group_id) REFERENCES device_groups(id) ON DELETE CASCADE
);

-- Backups table
CREATE TABLE IF NOT EXISTS backups (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    device_id INTEGER NOT NULL,
    backup_type TEXT NOT NULL,
    file_path TEXT NOT NULL,
    file_size INTEGER,
    checksum TEXT,
    verification_status TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    notes TEXT,
    FOREIGN KEY (device_id) REFERENCES devices(id) ON DELETE CASCADE
);

-- Schedule table
CREATE TABLE IF NOT EXISTS schedules (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    description TEXT,
    schedule_type TEXT NOT NULL, -- daily, weekly, monthly, custom
    priority INTEGER DEFAULT 1,
    enabled BOOLEAN DEFAULT 1,
    start_time TEXT, -- HH:MM format
    days_of_week TEXT, -- comma-separated list of days (0-6, 0 is Monday)
    days_of_month TEXT, -- comma-separated list of days (1-31)
    months TEXT, -- comma-separated list of months (1-12)
    last_run TIMESTAMP,
    next_run TIMESTAMP,
    target_type TEXT NOT NULL, -- 'device', 'group', or 'all'
    target_id INTEGER, -- device_id or group_id, NULL for 'all'
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (target_id) REFERENCES devices(id) ON DELETE CASCADE
);

-- Logs table
CREATE TABLE IF NOT EXISTS logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    level TEXT NOT NULL,
    source TEXT NOT NULL,
    message TEXT NOT NULL,
    details TEXT
);

-- Audit logs table
CREATE TABLE IF NOT EXISTS audit_logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    user TEXT NOT NULL,
    action TEXT NOT NULL,
    target_type TEXT NOT NULL,
    target_id INTEGER,
    details TEXT
);

-- Settings table
CREATE TABLE IF NOT EXISTS settings (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    category TEXT NOT NULL,
    key TEXT NOT NULL,
    value TEXT,
    description TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(category, key)
);

-- Device Templates table
CREATE TABLE IF NOT EXISTS device_templates (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    device_type TEXT NOT NULL UNIQUE,
    backup_commands TEXT NOT NULL, -- JSON format
    connection_settings TEXT NOT NULL, -- JSON format
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Performance Metrics table
CREATE TABLE IF NOT EXISTS performance_metrics (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    operation TEXT NOT NULL,
    target_id INTEGER,
    target_type TEXT,
    duration_ms INTEGER NOT NULL,
    status TEXT NOT NULL,
    details TEXT
);

-- Default Settings
INSERT OR IGNORE INTO settings (category, key, value, description) 
VALUES 
    ('backup', 'storage_path', './backups', 'Default backup storage path'),
    ('backup', 'retention_days', '90', 'Default backup retention period in days'),
    ('backup', 'max_concurrent_backups', '5', 'Maximum number of concurrent backup operations'),
    ('backup', 'verify_backups', '1', 'Default setting for backup verification'),
    ('connection', 'default_timeout', '30', 'Default connection timeout in seconds'),
    ('connection', 'default_retry', '3', 'Default number of connection retries'),
    ('connection', 'default_retry_delay', '5', 'Default delay between retries in seconds'),
    ('logging', 'log_level', 'INFO', 'Default log level'),
    ('logging', 'log_file', './logs/pulsarnet.log', 'Default log file path'),
    ('logging', 'max_log_size', '10485760', 'Maximum log file size in bytes (10MB)'),
    ('logging', 'backup_count', '5', 'Number of log files to keep'),
    ('logging', 'console_logging', '1', 'Enable console logging'),
    ('logging', 'detailed_logging', '0', 'Enable detailed logging for debugging'),
    ('logging', 'syslog_enabled', '0', 'Enable syslog forwarding'),
    ('logging', 'syslog_server', '', 'Syslog server address'),
    ('logging', 'syslog_port', '514', 'Syslog server port'),
    ('logging', 'syslog_protocol', 'UDP', 'Syslog protocol (UDP/TCP)'),
    ('gui', 'theme', 'system', 'GUI theme (system, light, dark)'),
    ('performance', 'max_workers', '10', 'Maximum number of worker threads'),
    ('security', 'encrypt_credentials', '1', 'Enable encryption of stored credentials'),
    ('security', 'encryption_key_path', './keys/encryption.key', 'Path to the encryption key file');

-- Indexes for performance
CREATE INDEX IF NOT EXISTS idx_devices_name ON devices(name);
CREATE INDEX IF NOT EXISTS idx_devices_ip ON devices(ip_address);
CREATE INDEX IF NOT EXISTS idx_devices_type ON devices(device_type);
CREATE INDEX IF NOT EXISTS idx_device_groups_name ON device_groups(name);
CREATE INDEX IF NOT EXISTS idx_backups_device_id ON backups(device_id);
CREATE INDEX IF NOT EXISTS idx_backups_created_at ON backups(created_at);
CREATE INDEX IF NOT EXISTS idx_schedules_next_run ON schedules(next_run);
CREATE INDEX IF NOT EXISTS idx_schedules_target ON schedules(target_type, target_id);
CREATE INDEX IF NOT EXISTS idx_logs_timestamp ON logs(timestamp);
CREATE INDEX IF NOT EXISTS idx_logs_level ON logs(level);
CREATE INDEX IF NOT EXISTS idx_logs_source ON logs(source);
CREATE INDEX IF NOT EXISTS idx_settings_category_key ON settings(category, key);
CREATE INDEX IF NOT EXISTS idx_audit_logs_timestamp ON audit_logs(timestamp);
CREATE INDEX IF NOT EXISTS idx_audit_logs_user ON audit_logs(user);
CREATE INDEX IF NOT EXISTS idx_audit_logs_action ON audit_logs(action);
CREATE INDEX IF NOT EXISTS idx_performance_metrics_timestamp ON performance_metrics(timestamp);
CREATE INDEX IF NOT EXISTS idx_performance_metrics_operation ON performance_metrics(operation); 