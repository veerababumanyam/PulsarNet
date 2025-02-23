"""Scheduler Service Module for PulsarNet.

This module provides the service layer for executing scheduled backup tasks
and integrating with the backup and monitoring systems.
"""

from typing import Optional
from datetime import datetime
import asyncio
from .scheduler_manager import SchedulerManager, ScheduleConfig
from ..backup_operations.backup_manager import BackupManager
from ..monitoring.monitor_manager import MonitorManager, MonitoringLevel

class SchedulerService:
    """Service class for executing scheduled backup operations."""

    def __init__(self, scheduler_manager: SchedulerManager,
                 backup_manager: BackupManager,
                 monitor_manager: MonitorManager):
        """Initialize the scheduler service.

        Args:
            scheduler_manager: Instance of SchedulerManager
            backup_manager: Instance of BackupManager
            monitor_manager: Instance of MonitorManager
        """
        self.scheduler_manager = scheduler_manager
        self.backup_manager = backup_manager
        self.monitor_manager = monitor_manager
        self._running = False
        self._execution_task: Optional[asyncio.Task] = None

    async def start(self) -> None:
        """Start the scheduler service."""
        if self._running:
            return

        self._running = True
        self._execution_task = asyncio.create_task(self._execution_loop())
        self.monitor_manager._add_event(
            MonitoringLevel.INFO,
            'scheduler_service',
            'Scheduler service started'
        )

    async def stop(self) -> None:
        """Stop the scheduler service."""
        if not self._running:
            return

        self._running = False
        if self._execution_task:
            self._execution_task.cancel()
            try:
                await self._execution_task
            except asyncio.CancelledError:
                pass

        self.monitor_manager._add_event(
            MonitoringLevel.INFO,
            'scheduler_service',
            'Scheduler service stopped'
        )

    async def _execution_loop(self) -> None:
        """Main execution loop for processing scheduled tasks."""
        while self._running:
            try:
                pending_tasks = self.scheduler_manager.get_pending_tasks()
                for task in pending_tasks:
                    if task.task_id not in self.scheduler_manager.running_tasks:
                        await self._execute_task(task.task_id)

                await asyncio.sleep(60)  # Check every minute
            except Exception as e:
                self.monitor_manager._add_event(
                    MonitoringLevel.ERROR,
                    'scheduler_service',
                    f'Error in execution loop: {str(e)}'
                )
                await asyncio.sleep(60)  # Wait before retrying

    async def _execute_task(self, task_id: str) -> None:
        """Execute a scheduled backup task.

        Args:
            task_id: ID of the task to execute
        """
        task = self.scheduler_manager.scheduled_tasks.get(task_id)
        if not task:
            return

        try:
            # Create backup jobs for each device
            operation_ids = []
            for device_id in task.config.device_ids:
                job = self.backup_manager.create_backup_job(
                    device_id,
                    task.config.protocol_type,
                    {
                        'backup_type': task.config.backup_type,
                        'timeout': task.config.timeout_minutes * 60
                    }
                )
                operation_ids.append(job.job_id)
                await self.backup_manager.start_backup(job.job_id)

            # Monitor backup operations
            success = True
            for op_id in operation_ids:
                status = await self._wait_for_operation(op_id)
                if not status or not status.get('success', False):
                    success = False
                    break

            # Update task status
            self.scheduler_manager.mark_task_complete(task_id, success)

        except Exception as e:
            self.monitor_manager._add_event(
                MonitoringLevel.ERROR,
                'scheduler_service',
                f'Error executing task {task_id}: {str(e)}'
            )
            self.scheduler_manager.mark_task_complete(task_id, False)

    async def _wait_for_operation(self, operation_id: str,
                                timeout_seconds: int = 3600) -> Optional[dict]:
        """Wait for a backup operation to complete.

        Args:
            operation_id: ID of the operation to wait for
            timeout_seconds: Maximum time to wait in seconds

        Returns:
            Optional[dict]: Operation status if completed, None if timed out
        """
        start_time = datetime.now()
        while True:
            status = self.backup_manager.get_job_status(operation_id)
            if not status:
                return None

            if status['status'] in ['completed', 'verified', 'failed']:
                return status

            if (datetime.now() - start_time).total_seconds() > timeout_seconds:
                return None

            await asyncio.sleep(10)  # Check every 10 seconds