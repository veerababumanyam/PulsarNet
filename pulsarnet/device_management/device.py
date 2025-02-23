"""Device class for managing individual network devices in PulsarNet.

This module provides the core functionality for representing and managing
individual network devices, including their credentials, connection status,
and backup history.
"""

from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Optional, Dict, List
import netmiko
import asyncio
import logging
import os
import json

class DeviceType(Enum):
    """Enumeration of supported device types."""
    CISCO_IOS = "cisco_ios"
    CISCO_NXOS = "cisco_nxos"
    JUNIPER_JUNOS = "juniper_junos"
    ARISTA_EOS = "arista_eos"
    PALOALTO_PANOS = "paloalto_panos"
    HP_COMWARE = "hp_comware"
    HP_PROCURVE = "hp_procurve"
    HUAWEI_VRP = "huawei_vrp"
    DELL_OS10 = "dell_os10"
    DELL_POWERCONNECT = "dell_powerconnect"
    CHECKPOINT_GAIA = "checkpoint_gaia"
    FORTINET_FORTIOS = "fortinet_fortios"

    @classmethod
    def _missing_(cls, value):
        """Handle case-insensitive lookup.
        
        Args:
            value: The value to look up
            
        Returns:
            DeviceType: The matching enum member, or None if not found
            
        Note:
            This method handles case-insensitive lookup of device types.
            It will return None if the value doesn't match any device type.
        """
        try:
            if isinstance(value, str):
                # Convert to lowercase for comparison
                value = value.strip().lower()
                # Check all enum values
                for member in cls:
                    if member.value.lower() == value:
                        return member
            return None
        except Exception as e:
            logging.error(f"Error in DeviceType._missing_: {str(e)}")
            return None

    def __eq__(self, other):
        """Case-insensitive equality check.
        
        Args:
            other: The value to compare with
            
        Returns:
            bool: True if values match (case-insensitive), False otherwise
            
        Note:
            This method allows case-insensitive comparison with strings.
            For example: DeviceType.CISCO_IOS == 'cisco_ios' will return True
        """
        try:
            if isinstance(other, str):
                return self.value.lower() == other.strip().lower()
            return super().__eq__(other)
        except Exception as e:
            logging.error(f"Error in DeviceType.__eq__: {str(e)}")
            return False

class ConnectionStatus(Enum):
    """Enumeration of possible device connection states."""
    UNKNOWN = "unknown"  # For backward compatibility
    DISCONNECTED = "disconnected"
    CONNECTING = "connecting"
    CONNECTED = "connected"
    BACKING_UP = "backing_up"
    BACKUP_SUCCESS = "backup_success"
    BACKUP_FAILED = "backup_failed"
    ERROR = "error"
    TIMEOUT = "timeout"
    AUTH_FAILED = "auth_failed"

@dataclass
class BackupHistory:
    """Class for tracking backup operations for a device."""
    timestamp: datetime
    status: str
    backup_path: str
    protocol_used: str
    error_message: Optional[str] = None

