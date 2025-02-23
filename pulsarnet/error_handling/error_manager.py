"""Error Manager Module for PulsarNet.

This module provides comprehensive error handling and recovery mechanisms,
including error classification, automatic recovery strategies, and integration
with the monitoring system.
"""

from typing import Dict, List, Optional, Callable, Any
from enum import Enum
from dataclasses import dataclass
from datetime import datetime
from ..monitoring.monitor_manager import MonitorManager, MonitoringLevel

class ErrorSeverity(Enum):
    """Enum for different error severity levels."""
    LOW = 1      # Minor issues that don't affect core functionality
    MEDIUM = 2   # Issues that affect some features but allow continued operation
    HIGH = 3     # Serious issues that require immediate attention
    CRITICAL = 4 # System-threatening issues that require immediate shutdown

class ErrorCategory(Enum):
    """Enum for different categories of errors."""
    NETWORK = "network"
    STORAGE = "storage"
    AUTHENTICATION = "authentication"
    PERMISSION = "permission"
    CONFIGURATION = "configuration"
    RESOURCE = "resource"
    SYSTEM = "system"
    BACKUP = "backup"
    RECOVERY = "recovery"

@dataclass
class ErrorEvent:
    """Class representing an error event."""
    timestamp: datetime
    category: ErrorCategory
    severity: ErrorSeverity
    message: str
    details: Optional[Dict] = None
    operation_id: Optional[str] = None
    recovery_attempts: int = 0
    resolved: bool = False

class ErrorManager:
    """Class for managing error handling and recovery operations."""

    def __init__(self, monitor_manager: MonitorManager):
        """Initialize the error manager.

        Args:
            monitor_manager: Instance of MonitorManager for event reporting
        """
        self.monitor_manager = monitor_manager
        self.active_errors: Dict[str, ErrorEvent] = {}
        self.error_history: List[ErrorEvent] = []
        self.recovery_strategies: Dict[ErrorCategory, List[Callable]] = {}
        self.max_recovery_attempts = 3

    def register_recovery_strategy(self, category: ErrorCategory,
                                 strategy: Callable) -> None:
        """Register a recovery strategy for a specific error category.

        Args:
            category: Category of errors the strategy handles
            strategy: Function implementing the recovery strategy
        """
        if category not in self.recovery_strategies:
            self.recovery_strategies[category] = []
        self.recovery_strategies[category].append(strategy)

    def handle_error(self, category: ErrorCategory, severity: ErrorSeverity,
                    message: str, details: Optional[Dict] = None,
                    operation_id: Optional[str] = None) -> str:
        """Handle a new error event.

        Args:
            category: Category of the error
            severity: Severity level of the error
            message: Error description
            details: Additional error details
            operation_id: ID of the related operation if any

        Returns:
            str: ID of the error event
        """
        error_id = f"{category.value}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        error_event = ErrorEvent(
            timestamp=datetime.now(),
            category=category,
            severity=severity,
            message=message,
            details=details,
            operation_id=operation_id
        )

        self.active_errors[error_id] = error_event
        self.error_history.append(error_event)

        # Report to monitoring system
        self.monitor_manager._add_event(
            MonitoringLevel.ERROR,
            f'error_{category.value}',
            message,
            {
                'error_id': error_id,
                'severity': severity.value,
                'operation_id': operation_id,
                **details if details else {}
            }
        )

        # Attempt recovery for non-critical errors
        if severity != ErrorSeverity.CRITICAL:
            self.attempt_recovery(error_id)

        return error_id

    def attempt_recovery(self, error_id: str) -> bool:
        """Attempt to recover from an error.

        Args:
            error_id: ID of the error to recover from

        Returns:
            bool: True if recovery was successful, False otherwise
        """
        if error_id not in self.active_errors:
            return False

        error = self.active_errors[error_id]
        if error.recovery_attempts >= self.max_recovery_attempts:
            return False

        strategies = self.recovery_strategies.get(error.category, [])
        for strategy in strategies:
            try:
                error.recovery_attempts += 1
                if strategy(error):
                    error.resolved = True
                    self._update_error_status(error_id, True)
                    return True
            except Exception as e:
                self.monitor_manager._add_event(
                    MonitoringLevel.ERROR,
                    'recovery_failed',
                    f'Recovery attempt failed: {str(e)}',
                    {'error_id': error_id, 'attempt': error.recovery_attempts}
                )

        self._update_error_status(error_id, False)
        return False

    def _update_error_status(self, error_id: str, resolved: bool) -> None:
        """Update the status of an error event.

        Args:
            error_id: ID of the error to update
            resolved: Whether the error was resolved
        """
        if error_id in self.active_errors:
            error = self.active_errors[error_id]
            error.resolved = resolved
            if resolved:
                del self.active_errors[error_id]

            self.monitor_manager._add_event(
                MonitoringLevel.INFO if resolved else MonitoringLevel.ERROR,
                'error_status_update',
                f'Error {"resolved" if resolved else "unresolved"}',
                {'error_id': error_id, 'attempts': error.recovery_attempts}
            )

    def get_active_errors(self) -> List[Dict[str, Any]]:
        """Get all currently active errors.

        Returns:
            List of active errors and their details
        """
        return [{
            'id': error_id,
            'category': error.category.value,
            'severity': error.severity.value,
            'message': error.message,
            'timestamp': error.timestamp.isoformat(),
            'recovery_attempts': error.recovery_attempts,
            'operation_id': error.operation_id,
            'details': error.details
        } for error_id, error in self.active_errors.items()]

    def get_error_history(self, category: Optional[ErrorCategory] = None,
                        severity: Optional[ErrorSeverity] = None) -> List[Dict[str, Any]]:
        """Get error history with optional filtering.

        Args:
            category: Filter by error category
            severity: Filter by error severity

        Returns:
            List of historical errors matching the filters
        """
        filtered_history = self.error_history
        if category:
            filtered_history = [e for e in filtered_history if e.category == category]
        if severity:
            filtered_history = [e for e in filtered_history if e.severity == severity]

        return [{
            'timestamp': error.timestamp.isoformat(),
            'category': error.category.value,
            'severity': error.severity.value,
            'message': error.message,
            'resolved': error.resolved,
            'recovery_attempts': error.recovery_attempts,
            'operation_id': error.operation_id,
            'details': error.details
        } for error in filtered_history]