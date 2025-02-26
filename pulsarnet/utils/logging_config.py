"""Enhanced logging configuration for PulsarNet.

This module provides advanced logging configuration options including:
- File-based logging with rotation
- Console logging
- Syslog forwarding
- Audit logging
- Performance metrics logging
"""

import os
import sys
import logging
import logging.handlers
import datetime
import json
import socket
import threading
import time
from typing import Dict, Any, Optional, List, Tuple
from pathlib import Path

from ..database.db_manager import DatabaseManager


# Custom log levels
AUDIT = 25  # Between INFO and WARNING
METRIC = 15  # Between DEBUG and INFO

# Register custom log levels
logging.addLevelName(AUDIT, "AUDIT")
logging.addLevelName(METRIC, "METRIC")


class AuditLogger:
    """Logger for audit events."""
    
    def __init__(self, db_manager: Optional[DatabaseManager] = None):
        """Initialize the audit logger.
        
        Args:
            db_manager: Optional database manager. If None, a new one will be created.
        """
        self.db = db_manager
        self.logger = logging.getLogger("pulsarnet.audit")
        self._user = os.environ.get("USERNAME", "system")
        
    async def initialize(self, db_manager: DatabaseManager = None):
        """Initialize the audit logger.
        
        Args:
            db_manager: Database manager to use.
        """
        if db_manager:
            self.db = db_manager
    
    async def log_action(self, action: str, target_type: str, target_id: Optional[int] = None, 
                    details: Optional[Dict] = None, user: Optional[str] = None):
        """Log an audit event.
        
        Args:
            action: Action being performed
            target_type: Type of object being acted upon
            target_id: ID of object being acted upon
            details: Additional details about the action
            user: User performing the action. If None, uses current user.
        """
        if user is None:
            user = self._user
            
        if details is not None and not isinstance(details, str):
            details = json.dumps(details)
            
        # Log to audit_logs table if db is available
        if self.db:
            try:
                await self.db.execute_query(
                    "INSERT INTO audit_logs (user, action, target_type, target_id, details) "
                    "VALUES (?, ?, ?, ?, ?)",
                    (user, action, target_type, target_id, details)
                )
            except Exception as e:
                self.logger.error(f"Failed to write audit log to database: {e}")
        
        # Also log to normal logger
        audit_msg = f"AUDIT: {user} performed {action} on {target_type}"
        if target_id is not None:
            audit_msg += f" (ID: {target_id})"
        
        if details:
            audit_msg += f" - {details}"
            
        self.logger.log(AUDIT, audit_msg)


class MetricLogger:
    """Logger for performance metrics."""
    
    def __init__(self, db_manager: Optional[DatabaseManager] = None):
        """Initialize the metric logger.
        
        Args:
            db_manager: Optional database manager. If None, a new one will be created.
        """
        self.db = db_manager
        self.logger = logging.getLogger("pulsarnet.metrics")
        self._timers = {}
        self._lock = threading.Lock()
        
    async def initialize(self, db_manager: DatabaseManager = None):
        """Initialize the metric logger.
        
        Args:
            db_manager: Database manager to use.
        """
        if db_manager:
            self.db = db_manager
    
    def start_timer(self, operation: str, target_id: Optional[int] = None, 
                   target_type: Optional[str] = None) -> str:
        """Start a timer for an operation.
        
        Args:
            operation: Name of the operation
            target_id: ID of the target
            target_type: Type of the target
            
        Returns:
            str: Timer ID
        """
        timer_id = f"{operation}_{target_type}_{target_id}_{time.time()}"
        with self._lock:
            self._timers[timer_id] = {
                'start_time': time.time(),
                'operation': operation,
                'target_id': target_id,
                'target_type': target_type
            }
        return timer_id
    
    async def end_timer(self, timer_id: str, status: str = "success", details: Optional[Dict] = None):
        """End a timer and record the metric.
        
        Args:
            timer_id: Timer ID returned from start_timer
            status: Status of the operation
            details: Additional details
        """
        with self._lock:
            if timer_id not in self._timers:
                self.logger.warning(f"Timer {timer_id} not found")
                return
                
            timer_data = self._timers.pop(timer_id)
            
        duration_ms = int((time.time() - timer_data['start_time']) * 1000)
        operation = timer_data['operation']
        target_id = timer_data['target_id']
        target_type = timer_data['target_type']
        
        if details is not None and not isinstance(details, str):
            details = json.dumps(details)
            
        # Log to performance_metrics table if db is available
        if self.db:
            try:
                await self.db.execute_query(
                    "INSERT INTO performance_metrics (operation, target_id, target_type, duration_ms, status, details) "
                    "VALUES (?, ?, ?, ?, ?, ?)",
                    (operation, target_id, target_type, duration_ms, status, details)
                )
            except Exception as e:
                self.logger.error(f"Failed to write performance metric to database: {e}")
        
        # Also log to normal logger
        metric_msg = f"METRIC: {operation} took {duration_ms}ms ({status})"
        if target_type and target_id:
            metric_msg += f" on {target_type} ID {target_id}"
            
        self.logger.log(METRIC, metric_msg)
        
        return duration_ms


