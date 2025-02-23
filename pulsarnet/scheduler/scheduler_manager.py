"""Scheduler Manager Module for PulsarNet.

This module manages scheduling of backup operations, including recurring backups,
priority-based execution, and conflict resolution.
"""

from typing import Dict, List, Optional
from datetime import datetime, timedelta
from enum import Enum
from dataclasses import dataclass
from uuid import uuid4

class SchedulePriority(Enum):
    """Enum for different schedule priority levels."""
    LOW = 1
    MEDIUM = 2
    HIGH = 3
    CRITICAL = 4

@dataclass
class ScheduleConfig:
    """Configuration for a scheduled backup operation."""
    device_ids: List[str]
    protocol_type: str
    backup_type: str
    priority: SchedulePriority
    start_time: datetime
    interval_hours: Optional[int] = None
    max_retries: int = 3
    retry_delay_minutes: int = 15
    timeout_minutes: int = 60

@dataclass
class ScheduledTask:
    """Class representing a scheduled backup task."""
    task_id: str
    config: ScheduleConfig
    status: str
    last_run: Optional[datetime] = None
    next_run: Optional[datetime] = None
    retry_count: int = 0

class SchedulerManager:
    """Class for managing scheduled backup operations."""

    def __init__(self):
        """Initialize the scheduler manager."""
        self.scheduled_tasks: Dict[str, ScheduledTask] = {}
        self.running_tasks: Dict[str, str] = {}  # task_id -> operation_id mapping
        self._task_queue: List[str] = []

    def create_schedule(self, config: ScheduleConfig) -> str:
        """Create a new scheduled backup task.

        Args:
            config: Schedule configuration

        Returns:
            str: ID of the created schedule
        """
        task_id = str(uuid4())
        task = ScheduledTask(
            task_id=task_id,
            config=config,
            status='pending',
            next_run=config.start_time
        )
        self.scheduled_tasks[task_id] = task
        self._update_task_queue()
        return task_id

    def update_schedule(self, task_id: str, config: ScheduleConfig) -> bool:
        """Update an existing schedule configuration.

        Args:
            task_id: ID of the schedule to update
            config: New schedule configuration

        Returns:
            bool: True if update successful, False otherwise
        """
        if task_id not in self.scheduled_tasks:
            return False

        task = self.scheduled_tasks[task_id]
        task.config = config
        task.next_run = config.start_time
        self._update_task_queue()
        return True

    def delete_schedule(self, task_id: str) -> bool:
        """Delete a scheduled task.

        Args:
            task_id: ID of the schedule to delete

        Returns:
            bool: True if deletion successful, False otherwise
        """
        if task_id in self.scheduled_tasks:
            del self.scheduled_tasks[task_id]
            self._update_task_queue()
            return True
        return False

    def get_pending_tasks(self) -> List[ScheduledTask]:
        """Get all tasks that are due for execution.

        Returns:
            List[ScheduledTask]: List of tasks ready for execution
        """
        current_time = datetime.now()
        return [
            task for task in self.scheduled_tasks.values()
            if task.next_run and task.next_run <= current_time
            and task.status not in ['running', 'failed']
        ]

    def mark_task_complete(self, task_id: str, success: bool) -> None:
        """Mark a task as complete and update its next run time.

        Args:
            task_id: ID of the completed task
            success: Whether the task completed successfully
        """
        if task_id in self.scheduled_tasks:
            task = self.scheduled_tasks[task_id]
            task.last_run = datetime.now()
            
            if success:
                task.status = 'completed'
                task.retry_count = 0
                if task.config.interval_hours:
                    task.next_run = task.last_run + timedelta(hours=task.config.interval_hours)
                else:
                    task.status = 'finished'
            else:
                if task.retry_count < task.config.max_retries:
                    task.retry_count += 1
                    task.status = 'pending'
                    task.next_run = task.last_run + timedelta(minutes=task.config.retry_delay_minutes)
                else:
                    task.status = 'failed'

            if task_id in self.running_tasks:
                del self.running_tasks[task_id]

            self._update_task_queue()

    def get_task_status(self, task_id: str) -> Optional[Dict]:
        """Get the current status of a scheduled task.

        Args:
            task_id: ID of the task to check

        Returns:
            Optional[Dict]: Task status information if found, None otherwise
        """
        task = self.scheduled_tasks.get(task_id)
        if not task:
            return None

        return {
            'task_id': task.task_id,
            'status': task.status,
            'last_run': task.last_run.isoformat() if task.last_run else None,
            'next_run': task.next_run.isoformat() if task.next_run else None,
            'retry_count': task.retry_count,
            'priority': task.config.priority.value,
            'devices': task.config.device_ids
        }

    def _update_task_queue(self) -> None:
        """Update the priority-based task execution queue."""
        pending_tasks = self.get_pending_tasks()
        sorted_tasks = sorted(
            pending_tasks,
            key=lambda x: (x.config.priority.value, x.next_run or datetime.max)
        )
        self._task_queue = [task.task_id for task in sorted_tasks]