"""Enhanced logging configuration for PulsarNet.

This module provides a flexible logging configuration with multiple handlers,
rotation, and customizable log levels for better troubleshooting and auditing.
"""

import os
import sys
import logging
import logging.handlers
import json
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, Optional

# Define log levels
DEFAULT_CONSOLE_LEVEL = logging.INFO
DEFAULT_FILE_LEVEL = logging.DEBUG
DEFAULT_AUDIT_LEVEL = logging.INFO

class AuditFilter(logging.Filter):
    """Filter that only allows audit records to pass through."""
    
    def filter(self, record):
        """Check if record has audit attribute."""
        return getattr(record, 'audit', False)

class LoggingManager:
    """Manages logging configuration for the application."""
    
    def __init__(self):
        """Initialize the logging manager."""
        self._configured = False
        self.log_dir = os.path.expanduser("~/.pulsarnet/logs")
        self.audit_dir = os.path.join(self.log_dir, "audit")
        self.max_file_size = 10 * 1024 * 1024  # 10 MB
        self.backup_count = 5
        self.console_level = DEFAULT_CONSOLE_LEVEL
        self.file_level = DEFAULT_FILE_LEVEL
        self.audit_level = DEFAULT_AUDIT_LEVEL
        self.enabled_loggers = {}
        
    def configure(self, settings: Optional[Dict[str, Any]] = None):
        """Configure logging with the specified settings.
        
        Args:
            settings: Dictionary containing logging settings. If None, default settings are used.
        """
        if self._configured:
            return
            
        if settings:
            self._apply_settings(settings)
            
        # Create log directories
        os.makedirs(self.log_dir, exist_ok=True)
        os.makedirs(self.audit_dir, exist_ok=True)
        
        # Configure root logger
        root_logger = logging.getLogger()
        root_logger.setLevel(logging.DEBUG)  # Capture all logs, let handlers filter
        
        # Remove any existing handlers
        for handler in root_logger.handlers[:]:
            root_logger.removeHandler(handler)
        
        # Add console handler
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(self.console_level)
        console_formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        console_handler.setFormatter(console_formatter)
        root_logger.addHandler(console_handler)
        
        # Add file handler for normal logs
        log_file = os.path.join(self.log_dir, "pulsarnet.log")
        file_handler = logging.handlers.RotatingFileHandler(
            log_file,
            maxBytes=self.max_file_size,
            backupCount=self.backup_count
        )
        file_handler.setLevel(self.file_level)
        file_formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - [%(filename)s:%(lineno)d] - %(message)s'
        )
        file_handler.setFormatter(file_formatter)
        root_logger.addHandler(file_handler)
        
        # Add file handler for audit logs
        audit_file = os.path.join(self.audit_dir, "audit.log")
        audit_handler = logging.handlers.RotatingFileHandler(
            audit_file,
            maxBytes=self.max_file_size,
            backupCount=self.backup_count
        )
        audit_handler.setLevel(self.audit_level)
        audit_formatter = logging.Formatter(
            '%(asctime)s - %(name)s - AUDIT - %(message)s'
        )
        audit_handler.setFormatter(audit_formatter)
        
        # Add filter to audit handler
        audit_filter = AuditFilter()
        audit_handler.addFilter(audit_filter)
        root_logger.addHandler(audit_handler)
        
        # Add debug file handler (full debug logs)
        debug_file = os.path.join(self.log_dir, "debug.log")
        debug_handler = logging.handlers.RotatingFileHandler(
            debug_file,
            maxBytes=self.max_file_size,
            backupCount=self.backup_count
        )
        debug_handler.setLevel(logging.DEBUG)
        debug_formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - [%(filename)s:%(lineno)d] - %(message)s'
        )
        debug_handler.setFormatter(debug_formatter)
        root_logger.addHandler(debug_handler)
        
        # Configure component-specific loggers
        self._configure_component_loggers()
        
        self._configured = True
        logging.info("Logging system initialized")
    
    def _apply_settings(self, settings: Dict[str, Any]):
        """Apply settings from the provided dictionary.
        
        Args:
            settings: Dictionary containing logging settings
        """
        if 'log_dir' in settings:
            self.log_dir = settings['log_dir']
            self.audit_dir = os.path.join(self.log_dir, "audit")
            
        if 'max_file_size' in settings:
            self.max_file_size = settings['max_file_size']
            
        if 'backup_count' in settings:
            self.backup_count = settings['backup_count']
            
        if 'console_level' in settings:
            self.console_level = self._parse_level(settings['console_level'])
            
        if 'file_level' in settings:
            self.file_level = self._parse_level(settings['file_level'])
            
        if 'audit_level' in settings:
            self.audit_level = self._parse_level(settings['audit_level'])
            
        if 'enabled_loggers' in settings:
            self.enabled_loggers = settings['enabled_loggers']
    
    def _parse_level(self, level) -> int:
        """Parse a log level string to its integer value.
        
        Args:
            level: String or integer log level
            
        Returns:
            int: Logging level
        """
        if isinstance(level, int):
            return level
            
        level_map = {
            'debug': logging.DEBUG,
            'info': logging.INFO,
            'warning': logging.WARNING,
            'error': logging.ERROR,
            'critical': logging.CRITICAL
        }
        
        return level_map.get(level.lower(), logging.INFO)
    
    def _configure_component_loggers(self):
        """Configure loggers for specific application components."""
        for logger_name, config in self.enabled_loggers.items():
            logger = logging.getLogger(logger_name)
            level = self._parse_level(config.get('level', 'info'))
            logger.setLevel(level)
            
            # If propagate is set to False, add a specific handler for this logger
            if not config.get('propagate', True):
                logger.propagate = False
                
                handler = logging.StreamHandler()
                handler.setLevel(level)
                formatter = logging.Formatter(config.get('format', '%(asctime)s - %(name)s - %(levelname)s - %(message)s'))
                handler.setFormatter(formatter)
                logger.addHandler(handler)
    
    def get_audit_logger(self) -> logging.Logger:
        """Get a logger configured for audit records.
        
        Returns:
            logging.Logger: Logger for audit records
        """
        audit_logger = logging.getLogger('pulsarnet.audit')
        
        # Add audit attribute adapter
        old_factory = logging.getLogRecordFactory()
        
        def record_factory(*args, **kwargs):
            record = old_factory(*args, **kwargs)
            record.audit = True
            return record
        
        logging.setLogRecordFactory(record_factory)
        
        return audit_logger
    
    def log_audit_event(self, event_type: str, details: Dict[str, Any], username: Optional[str] = None):
        """Log an audit event.
        
        Args:
            event_type: Type of event (e.g., "login", "backup", "configuration_change")
            details: Dictionary with event details
            username: Username associated with the event
        """
        audit_logger = self.get_audit_logger()
        
        # Create audit record
        audit_record = {
            "timestamp": datetime.now().isoformat(),
            "event_type": event_type,
            "username": username or "system",
            "details": details
        }
        
        # Log event
        audit_logger.info(json.dumps(audit_record))
    
    def shutdown(self):
        """Shut down logging system, closing all handlers."""
        logging.shutdown()

# Create a singleton instance
logging_manager = LoggingManager()

def configure_logging(settings: Optional[Dict[str, Any]] = None):
    """Configure the logging system with the specified settings.
    
    Args:
        settings: Dictionary containing logging settings. If None, default settings are used.
    """
    logging_manager.configure(settings)

def log_audit_event(event_type: str, details: Dict[str, Any], username: Optional[str] = None):
    """Log an audit event.
    
    Args:
        event_type: Type of event (e.g., "login", "backup", "configuration_change")
        details: Dictionary with event details
        username: Username associated with the event
    """
    logging_manager.log_audit_event(event_type, details, username) 