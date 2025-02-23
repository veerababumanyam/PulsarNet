"""Retention Policy Module for PulsarNet.

This module defines the RetentionPolicy class that manages backup retention rules
and cleanup operations for stored backup files.
"""

from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import Enum
from pathlib import Path
from typing import List, Optional

class RetentionType(Enum):
    """Enumeration of supported retention types."""
    TIME_BASED = "time_based"  # Keep backups for specified time period
    COUNT_BASED = "count_based"  # Keep specified number of backups
    HYBRID = "hybrid"  # Combination of time and count based

@dataclass
class RetentionRule:
    """Configuration for a retention rule."""
    retention_type: RetentionType
    max_age_days: Optional[int] = None  # For time-based retention
    max_count: Optional[int] = None  # For count-based retention
    min_count: Optional[int] = None  # Minimum backups to keep for hybrid retention

class RetentionPolicy:
    """Class for managing backup retention policies."""

    def __init__(self, name: str, rule: RetentionRule):
        """Initialize a retention policy.

        Args:
            name: Unique identifier for the policy
            rule: Retention rule configuration
        """
        self.name = name
        self.rule = rule
        self._validate_rule()

    def _validate_rule(self) -> None:
        """Validate the retention rule configuration.

        Raises:
            ValueError: If the rule configuration is invalid
        """
        if self.rule.retention_type == RetentionType.TIME_BASED:
            if not self.rule.max_age_days or self.rule.max_age_days <= 0:
                raise ValueError("Time-based retention requires positive max_age_days")

        elif self.rule.retention_type == RetentionType.COUNT_BASED:
            if not self.rule.max_count or self.rule.max_count <= 0:
                raise ValueError("Count-based retention requires positive max_count")

        elif self.rule.retention_type == RetentionType.HYBRID:
            if not self.rule.max_age_days or self.rule.max_age_days <= 0:
                raise ValueError("Hybrid retention requires positive max_age_days")
            if not self.rule.max_count or self.rule.max_count <= 0:
                raise ValueError("Hybrid retention requires positive max_count")
            if self.rule.min_count and self.rule.min_count > self.rule.max_count:
                raise ValueError("Minimum count cannot exceed maximum count")

    async def get_files_to_delete(self, backup_files: List[Path]) -> List[Path]:
        """Determine which backup files should be deleted based on the retention policy.

        Args:
            backup_files: List of backup file paths to evaluate

        Returns:
            List of file paths that should be deleted
        """
        if not backup_files:
            return []

        # Sort files by modification time, newest first
        sorted_files = sorted(
            backup_files,
            key=lambda f: f.stat().st_mtime,
            reverse=True
        )

        if self.rule.retention_type == RetentionType.TIME_BASED:
            return await self._apply_time_based_retention(sorted_files)
        elif self.rule.retention_type == RetentionType.COUNT_BASED:
            return await self._apply_count_based_retention(sorted_files)
        else:  # HYBRID
            return await self._apply_hybrid_retention(sorted_files)

    async def _apply_time_based_retention(self, files: List[Path]) -> List[Path]:
        """Apply time-based retention rules.

        Args:
            files: List of backup files sorted by modification time

        Returns:
            List of files to delete
        """
        cutoff_time = datetime.now() - timedelta(days=self.rule.max_age_days)
        return [f for f in files if datetime.fromtimestamp(f.stat().st_mtime) < cutoff_time]

    async def _apply_count_based_retention(self, files: List[Path]) -> List[Path]:
        """Apply count-based retention rules.

        Args:
            files: List of backup files sorted by modification time

        Returns:
            List of files to delete
        """
        if len(files) <= self.rule.max_count:
            return []
        return files[self.rule.max_count:]

    async def _apply_hybrid_retention(self, files: List[Path]) -> List[Path]:
        """Apply hybrid retention rules.

        Args:
            files: List of backup files sorted by modification time

        Returns:
            List of files to delete
        """
        # First apply time-based retention
        time_based_deletions = await self._apply_time_based_retention(files)
        
        # Then ensure we don't delete too many files
        remaining_count = len(files) - len(time_based_deletions)
        min_count = self.rule.min_count or 1

        if remaining_count < min_count:
            # Keep the newest files to meet minimum count
            files_to_keep = set(files[:min_count])
            return [f for f in time_based_deletions if f not in files_to_keep]

        return time_based_deletions

    def to_dict(self) -> dict:
        """Convert retention policy to dictionary representation.

        Returns:
            Dictionary containing retention policy configuration
        """
        return {
            "name": self.name,
            "retention_type": self.rule.retention_type.value,
            "max_age_days": self.rule.max_age_days,
            "max_count": self.rule.max_count,
            "min_count": self.rule.min_count
        }