class SysLogHandler(logging.handlers.SysLogHandler):
    """Enhanced SysLogHandler with better formatting."""
    
    def __init__(self, address=('localhost', 514), facility=logging.handlers.SysLogHandler.LOG_USER, 
                 socktype=socket.SOCK_DGRAM, hostname=None, app_name="pulsarnet"):
        """Initialize SysLogHandler with enhanced formatting.
        
        Args:
            address: Syslog server address
            facility: Syslog facility
            socktype: Socket type (SOCK_DGRAM for UDP, SOCK_STREAM for TCP)
            hostname: Hostname to use in syslog messages
            app_name: Application name to use in syslog messages
        """
        super().__init__(address, facility, socktype)
        self.hostname = hostname or socket.gethostname()
        self.app_name = app_name
        
    def format(self, record):
        """Format the record with RFC5424 format."""
        # Get the formatted message
        message = super().format(record)
        
        # RFC5424 format: <PRI>VERSION TIMESTAMP HOSTNAME APP-NAME PROCID MSGID SD MSG
        pri = self.encodePriority(self.facility, self.mapPriority(record.levelname))
        timestamp = datetime.datetime.fromtimestamp(record.created).isoformat()
        procid = record.process
        msgid = record.thread
        
        # Format the message
        msg = f"<{pri}>1 {timestamp} {self.hostname} {self.app_name} {procid} {msgid} - {message}"
        return msg


