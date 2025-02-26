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
from .connection_types import DeviceConnectionType

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

    def __hash__(self):
        """Return a hash value for the enum.
        
        Returns:
            int: Hash value based on the enum name
            
        Note:
            This is required because we've implemented a custom __eq__ method.
            We use the enum name for hashing to ensure consistent behavior.
        """
        return hash(self.name)

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
        connection_type: DeviceConnectionType = DeviceConnectionType.DIRECT_SSH,
        use_jump_server=False,
        jump_server=None,
        jump_username=None,
        jump_password=None,
        **kwargs
    ):
        """Initialize device instance."""
        self.name = name
        self.ip_address = ip_address
        self.device_type = Device._convert_device_type(device_type)
        self.username = username
        self.password = password
        self.enable_password = enable_password
        self.port = port
        self.connection_type = connection_type
        self.use_jump_server = use_jump_server
        
        # If connection_type starts with 'jump_', ensure use_jump_server is True
        if isinstance(self.connection_type, DeviceConnectionType) and self.connection_type.value.startswith('jump_'):
            self.use_jump_server = True
            logging.debug(f"Setting use_jump_server=True based on connection_type={self.connection_type.value}")
        
        self.jump_server = jump_server
        self.jump_username = jump_username
        self.jump_password = jump_password
        
        # Standardize jump host fields for consistency
        self.jump_host_name = kwargs.get('jump_host_name', '')
        
        # Ensure jump_protocol is properly set from kwargs
        # This is the key field that needs to be correctly set
        jump_protocol = kwargs.get('jump_protocol', 'ssh')
        if isinstance(jump_protocol, str):
            self.jump_protocol = jump_protocol.lower()
        else:
            self.jump_protocol = 'ssh'  # Default to SSH if not a string
            
        # For backwards compatibility, also set jump_connection_type
        self.jump_connection_type = self.jump_protocol
            
        # Log jump host details for debugging
        if self.use_jump_server:
            logging.info(f"Jump host details for {self.name}:")
            logging.info(f"  - jump_server: {self.jump_server}")
            logging.info(f"  - jump_host_name: {self.jump_host_name}")
            logging.info(f"  - jump_username: {self.jump_username}")
            logging.info(f"  - jump_protocol: {self.jump_protocol}")
            logging.info(f"  - jump_port: {kwargs.get('jump_port', 22)}")
            logging.info(f"  - connection_type: {self.connection_type.value if isinstance(self.connection_type, DeviceConnectionType) else self.connection_type}")
        
        self.jump_port = int(kwargs.get('jump_port', 22))
        
        # For backwards compatibility
        self.jump_server_port = self.jump_port
        
        self.is_connected = False
        self.last_seen = None
        self.last_connected = None
        self.last_error = None
        self.uptime = None
        self._connection_status = ConnectionStatus.DISCONNECTED
        self.backup_in_progress = False
        self.backup_history: List[BackupHistory] = []
        self._backup_status = ""  # Add backup status tracking
        self._last_backup = None  # Add last backup tracking
        
        # SSH key authentication
        self.use_keys = kwargs.get('use_keys', False)
        self.key_file = kwargs.get('key_file', '')
        
        # Initialize settings
        self.custom_settings = kwargs.get('custom_settings', {})
        
        # Initialize connection
        self._connection = None
        
        # Initialize groups
        self.groups = kwargs.get('groups', [])

    @staticmethod
    def _convert_device_type(input_type):
        """Convert input device type to a DeviceType enum if possible, otherwise return the input as is."""
        if isinstance(input_type, DeviceType):
            return input_type
        try:
            return DeviceType(input_type)
        except Exception:
            return input_type

    async def connect(self):
        """Asynchronously simulate connecting the device."""
        self.is_connected = True
        self.connection_status = ConnectionStatus.CONNECTED
        return True

    async def disconnect(self):
        """Asynchronously simulate disconnecting the device."""
        self.is_connected = False
        self.connection_status = ConnectionStatus.DISCONNECTED
        return True

    async def backup_config(self):
        """Asynchronously simulate backing up the device configuration."""
        config = "interface GigabitEthernet0/1\n no shutdown"
        self.backup_history.append(
            BackupHistory(
                timestamp=datetime.now(),
                status="success",
                backup_path="/dummy/path",
                protocol_used="dummy"
            )
        )
        self.last_backup = datetime.now()
        return config

    async def restore_config(self, config):
        """Asynchronously simulate restoring the device configuration."""
        return True

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
                'password': self.password,
                'port': self.port,
                'secret': self.enable_password,
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
        # Handle connection_type which might be a string or an enum
        if isinstance(self.connection_type, str):
            connection_type_value = self.connection_type
        else:
            # Assume it's an enum
            connection_type_value = self.connection_type.value
            
        return {
            'name': self.name,
            'ip_address': self.ip_address,
            'device_type': self.device_type.value,
            'username': self.username,
            'password': self.password,
            'enable_password': self.enable_password,
            'port': self.port,
            'connection_type': connection_type_value,
            'use_jump_server': self.use_jump_server,
            'jump_server': self.jump_server,
            'jump_username': self.jump_username,
            'jump_password': self.jump_password,
            'jump_protocol': getattr(self, 'jump_protocol', 'ssh'),
            'jump_host_name': getattr(self, 'jump_host_name', ''),
            'jump_port': getattr(self, 'jump_port', 22),
            'connection_status': self.connection_status.value,
            'is_connected': self.is_connected,
            'last_seen': self.last_seen.isoformat() if self.last_seen else None,
            'last_connected': self.last_connected.isoformat() if self.last_connected else None,
            'custom_settings': self.custom_settings
        }

    @classmethod
    def from_dict(cls, data: dict) -> 'Device':
        """Create device from dictionary."""
        # Debug logging to see what data is being passed
        logging.debug(f"Creating device from dict: {data}")
        
        # Log jump host details if present
        if data.get('use_jump_server') or data.get('connection_type', '').startswith('jump_'):
            logging.info(f"Importing device with jump host configuration: {data.get('name')}")
            logging.info(f"  - jump_server: {data.get('jump_server')}")
            logging.info(f"  - jump_host_name: {data.get('jump_host_name')}")
            logging.info(f"  - jump_username: {data.get('jump_username')}")
            logging.info(f"  - jump_protocol: {data.get('jump_protocol')}")
            logging.info(f"  - jump_port: {data.get('jump_port')}")
            logging.info(f"  - connection_type: {data.get('connection_type')}")
            logging.info(f"  - use_jump_server: {data.get('use_jump_server')}")
        
        groups = data.get('groups', [])
        if isinstance(groups, str):
            groups = [g.strip() for g in groups.split(',') if g.strip()]

        raw_connection = data.get('connection_type', 'direct_ssh').lower()
        # Special handling for 'jump_host' connection type
        if raw_connection == 'jump_host':
            # For 'jump_host', determine the connection type based on protocols
            device_protocol = data.get('protocol', 'ssh').lower()
            jump_protocol = data.get('jump_protocol', 'ssh').lower()
            
            if jump_protocol == 'telnet' and device_protocol == 'telnet':
                raw_connection = 'jump_telnet/telnet'
            elif jump_protocol == 'telnet' and device_protocol == 'ssh':
                raw_connection = 'jump_telnet/ssh'
            elif jump_protocol == 'ssh' and device_protocol == 'telnet':
                raw_connection = 'jump_ssh/telnet'
            else:  # Default: SSH jump host to SSH device
                raw_connection = 'jump_ssh/ssh'
                
            # Update the connection_type in the data dictionary
            data['connection_type'] = raw_connection
            # Explicitly set use_jump_server to True for jump_host connections
            data['use_jump_server'] = True
            logging.info(f"Converted 'jump_host' to '{raw_connection}' based on protocols")
            
        # Process jump host connection types
        if raw_connection.startswith('jump_'):
            # Set use_jump_server to True for any jump host connection
            data['use_jump_server'] = True
            
            mapping = {
                'jump_telnet/telnet': DeviceConnectionType.JUMP_TELNET_DEVICE_TELNET,
                'jump_telnet/ssh': DeviceConnectionType.JUMP_TELNET_DEVICE_SSH,
                'jump_ssh/telnet': DeviceConnectionType.JUMP_SSH_DEVICE_TELNET,
                'jump_ssh/ssh': DeviceConnectionType.JUMP_SSH_DEVICE_SSH
            }
            final_connection = mapping.get(raw_connection, DeviceConnectionType(raw_connection))
            
            # Ensure all jump host fields are present
            if not data.get('jump_server'):
                logging.warning(f"Jump server IP not provided for {data.get('name')} with connection type {raw_connection}")
            
            # Set default values for jump host fields if not provided
            if not data.get('jump_protocol'):
                data['jump_protocol'] = 'ssh'
                logging.info(f"Setting default jump_protocol='ssh' for {data.get('name')}")
                
            if not data.get('jump_port') or data.get('jump_port') in [None, ""]:
                data['jump_port'] = 22
                logging.info(f"Setting default jump_port=22 for {data.get('name')}")
        else:
            final_connection = DeviceConnectionType(raw_connection)

        # Debug logging for jump host details
        if data.get('use_jump_server') or raw_connection.startswith('jump_'):
            logging.info(f"Jump host details for {data.get('name')}: ")
            logging.info(f"  - jump_server: {data.get('jump_server')}")
            logging.info(f"  - jump_host_name: {data.get('jump_host_name')}")
            logging.info(f"  - jump_username: {data.get('jump_username')}")
            logging.info(f"  - jump_protocol: {data.get('jump_protocol')}")
            logging.info(f"  - jump_port: {data.get('jump_port')}")
            logging.info(f"  - connection_type: {raw_connection}")
            logging.info(f"  - use_jump_server: {data.get('use_jump_server')}")

        # Convert use_jump_server to boolean properly
        use_jump_server = False
        if 'use_jump_server' in data:
            if isinstance(data['use_jump_server'], bool):
                use_jump_server = data['use_jump_server']
            elif isinstance(data['use_jump_server'], str):
                use_jump_server = data['use_jump_server'].lower() == 'true'
            else:
                use_jump_server = bool(data['use_jump_server'])
        
        # Force use_jump_server to True if connection_type indicates a jump host
        if raw_connection.startswith('jump_') or raw_connection == 'jump_host':
            use_jump_server = True
            logging.info(f"Forcing use_jump_server=True for {data.get('name')} based on connection_type={raw_connection}")

        return cls(
            name=data.get('name'),
            ip_address=data.get('ip_address'),
            device_type=Device._convert_device_type(data.get('device_type')),
            username=data.get('username'),
            password=data.get('password'),
            enable_password=data.get('enable_password'),
            port=int(data.get('port', 22)),
            connection_type=final_connection,
            use_jump_server=use_jump_server,  # Use the properly converted boolean value
            jump_server=data.get('jump_server'),
            jump_host_name=data.get('jump_host_name'),
            jump_username=data.get('jump_username'),
            jump_password=data.get('jump_password'),
            jump_protocol=data.get('jump_protocol', 'ssh'),
            jump_port=int(data.get('jump_port', 22)) if data.get('jump_port') not in [None, ""] else 22,
            use_keys=(str(data.get('use_keys', 'false')).lower() == 'true'),
            key_file=data.get('key_file'),
            custom_settings=data.get('custom_settings', {}),
            groups=groups
        )