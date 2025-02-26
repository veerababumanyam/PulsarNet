"""Backup Job Module for PulsarNet.

This module handles individual backup operations, including progress tracking,
status management, and error handling for each backup task.
"""

from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Optional, Dict, Any
from pathlib import Path

class BackupStatus(Enum):
    """Enumeration of possible backup job states."""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    VERIFIED = "verified"

@dataclass
class BackupProgress:
    """Class for tracking backup operation progress."""
    total_bytes: int = 0
    transferred_bytes: int = 0
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    current_phase: str = "initializing"
    error_message: Optional[str] = None

    @property
    def duration(self) -> Optional[float]:
        """Calculate the duration of the backup operation in seconds."""
        if self.start_time and self.end_time:
            return (self.end_time - self.start_time).total_seconds()
        return None

    @property
    def percentage_complete(self) -> float:
        """Calculate the percentage of backup completion."""
        if self.total_bytes == 0:
            return 0.0
        return (self.transferred_bytes / self.total_bytes) * 100

class BackupJob:
    """Class representing an individual backup operation."""

    def __init__(
        self,
        device_ip: str,
        protocol_type: str,
        backup_path: Path,
        config: Dict[str, Any]
    ):
        self.job_id = f"{device_ip}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        self.device_ip = device_ip
        self.protocol_type = protocol_type
        self.backup_path = backup_path
        self.config = config
        self.status = BackupStatus.PENDING
        self.progress = BackupProgress()
        self.result: Dict[str, Any] = {}
        
        # Additional device details for better logging and tracking
        self.device_name = config.get('device_name', '')
        self.device_type = config.get('device_type', '')

    async def start(self) -> None:
        """Start the backup operation."""
        self.status = BackupStatus.IN_PROGRESS
        self.progress.start_time = datetime.now()
        self.progress.current_phase = "connecting"

    async def update_progress(self, transferred: int, total: int, phase: str) -> None:
        """Update the progress of the backup operation.

        Args:
            transferred: Number of bytes transferred.
            total: Total number of bytes to transfer.
            phase: Current phase of the backup operation.
        """
        self.progress.transferred_bytes = transferred
        self.progress.total_bytes = total
        self.progress.current_phase = phase

    def complete(self, success: bool, error_message: Optional[str] = None) -> None:
        """Mark the backup job as complete.

        Args:
            success: Whether the backup was successful.
            error_message: Error message if the backup failed.
        """
        self.progress.end_time = datetime.now()
        if success:
            self.status = BackupStatus.COMPLETED
        else:
            self.status = BackupStatus.FAILED
            self.progress.error_message = error_message

    def verify(self, verified: bool) -> None:
        """Mark the backup as verified.

        Args:
            verified: Whether the backup was verified successfully.
        """
        if verified and self.status == BackupStatus.COMPLETED:
            self.status = BackupStatus.VERIFIED

    def to_dict(self) -> Dict[str, Any]:
        """Convert the backup job to a dictionary for serialization."""
        return {
            "job_id": self.job_id,
            "device_ip": self.device_ip,
            "protocol_type": self.protocol_type,
            "backup_path": str(self.backup_path),
            "status": self.status.value,
            "progress": {
                "total_bytes": self.progress.total_bytes,
                "transferred_bytes": self.progress.transferred_bytes,
                "start_time": self.progress.start_time.isoformat() if self.progress.start_time else None,
                "end_time": self.progress.end_time.isoformat() if self.progress.end_time else None,
                "current_phase": self.progress.current_phase,
                "error_message": self.progress.error_message
            },
            "result": self.result
        }