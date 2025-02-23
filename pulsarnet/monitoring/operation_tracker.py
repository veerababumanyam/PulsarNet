"""Operation Tracker Module for PulsarNet.

This module provides detailed tracking of individual operations,
including performance metrics and status history.
"""

from typing import Dict, List, Optional
from datetime import datetime
from dataclasses import dataclass
from .monitor_manager import MonitoringLevel

@dataclass
class OperationMetrics:
    """Class for storing operation performance metrics."""
    start_time: datetime
    end_time: Optional[datetime] = None
    duration: Optional[float] = None
    bytes_processed: int = 0
    transfer_rate: Optional[float] = None

@dataclass
class StatusUpdate:
    """Class for tracking status changes."""
    timestamp: datetime
    status: str
    message: str
    progress: float

class OperationTracker:
    """Class for detailed operation tracking."""

    def __init__(self, operation_id: str, operation_type: str):
        """Initialize the operation tracker.

        Args:
            operation_id: Unique identifier for the operation
            operation_type: Type of operation being tracked
        """
        self.operation_id = operation_id
        self.operation_type = operation_type
        self.metrics = OperationMetrics(start_time=datetime.now())
        self.status_history: List[StatusUpdate] = []
        self.current_status = 'initialized'
        self.error_count = 0
        self.warning_count = 0

    def update_status(self, status: str, message: str, progress: float) -> None:
        """Update the operation status.

        Args:
            status: New status of the operation
            message: Status update message
            progress: Current progress percentage
        """
        update = StatusUpdate(
            timestamp=datetime.now(),
            status=status,
            message=message,
            progress=progress
        )
        self.status_history.append(update)
        self.current_status = status

    def update_metrics(self, bytes_processed: int) -> None:
        """Update operation metrics.

        Args:
            bytes_processed: Number of bytes processed so far
        """
        self.metrics.bytes_processed = bytes_processed
        if self.metrics.end_time:
            duration = (self.metrics.end_time - self.metrics.start_time).total_seconds()
            self.metrics.transfer_rate = bytes_processed / duration if duration > 0 else 0

    def complete_operation(self, success: bool) -> None:
        """Mark the operation as complete.

        Args:
            success: Whether the operation was successful
        """
        self.metrics.end_time = datetime.now()
        self.metrics.duration = (
            self.metrics.end_time - self.metrics.start_time
        ).total_seconds()
        
        final_status = 'completed' if success else 'failed'
        self.update_status(
            status=final_status,
            message=f'Operation {final_status}',
            progress=100.0 if success else -1.0
        )

    def add_error(self, message: str) -> None:
        """Record an error occurrence.

        Args:
            message: Error message
        """
        self.error_count += 1
        self.update_status('error', message, -1.0)

    def add_warning(self, message: str) -> None:
        """Record a warning occurrence.

        Args:
            message: Warning message
        """
        self.warning_count += 1
        self.update_status('warning', message, -1.0)

    def get_summary(self) -> Dict:
        """Get a summary of the operation.

        Returns:
            Dictionary containing operation summary
        """
        return {
            'operation_id': self.operation_id,
            'type': self.operation_type,
            'current_status': self.current_status,
            'start_time': self.metrics.start_time,
            'end_time': self.metrics.end_time,
            'duration': self.metrics.duration,
            'bytes_processed': self.metrics.bytes_processed,
            'transfer_rate': self.metrics.transfer_rate,
            'error_count': self.error_count,
            'warning_count': self.warning_count,
            'status_updates': len(self.status_history)
        }

    def get_status_history(self) -> List[Dict]:
        """Get the complete status history.

        Returns:
            List of status updates
        """
        return [{
            'timestamp': update.timestamp,
            'status': update.status,
            'message': update.message,
            'progress': update.progress
        } for update in self.status_history]