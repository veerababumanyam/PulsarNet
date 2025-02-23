"""Backup Manager Module for PulsarNet.

This module orchestrates backup operations, handles concurrent backups,
and manages the various backup protocols supported by the application.
"""

import asyncio
from typing import Dict, List, Optional, Type
from pathlib import Path
from functools import lru_cache
from asyncio import Queue

from .backup_protocol import BackupProtocol, ProtocolType, TFTPProtocol, SCPProtocol, SFTPProtocol, FTPProtocol
from .backup_job import BackupJob, BackupStatus

class BackupManager:
    """Class for managing backup operations and protocols."""

    def __init__(self, base_backup_path: Path):
        """Initialize the backup manager.

        Args:
            base_backup_path: Base directory for storing backups.
        """
        self.base_backup_path = base_backup_path
        self.active_jobs: Dict[str, BackupJob] = {}
        self.protocol_registry: Dict[ProtocolType, Type[BackupProtocol]] = {
            ProtocolType.TFTP: TFTPProtocol,
            ProtocolType.SCP: SCPProtocol,
            ProtocolType.SFTP: SFTPProtocol,
            ProtocolType.FTP: FTPProtocol
        }
        self.max_concurrent_backups = 5
        self._semaphore = asyncio.Semaphore(self.max_concurrent_backups)
        self._priority_queue = asyncio.PriorityQueue()
        self._last_configs: Dict[str, str] = {}
        self._connection_pool: Dict[str, Queue] = {}
        self._cache_ttl = 300  # Cache TTL in seconds

    @lru_cache(maxsize=100)
    def _get_cached_config(self, device_ip: str) -> Optional[str]:
        """Get cached configuration for a device.

        Args:
            device_ip: IP address of the device.

        Returns:
            Optional[str]: Cached configuration if available.
        """
        return self._last_configs.get(device_ip)

    async def _get_connection(self, protocol_type: str, device_ip: str) -> BackupProtocol:
        """Get a connection from the connection pool or create a new one.

        Args:
            protocol_type: Type of backup protocol.
            device_ip: IP address of the device.

        Returns:
            BackupProtocol: Protocol instance for the connection.
        """
        pool_key = f"{protocol_type}_{device_ip}"
        if pool_key not in self._connection_pool:
            self._connection_pool[pool_key] = Queue(maxsize=5)

        try:
            return await self._connection_pool[pool_key].get()
        except asyncio.QueueEmpty:
            protocol_class = self.protocol_registry[ProtocolType(protocol_type)]
            return protocol_class({})

    async def _release_connection(self, protocol: BackupProtocol, protocol_type: str, device_ip: str) -> None:
        """Release a connection back to the pool.

        Args:
            protocol: Protocol instance to release.
            protocol_type: Type of backup protocol.
            device_ip: IP address of the device.
        """
        pool_key = f"{protocol_type}_{device_ip}"
        try:
            await self._connection_pool[pool_key].put(protocol)
        except asyncio.QueueFull:
            await protocol.disconnect()

    def create_backup_job(self, device_ip: str, protocol_type: str, config: Dict) -> BackupJob:
        """Create a new backup job for a device.

        Args:
            device_ip: IP address of the device to backup.
            protocol_type: Type of backup protocol to use.
            config: Protocol-specific configuration.

        Returns:
            BackupJob: The created backup job instance.
        """
        backup_path = self._generate_backup_path(device_ip)
        job = BackupJob(device_ip, protocol_type, backup_path, config)
        self.active_jobs[job.job_id] = job
        return job

    async def start_backup(self, job_id: str, priority: int = 0, is_differential: bool = True) -> None:
        """Start a backup job with enhanced performance features.

        Args:
            job_id: ID of the backup job to start.
            priority: Priority level (0-9, higher number means higher priority).
            is_differential: Whether to perform differential backup.
        """
        job = self.active_jobs.get(job_id)
        if not job:
            raise ValueError(f"No backup job found with ID: {job_id}")

        await self._priority_queue.put((-priority, job_id))

        async with self._semaphore:
            try:
                current_priority, current_job_id = await self._priority_queue.get()
                if current_job_id != job_id:
                    await self._priority_queue.put((current_priority, current_job_id))
                    return

                await job.start()
                protocol = await self._get_connection(job.protocol_type, job.device_ip)

                try:
                    if await protocol.connect():
                        current_config = await self._get_cached_config(job.device_ip)

                        if is_differential and current_config:
                            has_changes, diff = await protocol.get_config_diff(current_config, "example_config")
                            
                            if not has_changes:
                                job.complete(True, "No configuration changes detected")
                                return

                        is_valid, error = await protocol.validate_config("example_config")
                        if not is_valid:
                            job.complete(False, f"Configuration validation failed: {error}")
                            return

                        success = await protocol.upload_config("example_config")
                        if success:
                            self._last_configs[job.device_ip] = "example_config"
                            self._get_cached_config.cache_clear()  # Clear cache when new config is uploaded
                finally:
                    await self._release_connection(protocol, job.protocol_type, job.device_ip)

            except Exception as e:
                job.complete(False, str(e))

    def get_job_status(self, job_id: str) -> Optional[Dict]:
        """Get the current status of a backup job.

        Args:
            job_id: ID of the backup job.

        Returns:
            Optional[Dict]: Job status information if job exists, None otherwise.
        """
        job = self.active_jobs.get(job_id)
        return job.to_dict() if job else None

    def get_active_jobs(self) -> List[Dict]:
        """Get a list of all active backup jobs.

        Returns:
            List[Dict]: List of active job status information.
        """
        return [job.to_dict() for job in self.active_jobs.values()]

    def _generate_backup_path(self, device_ip: str) -> Path:
        """Generate a backup file path for a device.

        Args:
            device_ip: IP address of the device.

        Returns:
            Path: Generated backup file path.
        """
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        return self.base_backup_path / f"{device_ip}_{timestamp}.cfg"

    def cleanup_completed_jobs(self, max_age_hours: int = 24) -> None:
        """Remove completed jobs older than specified age.

        Args:
            max_age_hours: Maximum age of completed jobs in hours.
        """
        current_time = datetime.now()
        jobs_to_remove = []

        for job_id, job in self.active_jobs.items():
            if job.status in [BackupStatus.COMPLETED, BackupStatus.VERIFIED, BackupStatus.FAILED]:
                if job.progress.end_time:
                    age = (current_time - job.progress.end_time).total_seconds() / 3600
                    if age > max_age_hours:
                        jobs_to_remove.append(job_id)

        for job_id in jobs_to_remove:
            del self.active_jobs[job_id]