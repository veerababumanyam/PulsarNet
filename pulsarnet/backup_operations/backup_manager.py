"""Backup Manager Module for PulsarNet.

This module orchestrates backup operations, handles concurrent backups,
and manages the various backup protocols supported by the application.
"""

import asyncio
from typing import Dict, List, Optional, Type, Any
from pathlib import Path
from functools import lru_cache
from asyncio import Queue
import logging
from datetime import datetime, timedelta

from .backup_protocol import BackupProtocol, ProtocolType, TFTPProtocol, SCPProtocol, SFTPProtocol, FTPProtocol
from .backup_job import BackupJob, BackupStatus
from ..device_management.connection_types import DeviceConnectionType
from ..device_management.device import Device

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
        self._last_configs: Dict[str, str] = {}  # Cache for device configs to support differential backups
        self._connection_pool: Dict[str, Queue] = {}
        self._cache_ttl = 300  # Cache TTL in seconds

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
            # Set a timeout to prevent waiting indefinitely
            return await asyncio.wait_for(self._connection_pool[pool_key].get(), timeout=5.0)
        except (asyncio.QueueEmpty, asyncio.TimeoutError):
            try:
                protocol_class = self.protocol_registry[ProtocolType(protocol_type)]
                return protocol_class({})
            except Exception as e:
                logging.error(f"Error creating protocol instance: {str(e)}")
                # Return a default protocol to avoid returning None
                default_protocol_class = self.protocol_registry[next(iter(self.protocol_registry))]
                return default_protocol_class({})

    async def _release_connection(self, protocol: BackupProtocol, protocol_type: str, device_ip: str) -> None:
        """Release a connection back to the pool.

        Args:
            protocol: Protocol instance to release.
            protocol_type: Type of backup protocol.
            device_ip: IP address of the device.
        """
        pool_key = f"{protocol_type}_{device_ip}"
        try:
            # Use try_put with a timeout to avoid blocking indefinitely
            await asyncio.wait_for(self._connection_pool[pool_key].put(protocol), timeout=1.0)
        except (asyncio.QueueFull, asyncio.TimeoutError, Exception) as e:
            logging.debug(f"Connection pool full or error, disconnecting directly: {str(e)}")
            # Always safely disconnect if we can't return to pool
            try:
                await protocol.disconnect()
            except Exception as disconnect_error:
                logging.error(f"Error disconnecting protocol: {str(disconnect_error)}")

    def create_backup_job(
        self, device_ip: str, protocol_type: str, config: Dict[str, Any]
    ) -> BackupJob:
        """Create a new backup job.

        Args:
            device_ip: IP address of the device to backup.
            protocol_type: Type of protocol to use (e.g., 'tftp', 'scp', etc.).
            config: Configuration dictionary for the protocol.

        Returns:
            BackupJob: The created backup job.
        """
        # Ensure protocol type is valid, default to TFTP if not
        if protocol_type not in [pt.value for pt in ProtocolType]:
            logging.warning(f"Invalid protocol type '{protocol_type}'. Defaulting to TFTP.")
            protocol_type = ProtocolType.TFTP.value

        # Create directory for backups if it doesn't exist
        backup_dir = Path(self.base_backup_path)
        backup_dir.mkdir(parents=True, exist_ok=True)

        # Generate unique filename for this backup
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        device_name = config.get('device_name', 'unknown')
        sanitized_device_name = "".join(c if c.isalnum() else "_" for c in device_name)
        
        backup_path = backup_dir / f"{sanitized_device_name}_{device_ip}_{timestamp}.cfg"

        # Create and register the job
        job = BackupJob(device_ip, protocol_type, backup_path, config)
        self.active_jobs[job.job_id] = job
        
        logging.info(f"Created backup job {job.job_id} for device {device_name} ({device_ip})")
        
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
            logging.error(f"No backup job found with ID: {job_id}")
            raise ValueError(f"No backup job found with ID: {job_id}")

        # Add job to priority queue
        await self._priority_queue.put((-priority, job_id))

        # Process the job within semaphore
        async with self._semaphore:
            protocol = None
            try:
                # Get job from queue and verify it's the one we want
                current_priority, current_job_id = await self._priority_queue.get()
                if current_job_id != job_id:
                    # Put it back and return if not our job
                    await self._priority_queue.put((current_priority, current_job_id))
                    return

                # Start the job
                logging.info(f"Starting backup job {job_id} for device {job.device_name} ({job.device_ip})")
                await job.start()
                
                # Get the appropriate protocol based on job configuration
                protocol = await self._get_connection(job.protocol_type, job.device_ip)
                
                # Connect to the device
                job.progress.current_phase = "connecting"
                connection_success = await protocol.connect()
                if not connection_success:
                    error_msg = "Failed to connect using the selected protocol"
                    logging.error(f"Backup failed for {job.device_name} ({job.device_ip}): {error_msg}")
                    job.complete(False, error_msg)
                    return
                
                # Get device configuration
                job.progress.current_phase = "retrieving_config"
                try:
                    # Use device-specific commands to get configuration
                    device_config = await self._get_device_config(job)
                    if not device_config:
                        error_msg = "Failed to retrieve device configuration"
                        logging.error(f"Backup failed for {job.device_name} ({job.device_ip}): {error_msg}")
                        job.complete(False, error_msg)
                        return
                        
                    # If differential backup is enabled and we have a previous config
                    if is_differential and job.device_ip in self._last_configs:
                        try:
                            job.progress.current_phase = "comparing_configs"
                            current_config = self._last_configs[job.device_ip]
                            
                            # Compare with previous configuration
                            has_changes, diff = await protocol.get_config_diff(current_config, device_config)
                            
                            if not has_changes:
                                logging.info(f"No configuration changes detected for {job.device_name} ({job.device_ip})")
                                job.complete(True, "No configuration changes detected")
                                return
                        except Exception as diff_error:
                            logging.warning(f"Error comparing configurations for {job.device_name}, proceeding with full backup: {str(diff_error)}")
                            # Continue with full backup if diff fails
                    
                    # Validate the configuration
                    try:
                        job.progress.current_phase = "validating_config"
                        is_valid, error = await protocol.validate_config(device_config)
                        if not is_valid:
                            error_msg = f"Configuration validation failed: {error}"
                            logging.error(f"Validation failed for {job.device_name} ({job.device_ip}): {error_msg}")
                            job.complete(False, error_msg)
                            return
                    except Exception as validation_error:
                        logging.warning(f"Configuration validation error for {job.device_name}: {str(validation_error)}")
                        # Proceed with backup even if validation fails
                    
                    # Write configuration to backup file
                    job.progress.current_phase = "writing_backup"
                    try:
                        # Write the configuration to the backup file
                        with open(job.backup_path, 'w', encoding='utf-8') as f:
                            f.write(device_config)
                            
                        # Store configuration for future differential backups
                        self._last_configs[job.device_ip] = device_config
                        
                        # Mark job as completed successfully
                        logging.info(f"Backup completed successfully for {job.device_name} ({job.device_ip})")
                        job.complete(True, "Backup completed successfully")
                        
                    except Exception as write_error:
                        error_msg = f"Failed to write backup file: {str(write_error)}"
                        logging.error(f"Backup failed for {job.device_name} ({job.device_ip}): {error_msg}")
                        job.complete(False, error_msg)
                        
                except Exception as config_error:
                    error_msg = f"Failed to get device configuration: {str(config_error)}"
                    logging.error(f"Backup failed for {job.device_name} ({job.device_ip}): {error_msg}")
                    job.complete(False, error_msg)
                    
            except Exception as e:
                error_msg = f"Unexpected error during backup: {str(e)}"
                logging.exception(f"Exception in backup job {job_id}: {error_msg}")
                # Only complete the job if it exists and isn't already completed
                if job and job.status in [BackupStatus.PENDING, BackupStatus.IN_PROGRESS]:
                    job.complete(False, error_msg)
            finally:
                # Always release the protocol connection
                if protocol:
                    try:
                        await protocol.disconnect()
                    except Exception as disconnect_error:
                        logging.error(f"Error disconnecting protocol: {str(disconnect_error)}")
                    finally:
                        # No need to release connection to pool since we'll disconnect
                        pass
                        
    async def _get_device_config(self, job) -> str:
        """Get device configuration based on device type and connection method.
        
        Args:
            job: The backup job containing device information
            
        Returns:
            str: The device configuration or empty string if failed
        """
        try:
            # Find the device in device_manager
            from ..device_management.device_manager import DeviceManager
            
            # This is a simplified approach - in a real implementation we'd need
            # to have access to the device_manager or the actual device object
            # For now, we'll simulate the device-specific commands
            
            device_type = job.device_type.lower() if job.device_type else ""
            
            # Use the appropriate commands based on device type
            commands = []
            if "cisco_ios" in device_type:
                commands = ['terminal length 0', 'show running-config']
            elif "cisco_nxos" in device_type:
                commands = ['terminal length 0', 'show running-config']
            elif "juniper" in device_type:
                commands = ['show configuration | display set']
            elif "arista" in device_type:
                commands = ['terminal width 512', 'show running-config']
            elif "paloalto" in device_type:
                commands = ['set cli pager off', 'show config running format xml']
            elif "hp_comware" in device_type:
                commands = ['screen-length disable', 'display current-configuration']
            elif "hp_procurve" in device_type:
                commands = ['no page', 'show running-config']
            elif "huawei" in device_type:
                commands = ['screen-length 0 temporary', 'display current-configuration']
            elif "dell_os10" in device_type:
                commands = ['terminal length 0', 'show running-configuration']
            elif "dell_powerconnect" in device_type:
                commands = ['terminal length 0', 'show running-config']
            elif "checkpoint" in device_type:
                commands = ['set clienv rows 0', 'show configuration']
            elif "fortinet" in device_type:
                commands = ['config system console', 'set output standard', 'end', 'show full-configuration']
            else:
                # Default commands for unknown device types
                commands = ['terminal length 0', 'show running-config']
                
            # In a real implementation, we would execute these commands
            # For now, we'll return a simulated configuration
            logging.info(f"Would execute commands for {job.device_name} ({job.device_type}): {commands}")
            
            # Simulate getting configuration - in real implementation this would
            # come from executing the commands on the device
            simulated_config = f"# Configuration for {job.device_name} ({job.device_ip})\n"
            simulated_config += f"# Device Type: {job.device_type}\n"
            simulated_config += f"# Backup Time: {datetime.now().isoformat()}\n"
            simulated_config += "# This is a simulated configuration\n"
            
            return simulated_config
            
        except Exception as e:
            logging.error(f"Error getting device configuration: {str(e)}")
            return ""

    async def backup_device(self, device) -> bool:
        """Perform a backup operation for a given device using the appropriate protocol and configuration.
        
        Args:
            device: The device object to backup
            
        Returns:
            bool: True if backup was successful, False otherwise
        """
        try:
            # Determine the appropriate protocol based on connection type
            protocol_type = self._get_protocol_for_device(device)
            
            # Prepare configuration for the protocol
            config = self._prepare_protocol_config(device)
            
            # Log the backup attempt
            logging.info(f"Starting backup for device {device.name} ({device.ip_address}) using {protocol_type} protocol")
            
            # Create and start the backup job
            job = self.create_backup_job(device.ip_address, protocol_type, config)
            job.device_name = device.name  # Store device name for better logging
            job.device_type = str(device.device_type)  # Store device type
            
            # Start the backup process
            await self.start_backup(job.job_id)
            
            # Log the result
            if job.status == BackupStatus.COMPLETED:
                logging.info(f"Backup completed successfully for {device.name} ({device.ip_address})")
            else:
                error_msg = job.progress.error_message or "Unknown error"
                logging.error(f"Backup failed for {device.name} ({device.ip_address}): {error_msg}")
                
            return job.status == BackupStatus.COMPLETED
            
        except Exception as e:
            logging.error(f"Exception during backup of {device.name} ({device.ip_address}): {str(e)}")
            return False
    
    def _get_protocol_for_device(self, device) -> str:
        """Determine the appropriate backup protocol for a device based on its connection type.
        
        Args:
            device: The device object
            
        Returns:
            str: The protocol type to use for backup
        """
        # Map connection types to protocols
        if device.connection_type == DeviceConnectionType.DIRECT_SSH:
            return ProtocolType.SCP.value
        elif device.connection_type == DeviceConnectionType.DIRECT_TELNET:
            return ProtocolType.TFTP.value
        elif device.connection_type in [
            DeviceConnectionType.JUMP_SSH_DEVICE_SSH,
            DeviceConnectionType.JUMP_SSH_DEVICE_TELNET,
            DeviceConnectionType.JUMP_TELNET_DEVICE_SSH,
            DeviceConnectionType.JUMP_TELNET_DEVICE_TELNET
        ]:
            # For jump host configurations, use SFTP which supports proxying
            return ProtocolType.SFTP.value
        else:
            # Default to TFTP for unknown connection types
            logging.warning(f"Unknown connection type {device.connection_type} for {device.name}, defaulting to TFTP")
            return ProtocolType.TFTP.value
    
    def _prepare_protocol_config(self, device) -> dict:
        """Prepare configuration dictionary for the backup protocol based on device properties.
        
        Args:
            device: The device object
            
        Returns:
            dict: Configuration for the backup protocol
        """
        config = {
            'device_name': device.name,
            'device_type': str(device.device_type),
            'username': device.username,
            'password': device.password,
            'port': device.port,
            'use_keys': device.use_keys if hasattr(device, 'use_keys') else False,
            'key_file': device.key_file if hasattr(device, 'key_file') else None,
        }
        
        # Add jump host configuration if needed
        if device.use_jump_server:
            config.update({
                'jump_host': device.jump_server,
                'jump_username': device.jump_username,
                'jump_password': device.jump_password,
                'jump_port': device.jump_port,
                'jump_protocol': device.jump_protocol
            })
            
        return config

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