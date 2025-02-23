"""Monitor Manager Module for PulsarNet.

This module manages real-time monitoring of backup operations,
system status, and performance metrics.
"""

from typing import Dict, List, Optional
from datetime import datetime
from enum import Enum
from dataclasses import dataclass

class MonitoringLevel(Enum):
    """Enum for different monitoring levels."""
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    DEBUG = "DEBUG"

@dataclass
class MonitoringEvent:
    """Class representing a monitoring event."""
    timestamp: datetime
    level: MonitoringLevel
    source: str
    message: str
    details: Optional[Dict] = None

class MonitorManager:
    """Class for managing monitoring operations."""

    def __init__(self):
        """Initialize the monitor manager."""
        self.active_operations: Dict[str, Dict] = {}
        self.event_history: List[MonitoringEvent] = []
        self.performance_metrics: Dict[str, float] = {}
        self._subscribers = []

    def register_operation(self, operation_id: str, operation_type: str, details: Dict) -> None:
        """Register a new operation for monitoring.

        Args:
            operation_id: Unique identifier for the operation
            operation_type: Type of operation (e.g., 'backup', 'verification')
            details: Additional operation details
        """
        self.active_operations[operation_id] = {
            'type': operation_type,
            'start_time': datetime.now(),
            'status': 'running',
            'progress': 0,
            'details': details
        }
        self._add_event(MonitoringLevel.INFO, 'operation_start',
                      f'Started {operation_type} operation', details)

    def update_operation_progress(self, operation_id: str, progress: float,
                                status: str = 'running', details: Optional[Dict] = None) -> None:
        """Update the progress of an operation.

        Args:
            operation_id: ID of the operation to update
            progress: Progress percentage (0-100)
            status: Current status of the operation
            details: Additional update details
        """
        if operation_id in self.active_operations:
            self.active_operations[operation_id].update({
                'progress': progress,
                'status': status,
                'last_update': datetime.now()
            })
            if details:
                self.active_operations[operation_id]['details'].update(details)

            self._notify_subscribers(operation_id)

    def complete_operation(self, operation_id: str, success: bool,
                         details: Optional[Dict] = None) -> None:
        """Mark an operation as complete.

        Args:
            operation_id: ID of the operation to complete
            success: Whether the operation was successful
            details: Additional completion details
        """
        if operation_id in self.active_operations:
            operation = self.active_operations[operation_id]
            operation.update({
                'status': 'completed' if success else 'failed',
                'end_time': datetime.now(),
                'success': success
            })
            if details:
                operation['details'].update(details)

            level = MonitoringLevel.INFO if success else MonitoringLevel.ERROR
            self._add_event(level, 'operation_complete',
                          f'Operation {operation["type"]} completed',
                          {'success': success, **operation})

            self._notify_subscribers(operation_id)

    def get_active_operations(self) -> List[Dict]:
        """Get all currently active operations.

        Returns:
            List of active operations and their details
        """
        return [{
            'id': op_id,
            **op_details
        } for op_id, op_details in self.active_operations.items()]

    def get_operation_status(self, operation_id: str) -> Optional[Dict]:
        """Get the status of a specific operation.

        Args:
            operation_id: ID of the operation to check

        Returns:
            Operation status and details if found, None otherwise
        """
        return self.active_operations.get(operation_id)

    def subscribe(self, callback) -> None:
        """Subscribe to monitoring updates.

        Args:
            callback: Function to call when updates occur
        """
        if callback not in self._subscribers:
            self._subscribers.append(callback)

    def unsubscribe(self, callback) -> None:
        """Unsubscribe from monitoring updates.

        Args:
            callback: Function to remove from subscribers
        """
        if callback in self._subscribers:
            self._subscribers.remove(callback)

    def _add_event(self, level: MonitoringLevel, source: str,
                   message: str, details: Optional[Dict] = None) -> None:
        """Add a new monitoring event.

        Args:
            level: Severity level of the event
            source: Source of the event
            message: Event description
            details: Additional event details
        """
        event = MonitoringEvent(
            timestamp=datetime.now(),
            level=level,
            source=source,
            message=message,
            details=details
        )
        self.event_history.append(event)

    def _notify_subscribers(self, operation_id: str) -> None:
        """Notify all subscribers of an operation update.

        Args:
            operation_id: ID of the updated operation
        """
        operation = self.active_operations[operation_id]
        for subscriber in self._subscribers:
            subscriber(operation_id, operation)