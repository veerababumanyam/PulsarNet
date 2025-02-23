"""Audit Logger Module for PulsarNet.

This module provides comprehensive logging and audit trail functionality,
ensuring compliance with ISO standards for data protection and privacy.
"""

from typing import Dict, Optional
from datetime import datetime
import logging
import json
from pathlib import Path
from concurrent_log_handler import ConcurrentRotatingFileHandler
from .monitor_manager import MonitoringLevel

class AuditLogger:
    """Class for managing audit logging operations."""

    def __init__(self, log_dir: Path):
        """Initialize the audit logger.

        Args:
            log_dir: Directory for storing log files
        """
        self.log_dir = log_dir
        self.log_dir.mkdir(parents=True, exist_ok=True)

        # Setup main application logger
        self.app_logger = logging.getLogger('pulsarnet')
        self.app_logger.setLevel(logging.DEBUG)

        # Setup audit logger
        self.audit_logger = logging.getLogger('pulsarnet.audit')
        self.audit_logger.setLevel(logging.INFO)

        self._setup_handlers()

    def _setup_handlers(self) -> None:
        """Configure logging handlers with rotation and formatting."""
        # Application log handler
        app_handler = ConcurrentRotatingFileHandler(
            filename=self.log_dir / 'pulsarnet.log',
            maxBytes=10 * 1024 * 1024,  # 10MB
            backupCount=5,
            encoding='utf-8'
        )
        app_handler.setFormatter(logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        ))
        self.app_logger.addHandler(app_handler)

        # Audit log handler
        audit_handler = ConcurrentRotatingFileHandler(
            filename=self.log_dir / 'audit.log',
            maxBytes=20 * 1024 * 1024,  # 20MB
            backupCount=10,
            encoding='utf-8'
        )
        audit_handler.setFormatter(logging.Formatter(
            '%(asctime)s - %(levelname)s - %(message)s'
        ))
        self.audit_logger.addHandler(audit_handler)

    def log_operation(self, operation_type: str, user: str,
                     details: Dict, level: MonitoringLevel = MonitoringLevel.INFO) -> None:
        """Log an operation with audit details.

        Args:
            operation_type: Type of operation being logged
            user: User performing the operation
            details: Operation details
            level: Monitoring level for the operation
        """
        audit_entry = {
            'timestamp': datetime.now().isoformat(),
            'operation_type': operation_type,
            'user': user,
            'details': details
        }

        self.audit_logger.log(
            self._get_log_level(level),
            json.dumps(audit_entry)
        )

    def log_security_event(self, event_type: str, user: str,
                          details: Dict, success: bool = True) -> None:
        """Log security-related events.

        Args:
            event_type: Type of security event
            user: User involved in the event
            details: Event details
            success: Whether the security event was successful
        """
        security_entry = {
            'timestamp': datetime.now().isoformat(),
            'event_type': event_type,
            'user': user,
            'success': success,
            'details': details
        }

        level = logging.INFO if success else logging.WARNING
        self.audit_logger.log(level, json.dumps(security_entry))

    def log_error(self, error_type: str, message: str,
                  details: Optional[Dict] = None) -> None:
        """Log error events.

        Args:
            error_type: Type of error
            message: Error message
            details: Additional error details
        """
        error_entry = {
            'timestamp': datetime.now().isoformat(),
            'error_type': error_type,
            'message': message,
            'details': details or {}
        }

        self.app_logger.error(json.dumps(error_entry))

    def log_backup_event(self, device_ip: str, backup_type: str,
                        status: str, details: Dict) -> None:
        """Log backup-related events.

        Args:
            device_ip: IP of the device being backed up
            backup_type: Type of backup operation
            status: Status of the backup operation
            details: Backup operation details
        """
        backup_entry = {
            'timestamp': datetime.now().isoformat(),
            'device_ip': device_ip,
            'backup_type': backup_type,
            'status': status,
            'details': details
        }

        level = logging.INFO if status == 'success' else logging.ERROR
        self.app_logger.log(level, json.dumps(backup_entry))

    @staticmethod
    def _get_log_level(monitoring_level: MonitoringLevel) -> int:
        """Convert monitoring level to logging level.

        Args:
            monitoring_level: MonitoringLevel enum value

        Returns:
            Corresponding logging level
        """
        level_map = {
            MonitoringLevel.DEBUG: logging.DEBUG,
            MonitoringLevel.INFO: logging.INFO,
            MonitoringLevel.WARNING: logging.WARNING,
            MonitoringLevel.ERROR: logging.ERROR
        }
        return level_map.get(monitoring_level, logging.INFO)