class LoggingManager:
    """Manager for application logging."""
    
    def __init__(self, db_manager: Optional[DatabaseManager] = None):
        """Initialize the logging manager.
        
        Args:
            db_manager: Optional database manager. If None, a new one will be created.
        """
        self.db = db_manager
        self.root_logger = logging.getLogger()
        self.app_logger = logging.getLogger("pulsarnet")
        self.audit_logger = AuditLogger(db_manager)
        self.metric_logger = MetricLogger(db_manager)
        self.handlers = []
        self._settings = {}
        
    async def initialize(self, db_manager: Optional[DatabaseManager] = None):
        """Initialize the logging manager with settings from the database.
        
        Args:
            db_manager: Database manager to use. If None, uses the one provided at initialization.
        """
        if db_manager:
            self.db = db_manager
            
        if self.db:
            await self.db.initialize()
            await self.audit_logger.initialize(self.db)
            await self.metric_logger.initialize(self.db)
            
            # Load settings from database
            settings = await self.db.execute_query(
                "SELECT key, value FROM settings WHERE category = 'logging'"
            )
            
            for key, value in settings:
                self._settings[key] = value
        
        await self.configure_logging()
    
    async def configure_logging(self):
        """Configure logging based on settings."""
        # Clear existing handlers
        for handler in self.root_logger.handlers[:]:
            self.root_logger.removeHandler(handler)
            
        # Set default log level
        log_level_str = self._settings.get('log_level', 'INFO')
        log_level = getattr(logging, log_level_str)
        self.root_logger.setLevel(log_level)
        self.app_logger.setLevel(log_level)
        
        # Add console handler if enabled
        if self._settings.get('console_logging', '1') == '1':
            console_handler = logging.StreamHandler(sys.stdout)
            console_formatter = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            )
            console_handler.setFormatter(console_formatter)
            self.root_logger.addHandler(console_handler)
            self.handlers.append(console_handler)
        
        # Add file handler
        log_file = self._settings.get('log_file', './logs/pulsarnet.log')
        log_dir = os.path.dirname(log_file)
        os.makedirs(log_dir, exist_ok=True)
        
        max_size = int(self._settings.get('max_log_size', 10 * 1024 * 1024))  # Default 10MB
        backup_count = int(self._settings.get('backup_count', 5))
        
        file_handler = logging.handlers.RotatingFileHandler(
            log_file, maxBytes=max_size, backupCount=backup_count
        )
        
        detailed_logging = self._settings.get('detailed_logging', '0') == '1'
        if detailed_logging:
            file_formatter = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(filename)s:%(lineno)d - %(funcName)s - %(message)s'
            )
        else:
            file_formatter = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            )
            
        file_handler.setFormatter(file_formatter)
        self.root_logger.addHandler(file_handler)
        self.handlers.append(file_handler)
        
        # Add syslog handler if enabled
        if self._settings.get('syslog_enabled', '0') == '1':
            syslog_server = self._settings.get('syslog_server', 'localhost')
            syslog_port = int(self._settings.get('syslog_port', 514))
            syslog_protocol = self._settings.get('syslog_protocol', 'UDP')
            
            socktype = socket.SOCK_DGRAM if syslog_protocol.upper() == 'UDP' else socket.SOCK_STREAM
            
            try:
                syslog_handler = SysLogHandler(
                    address=(syslog_server, syslog_port),
                    facility=logging.handlers.SysLogHandler.LOG_LOCAL0,
                    socktype=socktype
                )
                
                syslog_formatter = logging.Formatter('%(name)s[%(process)d]: %(levelname)s - %(message)s')
                syslog_handler.setFormatter(syslog_formatter)
                self.root_logger.addHandler(syslog_handler)
                self.handlers.append(syslog_handler)
                
                self.app_logger.info(f"Configured syslog forwarding to {syslog_server}:{syslog_port} via {syslog_protocol}")
            except Exception as e:
                self.app_logger.error(f"Failed to configure syslog handler: {e}")
        
        # Add database handler
        if self.db:
            self.app_logger.info("Configured database logging")
        
        self.app_logger.info(f"Logging configured with level {log_level_str}")
        
    def get_logger(self, name: str) -> logging.Logger:
        """Get a logger with the given name.
        
        Args:
            name: Logger name
            
        Returns:
            logging.Logger: Logger instance
        """
        return logging.getLogger(f"pulsarnet.{name}")
    
    async def set_log_level(self, level: str):
        """Set the log level for all handlers.
        
        Args:
            level: Log level name (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        """
        if hasattr(logging, level):
            log_level = getattr(logging, level)
            self.root_logger.setLevel(log_level)
            for handler in self.handlers:
                handler.setLevel(log_level)
                
            if self.db:
                await self.db.execute_query(
                    "UPDATE settings SET value = ? WHERE category = 'logging' AND key = 'log_level'",
                    (level,)
                )
                
            self.app_logger.info(f"Log level set to {level}")
        else:
            self.app_logger.error(f"Invalid log level: {level}")
    
    async def audit(self, action: str, target_type: str, target_id: Optional[int] = None, 
                   details: Optional[Dict] = None, user: Optional[str] = None):
        """Log an audit event.
        
        Args:
            action: Action being performed
            target_type: Type of object being acted upon
            target_id: ID of object being acted upon
            details: Additional details about the action
            user: User performing the action
        """
        await self.audit_logger.log_action(action, target_type, target_id, details, user)
    
    def start_metric(self, operation: str, target_id: Optional[int] = None, 
                    target_type: Optional[str] = None) -> str:
        """Start a performance metric timer.
        
        Args:
            operation: Name of the operation
            target_id: ID of the target
            target_type: Type of the target
            
        Returns:
            str: Timer ID
        """
        return self.metric_logger.start_timer(operation, target_id, target_type)
    
    async def end_metric(self, timer_id: str, status: str = "success", details: Optional[Dict] = None):
        """End a performance metric timer and record it.
        
        Args:
            timer_id: Timer ID returned from start_metric
            status: Status of the operation
            details: Additional details
        """
        return await self.metric_logger.end_timer(timer_id, status, details)


# Initialize module-level logging objects
logging_manager = LoggingManager()

# Helper methods for auditing common operations
async def audit_device_created(device_id: int, device_name: str, user: Optional[str] = None):
    """Audit a device creation event."""
    await logging_manager.audit(
        action="create",
        target_type="device",
        target_id=device_id,
        details={"name": device_name},
        user=user
    )

async def audit_device_updated(device_id: int, device_name: str, user: Optional[str] = None):
    """Audit a device update event."""
    await logging_manager.audit(
        action="update",
        target_type="device",
        target_id=device_id,
        details={"name": device_name},
        user=user
    )

async def audit_device_deleted(device_id: int, device_name: str, user: Optional[str] = None):
    """Audit a device deletion event."""
    await logging_manager.audit(
        action="delete",
        target_type="device",
        target_id=device_id,
        details={"name": device_name},
        user=user
    )

async def audit_backup_created(backup_id: int, device_id: int, device_name: str, user: Optional[str] = None):
    """Audit a backup creation event."""
    await logging_manager.audit(
        action="create",
        target_type="backup",
        target_id=backup_id,
        details={"device_id": device_id, "device_name": device_name},
        user=user
    )

async def audit_configuration_changed(category: str, key: str, value: str, user: Optional[str] = None):
    """Audit a configuration change event."""
    await logging_manager.audit(
        action="update",
        target_type="configuration",
        details={"category": category, "key": key, "value": value},
        user=user
    )


# Helper function to create a logger for a module
def get_logger(name: str) -> logging.Logger:
    """Get a logger for a module.
    
    Args:
        name: Module name
        
    Returns:
        logging.Logger: Logger instance
    """
    return logging.getLogger(f"pulsarnet.{name}") 