class Device:
    """Class representing a network device in PulsarNet."""

    def __init__(
        self,
        name: str,
        ip_address: str,
        device_type: DeviceType,
        username: str = None,
        password: str = None,
        enable_password: str = None,
        port: int = 22,
    ):
        """Initialize device instance."""
        self.name = name
        self.ip_address = ip_address
        self.device_type = device_type
        self.username = username
        self._password = password
        self._enable_password = enable_password
        self.port = port
        self.is_connected = False
        self.last_seen = None
        self.last_connected = None
        self.last_error = None
        self.uptime = None
        self._connection_status = ConnectionStatus.DISCONNECTED
        self.backup_in_progress = False
        self.backup_history: List[BackupHistory] = []
        self._backup_status = ""  # Add backup status tracking
        self.last_backup = None  # Add last backup tracking
        
        # Initialize settings
        self.custom_settings: Dict[str, str] = {}
        
        # Initialize connection
        self._connection = None

    def set_error(self, error_msg: str):
        """Set the last error message."""
        self.last_error = error_msg
        logging.error(f"Device {self.name}: {error_msg}")

    @property
    def connection_status(self) -> ConnectionStatus:
        """Get the current connection status."""
        return self._connection_status
    
    @connection_status.setter
    def connection_status(self, value: ConnectionStatus):
        """Set the connection status."""
        self._connection_status = value
    
    @property
    def last_backup(self) -> Optional[datetime]:
        """Get the last backup time."""
        return self._last_backup
    
    @last_backup.setter
    def last_backup(self, value: Optional[datetime]):
        """Set the last backup time."""
        self._last_backup = value
    
    @property
    def backup_status(self) -> str:
        """Get the current backup status."""
        return self._backup_status
    
    @backup_status.setter
    def backup_status(self, value: str):
        """Set the backup status."""
        self._backup_status = value
    
    async def test_connection(self) -> tuple[bool, str]:
        """Test connection to the device.
        
        Returns:
            tuple[bool, str]: Success status and message
        """
        try:
            # Create device parameters for Netmiko
            device_params = {
                'device_type': self.device_type.value,
                'host': self.ip_address,
                'username': self.username,
                'password': self._password,
                'port': self.port,
                'secret': self._enable_password,
                'timeout': 10,  # Connection timeout
                'session_timeout': 60,  # Session timeout
                'auth_timeout': 10,  # Authentication timeout
            }

            # Update connection status
            self.connection_status = ConnectionStatus.CONNECTING
            self.backup_in_progress = True  # Prevent other operations

            try:
                # Run connection in thread pool to avoid blocking
                loop = asyncio.get_event_loop()
                connection = await loop.run_in_executor(None, lambda: netmiko.ConnectHandler(**device_params))
                
                try:
                    # Try to get device prompt
                    prompt = await loop.run_in_executor(None, connection.find_prompt)
                    
                    # Update status
                    self.connection_status = ConnectionStatus.CONNECTED
                    self.is_connected = True
                    self.last_connected = datetime.now()
                    self.last_seen = datetime.now()
                    
                    return True, f"Successfully connected to {self.name} ({prompt})"

                finally:
                    # Always disconnect
                    if connection:
                        await loop.run_in_executor(None, connection.disconnect)

            except netmiko.NetmikoTimeoutException:
                self.connection_status = ConnectionStatus.TIMEOUT
                return False, f"Connection to {self.name} timed out. Please check if device is reachable."

            except netmiko.NetmikoAuthenticationException:
                self.connection_status = ConnectionStatus.AUTH_FAILED
                return False, f"Authentication failed for {self.name}. Please check credentials."

            except ValueError as e:
                self.connection_status = ConnectionStatus.ERROR
                return False, f"Invalid device type '{self.device_type.value}'. Please check device configuration."

            except Exception as e:
                self.connection_status = ConnectionStatus.ERROR
                return False, f"Connection error: {str(e)}"

        except Exception as e:
            self.connection_status = ConnectionStatus.ERROR
            return False, f"Test failed: {str(e)}"

        finally:
            self.backup_in_progress = False  # Re-enable operations

    async def connect(self):
        """Establish connection to the device."""
        try:
            self.connection_status = ConnectionStatus.CONNECTING
            
            # Create connection parameters
            device_params = {
                'device_type': self.device_type.value,
                'host': self.ip_address,
                'username': self.username,
                'password': self._password,
                'port': self.port,
                'secret': self._enable_password,
                'timeout': 10,
                'session_timeout': 60,
                'auth_timeout': 10
            }
            
            # Create connection in thread pool
            loop = asyncio.get_event_loop()
            self._connection = await loop.run_in_executor(
                None, 
                lambda: netmiko.ConnectHandler(**device_params)
            )
            
            self.connection_status = ConnectionStatus.CONNECTED
            self.is_connected = True
            self.last_connected = datetime.now()
            
        except netmiko.NetmikoTimeoutException:
            self.connection_status = ConnectionStatus.TIMEOUT
            raise
        except netmiko.NetmikoAuthenticationException:
            self.connection_status = ConnectionStatus.AUTH_FAILED
            raise
        except Exception as e:
            self.connection_status = ConnectionStatus.ERROR
            raise

    async def backup_config(self) -> bool:
        """Backup device configuration."""
        try:
            if self.backup_in_progress:
                self.backup_status = "Backup already in progress"
                self.set_error("Backup already in progress")
                return False
                
            self.backup_in_progress = True
            self.last_error = None  # Clear previous errors
            self.backup_status = "Starting backup..."
            
            # Connect to device
            try:
                await self.connect()
            except netmiko.NetmikoTimeoutException:
                error_msg = f"TCP connection to device failed.\n\nCommon causes of this problem are:\n1. Incorrect hostname or IP address.\n2. Wrong TCP port.\n3. Intermediate firewall blocking access.\n\nDevice settings: {self.device_type.value} {self.ip_address}:{self.port}"
                self.set_error(error_msg)
                self.backup_status = "Connection failed"
                return False
            except netmiko.NetmikoAuthenticationException:
                self.set_error(f"Authentication failed. Please check username and password.")
                self.backup_status = "Authentication failed"
                return False
            except Exception as e:
                self.set_error(f"Connection error: {str(e)}")
                self.backup_status = "Connection error"
                return False

            # Get device configuration
            try:
                self.backup_status = "Retrieving configuration..."
                config = await self.get_config()
                if not config:
                    self.set_error("Failed to retrieve configuration")
                    self.backup_status = "Failed to get config"
                    return False
                    
                # Save configuration
                self.backup_status = "Saving configuration..."
                await self.save_config(config)
                self.last_error = None  # Clear error on success
                self.backup_status = "Backup completed successfully"
                return True
                
            except Exception as e:
                self.set_error(f"Backup error: {str(e)}")
                self.backup_status = "Backup failed"
                return False
                
        finally:
            self.backup_in_progress = False

    async def get_config(self) -> str:
        """Get device configuration based on device type."""
        try:
            commands = []
            if self.device_type == DeviceType.CISCO_IOS:
                commands = ['terminal length 0', 'show running-config']
            elif self.device_type == DeviceType.CISCO_NXOS:
                commands = ['terminal length 0', 'show running-config']
            elif self.device_type == DeviceType.JUNIPER_JUNOS:
                commands = ['show configuration | display set']
            elif self.device_type == DeviceType.ARISTA_EOS:
                commands = ['terminal width 512', 'show running-config']
            elif self.device_type == DeviceType.PALOALTO_PANOS:
                commands = ['set cli pager off', 'show config running format xml']
            elif self.device_type == DeviceType.HP_COMWARE:
                commands = ['screen-length disable', 'display current-configuration']
            elif self.device_type == DeviceType.HP_PROCURVE:
                commands = ['no page', 'show running-config']
            elif self.device_type == DeviceType.HUAWEI_VRP:
                commands = ['screen-length 0 temporary', 'display current-configuration']
            elif self.device_type == DeviceType.DELL_OS10:
                commands = ['terminal length 0', 'show running-configuration']
            elif self.device_type == DeviceType.DELL_POWERCONNECT:
                commands = ['terminal length 0', 'show running-config']
            elif self.device_type == DeviceType.CHECKPOINT_GAIA:
                commands = ['set clienv rows 0', 'show configuration']
            elif self.device_type == DeviceType.FORTINET_FORTIOS:
                commands = ['config system console', 'set output standard', 'end', 'show full-configuration']
            else:
                raise ValueError(f"Unsupported device type: {self.device_type}")
            
            return await self.send_commands(commands)
            
        except Exception as e:
            self.set_error(f"Failed to get configuration: {str(e)}")
            raise

    async def save_config(self, config: str):
        """Save configuration to backup file."""
        try:
            # Load settings
            settings_file = os.path.expanduser("~/.pulsarnet/settings.json")
            if os.path.exists(settings_file):
                with open(settings_file, 'r') as f:
                    settings = json.load(f)
            else:
                settings = {}
            
            # Get backup path from settings or use default
            backup_dir = settings.get('local_path', os.path.expanduser("~/.pulsarnet/backups"))
            os.makedirs(backup_dir, exist_ok=True)
            
            # Generate filename with timestamp
            timestamp = datetime.now()
            filename = f"{self.name}_{timestamp.strftime('%Y%m%d%H%M%S')}.cfg"
            filepath = os.path.join(backup_dir, filename)
            
            # Save configuration locally
            with open(filepath, "w", encoding='utf-8') as f:
                f.write(config)
            
            # Update history and timestamps
            self.last_backup = timestamp
            self.backup_history.append(
                BackupHistory(
                    timestamp=timestamp,
                    status="Success",
                    backup_path=filepath,
                    protocol_used=self.device_type.value,
                )
            )
            
            # Enforce retention policy
            max_backups = settings.get('max_backups', 10)
            if len(self.backup_history) > max_backups:
                # Remove oldest backups
                for old_backup in sorted(self.backup_history[:-max_backups], 
                                      key=lambda x: x.timestamp):
                    try:
                        if os.path.exists(old_backup.backup_path):
                            os.remove(old_backup.backup_path)
                    except Exception as e:
                        logging.warning(f"Failed to remove old backup {old_backup.backup_path}: {e}")
                self.backup_history = sorted(self.backup_history[-max_backups:], 
                                          key=lambda x: x.timestamp)
            
            # Handle remote storage if configured
            remote_type = settings.get('remote_type', 'None')
            if remote_type != 'None':
                await self._push_to_remote(filepath, settings)
            
            logging.info(f"Successfully backed up {self.name} to {filepath}")
            
        except Exception as e:
            self.set_error(f"Failed to save configuration: {str(e)}")
            raise
            
    async def _push_to_remote(self, local_file: str, settings: dict):
        """Push backup to remote storage."""
        remote_type = settings.get('remote_type')
        if remote_type == 'FTP':
            import ftplib
            try:
                with ftplib.FTP() as ftp:
                    ftp.connect(
                        settings['remote_host'], 
                        settings.get('remote_port', 21)
                    )
                    ftp.login(
                        settings['remote_user'], 
                        settings['remote_pass']
                    )
                    
                    remote_path = settings.get('remote_path', '')
                    if remote_path:
                        try:
                            ftp.mkd(remote_path)
                        except:
                            pass
                        ftp.cwd(remote_path)
                    
                    with open(local_file, 'rb') as f:
                        ftp.storbinary(f'STOR {os.path.basename(local_file)}', f)
                        
            except Exception as e:
                logging.error(f"FTP upload failed: {str(e)}")
                raise
                
        elif remote_type == 'SFTP':
            import paramiko
            try:
                transport = paramiko.Transport((
                    settings['remote_host'],
                    settings.get('remote_port', 22)
                ))
                transport.connect(
                    username=settings['remote_user'],
                    password=settings['remote_pass']
                )
                
                sftp = paramiko.SFTPClient.from_transport(transport)
                try:
                    remote_path = settings.get('remote_path', '')
                    if remote_path:
                        try:
                            sftp.mkdir(remote_path)
                        except:
                            pass
                        
                    remote_file = os.path.join(
                        remote_path,
                        os.path.basename(local_file)
                    )
                    sftp.put(local_file, remote_file)
                    
                finally:
                    sftp.close()
                    transport.close()
                    
            except Exception as e:
                logging.error(f"SFTP upload failed: {str(e)}")
                raise
                
        elif remote_type == 'TFTP':
            import tftpy
            try:
                client = tftpy.TftpClient(
                    settings['remote_host'],
                    settings.get('remote_port', 69)
                )
                remote_path = os.path.join(
                    settings.get('remote_path', ''),
                    os.path.basename(local_file)
                )
                client.upload(remote_path, local_file)
                
            except Exception as e:
                logging.error(f"TFTP upload failed: {str(e)}")
                raise

    def to_dict(self) -> dict:
        """Convert device to dictionary for serialization."""
        return {
            'name': self.name,
            'ip_address': self.ip_address,
            'device_type': self.device_type.value,
            'username': self.username,
            'password': self._password,
            'enable_password': self._enable_password,
            'port': self.port,
            'connection_status': self.connection_status.value,
            'is_connected': self.is_connected,
            'last_seen': self.last_seen.isoformat() if self.last_seen else None,
            'last_connected': self.last_connected.isoformat() if self.last_connected else None,
            'custom_settings': self.custom_settings
        }

    @classmethod
    def from_dict(cls, data: dict) -> 'Device':
        """Create device from dictionary."""
        device = cls(
            name=data['name'],
            ip_address=data['ip_address'],
            device_type=DeviceType(data['device_type']),
            username=data['username'],
            password=data['password'],
            enable_password=data.get('enable_password'),
            port=data.get('port', 22)
        )
        
        # Restore other attributes
        device.connection_status = ConnectionStatus(data.get('connection_status', 'unknown'))
        device.is_connected = data.get('is_connected', False)
        device.last_seen = datetime.fromisoformat(data['last_seen']) if data.get('last_seen') else None
        device.last_connected = datetime.fromisoformat(data['last_connected']) if data.get('last_connected') else None
        device.custom_settings = data.get('custom_settings', {})
        
        return device