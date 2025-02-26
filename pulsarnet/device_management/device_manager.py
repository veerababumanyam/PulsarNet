"""DeviceManager class for managing network devices in PulsarNet.

This module provides the core functionality for device discovery, credential management,
and connectivity testing across multiple vendor platforms.
"""

from typing import List, Dict, Optional, Tuple
from datetime import datetime
import asyncio
import netmiko
from cryptography.fernet import Fernet
from .device import Device, DeviceType, ConnectionStatus, BackupHistory
from .device_group import DeviceGroup
import os
import json
import logging
from .connection_types import DeviceConnectionType

class DeviceManager:
    """Class for managing network devices and their operations."""

    def __init__(self):
        """Initialize DeviceManager."""
        self.devices: Dict[str, Device] = {}
        self.groups: Dict[str, DeviceGroup] = {}
        self._discovery_running = False
        self._connection_pool: Dict[str, asyncio.Queue] = {}
        self._max_pool_size = 10
        
        # Create data directory if it doesn't exist
        self.data_dir = os.path.join(os.path.expanduser('~'), '.pulsarnet')
        os.makedirs(self.data_dir, exist_ok=True)
        
        # Handle encryption key persistence
        self._setup_encryption()
        
        # Load saved data
        self.load_devices()
        self.load_groups()

    def _setup_encryption(self):
        """Set up the encryption key, loading or creating as needed."""
        key_file = os.path.join(self.data_dir, '.keyfile')
        try:
            if os.path.exists(key_file):
                # Load existing key
                with open(key_file, 'rb') as f:
                    self._encryption_key = f.read()
            else:
                # Generate new key and save it
                self._encryption_key = Fernet.generate_key()
                with open(key_file, 'wb') as f:
                    f.write(self._encryption_key)
                # Secure the key file permissions (for non-Windows systems)
                if os.name != 'nt':
                    os.chmod(key_file, 0o600)
            
            self._cipher_suite = Fernet(self._encryption_key)
        except Exception as e:
            logging.error(f"Error setting up encryption: {str(e)}")
            # Fallback to a temporary key if there's an issue
            self._encryption_key = Fernet.generate_key()
            self._cipher_suite = Fernet(self._encryption_key)

    def load_devices(self) -> None:
        """Load devices from storage."""
        try:
            # Create devices directory if it doesn't exist
            devices_dir = os.path.expanduser('~/.pulsarnet/devices')
            os.makedirs(devices_dir, exist_ok=True)
            
            # Load devices file
            devices_file = os.path.join(self.data_dir, 'devices.json')
            if not os.path.exists(devices_file):
                logging.info("No devices file found. Starting with empty device list.")
                return
            
            with open(devices_file, 'r') as f:
                try:
                    devices_data = json.load(f)
                    logging.info(f"Loaded devices data: {devices_data}")  # Debug log
                    
                    # Clear existing devices
                    self.devices.clear()
                    
                    for name, data in devices_data.items():
                        try:
                            # Handle legacy connection status
                            if 'connection_status' in data:
                                status = data['connection_status'].lower()
                                if status not in [s.value for s in ConnectionStatus]:
                                    data['connection_status'] = 'unknown'
                            
                            # For each loaded device data, ensure connection_type is a string
                            ct = data.get('connection_type', 'direct_ssh')
                            if not isinstance(ct, str):
                                # If ct is not a string, try to get its value attribute or convert to string
                                data['connection_type'] = ct.value if hasattr(ct, 'value') else str(ct)
                            else:
                                data['connection_type'] = ct.lower()
                            
                            device = Device.from_dict(data)
                            self.devices[name] = device
                            logging.info(f"Loaded device: {name}")  # Debug log
                            
                        except Exception as e:
                            logging.error(f"Failed to load device {name}: {str(e)}")
                            continue
                            
                except json.JSONDecodeError as e:
                    logging.error(f"Invalid JSON in devices file: {str(e)}")
                    raise
                    
            logging.info(f"Successfully loaded {len(self.devices)} devices")
            
        except Exception as e:
            logging.error(f"Failed to load devices: {str(e)}")

    def load_groups(self):
        """Load groups from disk."""
        try:
            groups_file = os.path.join(self.data_dir, 'groups.json')
            if os.path.exists(groups_file):
                with open(groups_file, 'r') as f:
                    groups_data = json.load(f)
                for name, data in groups_data.items():
                    try:
                        group = DeviceGroup(
                            name=data['name'],
                            description=data.get('description', '')
                        )
                        # Add devices to group
                        for device_name in data.get('devices', []):
                            if device_name in self.devices:
                                group.add_device(self.devices[device_name])
                        # Add custom attributes
                        group.custom_attributes = data.get('custom_attributes', {})
                        self.groups[name] = group
                    except Exception as e:
                        logging.error(f"Failed to load group {name}: {str(e)}")
            else:
                logging.info("No groups file found. Starting with empty group list.")

        except Exception as e:
            logging.error(f"Failed to load groups: {str(e)}")
            raise

    def save_devices(self):
        """Save devices to disk."""
        try:
            devices_file = os.path.join(self.data_dir, 'devices.json')
            devices_data = {}
            for name, device in self.devices.items():
                devices_data[name] = device.to_dict()
            
            with open(devices_file, 'w') as f:
                json.dump(devices_data, f, indent=4)
                logging.info(f"Saved devices: {list(devices_data.keys())}")  # Debug log
        except Exception as e:
            logging.error(f"Failed to save devices: {str(e)}")
            raise

    def save_groups(self):
        """Save groups to disk."""
        try:
            groups_data = {}
            for name, group in self.groups.items():
                groups_data[name] = {
                    'name': group.name,
                    'description': group.description,
                    'devices': [device.name for device in group.devices],
                    'custom_attributes': group.custom_attributes
                }
            
            groups_file = os.path.join(self.data_dir, 'groups.json')
            with open(groups_file, 'w') as f:
                json.dump(groups_data, f, indent=4)

        except Exception as e:
            logging.error(f"Failed to save groups: {str(e)}")
            raise

    def _encrypt_credentials(self, password: str) -> bytes:
        """Encrypt sensitive credentials.

        Args:
            password: The password to encrypt.

        Returns:
            bytes: Encrypted password.
        """
        return self._cipher_suite.encrypt(password.encode())

    def _decrypt_credentials(self, encrypted_password: bytes) -> str:
        """Decrypt sensitive credentials.

        Args:
            encrypted_password: The encrypted password.

        Returns:
            str: Decrypted password.
        """
        return self._cipher_suite.decrypt(encrypted_password).decode()

    async def _get_connection(self, device: Device) -> netmiko.ConnectHandler:
        """Get a connection from the pool or create a new one.

        Args:
            device: The device to connect to.

        Returns:
            netmiko.ConnectHandler: A connection to the device.
            
        Raises:
            Exception: If the connection fails.
        """
        # Initialize resource variables that need cleanup
        jump_connection = None
        
        try:
            # Check if there's an existing connection in the pool
            if device.ip_address not in self._connection_pool:
                self._connection_pool[device.ip_address] = asyncio.Queue(maxsize=self._max_pool_size)

            try:
                # Try to get an existing connection from the pool with a short timeout
                connection = await asyncio.wait_for(
                    self._connection_pool[device.ip_address].get(), 
                    timeout=0.5
                )
                
                # Verify the connection is still active before returning it
                if hasattr(connection, 'is_alive') and callable(connection.is_alive):
                    if not connection.is_alive():
                        logging.warning(f"Dead connection found in pool for {device.name}. Creating a new one.")
                        raise asyncio.QueueEmpty()
                return connection
                
            except (asyncio.QueueEmpty, asyncio.TimeoutError):
                # Prepare base connection parameters
                connection_params = {
                    'host': device.ip_address,
                    'username': device.username,
                    'password': self._decrypt_credentials(device.password),
                    'port': device.port,
                    'secret': self._decrypt_credentials(device.enable_password) if device.enable_password else None,
                    'timeout': device.timeout if hasattr(device, 'timeout') and device.timeout else 10,
                    'session_timeout': 60,
                    'auth_timeout': 10,
                    'banner_timeout': 15,
                    'fast_cli': False,  # More reliable for different devices
                    'verbose': False
                }
                
                # Add key-based authentication if configured
                if hasattr(device, 'use_keys') and device.use_keys and hasattr(device, 'key_file') and device.key_file:
                    connection_params['use_keys'] = True
                    connection_params['key_file'] = device.key_file
                
                # Handle device type mapping
                device_type = device.device_type.value
                if 'cisco_ios' in device_type:
                    base_device_type = 'cisco_ios'
                elif 'juniper' in device_type:
                    base_device_type = 'juniper_junos'
                elif 'arista' in device_type:
                    base_device_type = 'arista_eos'
                else:
                    base_device_type = device_type

                # Handle connection scenarios based on connection type
                if device.connection_type == DeviceConnectionType.DIRECT_TELNET:
                    connection_params['device_type'] = f"{base_device_type}_telnet"
                elif device.connection_type == DeviceConnectionType.DIRECT_SSH:
                    connection_params['device_type'] = base_device_type
                elif device.connection_type in [
                    DeviceConnectionType.JUMP_TELNET_DEVICE_TELNET,
                    DeviceConnectionType.JUMP_TELNET_DEVICE_SSH,
                    DeviceConnectionType.JUMP_SSH_DEVICE_TELNET,
                    DeviceConnectionType.JUMP_SSH_DEVICE_SSH
                ]:
                    # Establish connection to the jump host
                    jump_params = {
                        'host': device.jump_server,
                        'username': device.jump_username,
                        'password': self._decrypt_credentials(device.jump_password),
                        'port': device.jump_server_port if hasattr(device, 'jump_server_port') and device.jump_server_port else 22,
                        'timeout': 15,  # Increased timeout for jump hosts
                        'session_timeout': 60,
                        'auth_timeout': 15,
                        'banner_timeout': 15,
                        'fast_cli': False,
                        'verbose': False
                    }

                    # Determine jump host connection type based on device.jump_connection_type
                    if hasattr(device, 'jump_protocol') and device.jump_protocol.lower() == 'telnet':
                        jump_params['device_type'] = 'terminal_server_telnet'
                    elif hasattr(device, 'jump_connection_type') and device.jump_connection_type.lower() == 'telnet':
                        jump_params['device_type'] = 'terminal_server_telnet'
                    else:
                        jump_params['device_type'] = 'terminal_server'

                    try:
                        logging.info(f"Connecting to jump host {device.jump_server} for device {device.name}")
                        # Run in executor to avoid blocking the event loop
                        loop = asyncio.get_event_loop()
                        jump_connection = await loop.run_in_executor(None, lambda: netmiko.ConnectHandler(**jump_params))
                        
                        if not jump_connection.is_alive():
                            raise Exception("Jump host connection established but not responsive")
                        
                        logging.info(f"Successfully connected to jump host for device {device.name}")
                    except Exception as e:
                        logging.error(f"Failed to connect to jump host for {device.name}: {str(e)}")
                        raise Exception(f'Failed to connect to jump host: {str(e)}')

                    # Determine device connection type
                    if 'telnet' in device.connection_type.value.split('/')[1]:
                        # For telnet through jump host
                        connection_params['device_type'] = f"{base_device_type}_telnet"
                    else:
                        # For SSH through jump host
                        connection_params['device_type'] = base_device_type
                    
                    # Add proxy session parameters for jump host connection
                    connection_params['session_log'] = None
                    connection_params['global_delay_factor'] = 2.0  # More reliable for jump host connections
                    
                    # Create jump host proxy command
                    if 'telnet' in device.connection_type.value.split('/')[1]:
                        # Telnet command to the device
                        proxy_command = f"telnet {device.ip_address} {device.port}"
                    else:
                        # SSH command to the device
                        proxy_command = f"ssh -l {device.username} -p {device.port} {device.ip_address}"
                    
                    # Store jump session for use in the device connection
                    connection_params['jump_connection'] = jump_connection
                    connection_params['proxy_command'] = proxy_command

                # Create the connection with appropriate exception handling
                try:
                    logging.info(f"Initiating connection to device {device.name} ({device.ip_address})")
                    # Run in executor to avoid blocking the event loop
                    loop = asyncio.get_event_loop()
                    conn = await loop.run_in_executor(None, lambda: netmiko.ConnectHandler(**connection_params))
                    logging.info(f"Successfully established connection to {device.name}")
                    return conn
                except Exception as e:
                    error_msg = str(e)
                    if "timed out" in error_msg.lower():
                        logging.error(f"Timeout connecting to {device.name}: {error_msg}")
                        raise Exception(f'Connection timeout: {error_msg}')
                    elif "authentication" in error_msg.lower():
                        logging.error(f"Authentication failed for {device.name}: {error_msg}")
                        raise Exception(f'Authentication failed: {error_msg}')
                    else:
                        logging.error(f"Failed to connect to {device.name}: {error_msg}")
                        raise Exception(f'Connection failed: {error_msg}')
        except Exception as e:
            # Clean up resources before propagating the exception
            if jump_connection:
                try:
                    jump_connection.disconnect()
                    logging.info(f"Disconnected from jump host after connection failure to {device.name}")
                except Exception as cleanup_error:
                    logging.warning(f"Error disconnecting from jump host: {str(cleanup_error)}")
            
            # Propagate the original exception
            raise

    async def _release_connection(self, device_name: str, connection: netmiko.ConnectHandler) -> None:
        """Release a connection back to the pool.

        Args:
            device_name: Name of the device.
            connection: The connection to release.
        """
        try:
            await self._connection_pool[device_name].put(connection)
        except asyncio.QueueFull:
            await connection.disconnect()

    async def test_device_connection(self, device: Device) -> Tuple[bool, Optional[str]]:
        """Tests connection to a device and updates its status.
        
        Args:
            device: The device to test connection to.
            
        Returns:
            Tuple[bool, Optional[str]]: A tuple containing a success boolean and an error message (if any).
        """
        connection = None
        start_time = datetime.now()
        metric_id = None
        
        # Create a metric ID for logging if the logger has a start_metric method
        if hasattr(self, 'logger') and hasattr(self.logger, 'start_metric'):
            metric_id = self.logger.start_metric(
                operation="test_connection", 
                target_id=device.name, 
                target_type="device"
            )
        
        try:
            # Get device type-specific test commands
            test_commands = self._get_test_commands(device.device_type)
            
            # Log the connection attempt
            logging.info(f"Testing connection to {device.name} ({device.ip_address}) via {device.connection_type.value}")
            
            # Set connection status to connecting during the test
            device.connection_status = ConnectionStatus.CONNECTING
            
            # Set escalating timeouts based on connection type
            base_timeout = 30
            if device.use_jump_server:
                # Jump server connections may need more time
                timeout = base_timeout * 1.5
            else:
                timeout = base_timeout
                
            # Adjust timeout if device has custom timeout setting
            if hasattr(device, 'timeout') and device.timeout:
                # Use device's timeout as a factor of the base timeout
                timeout = max(timeout, device.timeout * 1.2)
            
            # Get connection with timeout
            try:
                connection = await asyncio.wait_for(
                    self._get_connection(device), 
                    timeout=timeout
                )
            except asyncio.TimeoutError:
                device.connection_status = ConnectionStatus.TIMEOUT
                elapsed = (datetime.now() - start_time).total_seconds()
                logging.warning(f"Connection to {device.name} timed out after {elapsed:.1f} seconds")
                return False, f"Connection timed out after {elapsed:.1f} seconds"
            except Exception as e:
                error_msg = str(e).lower()
                if "authentication" in error_msg or "password" in error_msg:
                    device.connection_status = ConnectionStatus.AUTH_FAILED
                    logging.error(f"Authentication failed for {device.name}: {str(e)}")
                    return False, f"Authentication failed: {str(e)}"
                else:
                    device.connection_status = ConnectionStatus.ERROR
                    logging.error(f"Connection error for {device.name}: {str(e)}")
                    return False, f"Connection error: {str(e)}"
            
            # Successful connection established, now verify with commands
            device.is_connected = True
            device.last_connected = datetime.now()
            device.last_seen = datetime.now()
            
            # First try a simple command appropriate for this device type
            try:
                # Use a device-appropriate command to verify connectivity
                loop = asyncio.get_event_loop()
                output = await loop.run_in_executor(
                    None, 
                    lambda: connection.send_command(
                        test_commands[0],  # First command from the test commands list
                        delay_factor=2,
                        max_loops=2000,  # Increase max loops to avoid premature timeout
                        strip_prompt=False,
                        strip_command=False
                    )
                )
                
                # Check for common error patterns in the output
                if not output or any(error in output.lower() for error in 
                           ['error', 'invalid', 'failure', 'denied', 'not recognized', 
                            'unknown command', 'syntax error', 'incomplete']):
                    
                    # If the first command failed, try a more universal one
                    fallback_output = await loop.run_in_executor(
                        None, 
                        lambda: connection.send_command(
                            test_commands[-1],  # Last command is most universal
                            delay_factor=2,
                            max_loops=2000,
                            strip_prompt=False,
                            strip_command=False
                        )
                    )
                    
                    if not fallback_output or any(error in fallback_output.lower() for error in 
                               ['error', 'invalid', 'failure', 'denied', 'not recognized']):
                        device.connection_status = ConnectionStatus.ERROR
                        return False, f"Command execution failed: {output or fallback_output}"
                
                # Successfully executed commands
                device.connection_status = ConnectionStatus.CONNECTED
                
                # Extract and store device info from output if available
                if hasattr(device, 'custom_settings') and isinstance(device.custom_settings, dict):
                    device.custom_settings['last_test_output'] = output
                    
                    # Try to extract version info
                    if 'version' in output.lower():
                        import re
                        version_match = re.search(r'(?:Version|ver\.?|software)[\s:]+([0-9\.]+)', output, re.IGNORECASE)
                        if version_match:
                            device.custom_settings['software_version'] = version_match.group(1)
                
                elapsed = (datetime.now() - start_time).total_seconds()
                return True, f"Connection successful ({elapsed:.1f}s)"
                
            except Exception as cmd_error:
                device.connection_status = ConnectionStatus.ERROR
                logging.error(f"Command execution failed for {device.name}: {str(cmd_error)}")
                return False, f"Connected but command execution failed: {str(cmd_error)}"
                
        except Exception as e:
            device.connection_status = ConnectionStatus.ERROR
            logging.error(f"Unexpected error testing connection to {device.name}: {str(e)}")
            return False, f"Unexpected error: {str(e)}"
            
        finally:
            # Resource cleanup
            if connection:
                try:
                    await self._release_connection(device.name, connection)
                except Exception as e:
                    logging.error(f"Error releasing connection for {device.name}: {e}")
            
            # Update metrics if applicable
            if metric_id and hasattr(self, 'logger') and hasattr(self.logger, 'end_metric'):
                elapsed = (datetime.now() - start_time).total_seconds()
                status = "success" if device.connection_status == ConnectionStatus.CONNECTED else "failure"
                details = {
                    "elapsed_time": elapsed,
                    "connection_type": device.connection_type.value,
                    "status": device.connection_status.value,
                    "ip_address": device.ip_address
                }
                
                try:
                    await self.logger.end_metric(metric_id, status, details)
                except Exception as log_error:
                    logging.warning(f"Failed to log metrics for connection test to {device.name}: {str(log_error)}")
    
    def _get_test_commands(self, device_type: DeviceType) -> List[str]:
        """Get appropriate test commands for a specific device type.
        
        Args:
            device_type: The device type to get test commands for.
            
        Returns:
            List[str]: A list of test commands, ordered by preference.
        """
        # Define commands for different device types
        commands = {
            DeviceType.CISCO_IOS: ["show version", "show running-config | include hostname", "terminal length 0"],
            DeviceType.CISCO_NXOS: ["show version", "show hostname", "terminal length 0"],
            DeviceType.JUNIPER_JUNOS: ["show version", "show configuration | match host-name", "set cli screen-length 0"],
            DeviceType.ARISTA_EOS: ["show version", "show hostname", "terminal length 0"],
            DeviceType.PALOALTO_PANOS: ["show system info", "show hostname", "set cli pager off"],
            DeviceType.HP_COMWARE: ["display version", "display current-configuration | include sysname", "screen-length disable"],
            DeviceType.HP_PROCURVE: ["show version", "show running-config | include hostname", "no page"],
            DeviceType.HUAWEI_VRP: ["display version", "display current-configuration | include sysname", "screen-length 0 temporary"],
            DeviceType.DELL_OS10: ["show version", "show running-configuration | grep hostname", "terminal length 0"],
            DeviceType.DELL_POWERCONNECT: ["show version", "show running-config | find hostname", "terminal datadump"],
            DeviceType.CHECKPOINT_GAIA: ["show version all", "show hostname", "set clienv rows 0"],
            DeviceType.FORTINET_FORTIOS: ["get system status", "get system hostname", "config system console\nset output standard\nend"]
        }
        
        # Default test commands for any device type
        default_commands = ["show version", "terminal length 0"]
        
        # Return device-specific commands if available, otherwise fallback to default
        return commands.get(device_type, default_commands)

    def discover_devices(self, subnet: str, timeout: int = 5) -> List[Dict[str, str]]:
        """Discovers network devices in the specified subnet using SNMP/ICMP."""
        discovered_devices = []
        self._discovery_running = True

        # Implementation will use asyncio for concurrent device discovery
        # This is a placeholder for the actual implementation
        return discovered_devices

    def add_device(self, device: Device) -> None:
        """Add a device to the manager."""
        self.devices[device.name] = device
        # Notify listeners that the devices list has changed
        if hasattr(self, 'on_devices_changed') and callable(self.on_devices_changed):
            self.on_devices_changed()
        self.save_devices()

    def remove_device(self, device_name: str) -> None:
        """Remove a device from the manager."""
        if device_name in self.devices:
            # Remove device from all groups
            device = self.devices[device_name]
            for group in self.groups.values():
                if device in group.devices:
                    group.remove_device(device)
            # Remove device
            del self.devices[device_name]
            # Notify listeners that the devices list has changed
            if hasattr(self, 'on_devices_changed') and callable(self.on_devices_changed):
                self.on_devices_changed()
            self.save_devices()

    def add_group(self, group: DeviceGroup) -> None:
        """Add a group to the manager."""
        self.groups[group.name] = group
        self.save_groups()

    def remove_group(self, group_name: str) -> None:
        """Remove a group from the manager."""
        if group_name in self.groups:
            del self.groups[group_name]
            self.save_groups()

    def add_device_to_group(self, device_name: str, group_name: str) -> None:
        """Adds a device to a group."""
        if device_name not in self.devices or group_name not in self.groups:
            raise ValueError("Device or group not found")
        self.groups[group_name].add_device(self.devices[device_name])

    def get_devices_by_type(self, device_type: DeviceType) -> List[Device]:
        """Returns all devices of a specific type.
        
        Args:
            device_type: The device type to filter by, can be a DeviceType enum or a string
            
        Returns:
            List[Device]: List of devices matching the specified type
        """
        # Handle both DeviceType enum and string inputs
        if isinstance(device_type, str):
            try:
                # Try to convert string to enum
                device_type_enum = DeviceType(device_type.lower())
            except ValueError:
                # If string doesn't match exactly, try case-insensitive match
                for dt in DeviceType:
                    if dt.value.lower() == device_type.lower():
                        device_type_enum = dt
                        break
                else:
                    # No match found, return empty list
                    logging.warning(f"Invalid device type: {device_type}")
                    return []
        else:
            device_type_enum = device_type
            
        return [device for device in self.devices.values()
                if device.device_type == device_type_enum]

    def get_device_status_summary(self) -> Dict[str, int]:
        """Returns a summary of device connection statuses."""
        summary = {status.value: 0 for status in ConnectionStatus}
        for device in self.devices.values():
            summary[device.connection_status.value] += 1
        return summary

    def to_dict(self) -> Dict:
        """Converts the manager instance to a dictionary for serialization."""
        return {
            "devices": {name: device.to_dict() for name, device in self.devices.items()},
            "groups": {name: group.to_dict() for name, group in self.groups.items()}
        }

    @classmethod
    def from_dict(cls, data: Dict) -> 'DeviceManager':
        """Creates a DeviceManager instance from a dictionary."""
        manager = cls()
        
        # Restore devices
        for device_data in data.get("devices", {}).values():
            device = Device.from_dict(device_data)
            manager.add_device(device)
        
        # Restore groups
        for group_data in data.get("groups", {}).values():
            group = DeviceGroup.from_dict(group_data)
            manager.groups[group.name] = group
            
            # Restore device references in groups
            for device_data in group_data.get("devices", []):
                if device_data["name"] in manager.devices:
                    group.add_device(manager.devices[device_data["name"]])
        
        return manager

    async def bulk_upload_devices(self, devices_config: List[Dict[str, str]], update_existing: bool = False) -> List[Tuple[str, bool, Optional[str]]]:
        """Uploads multiple device configurations simultaneously.

        Args:
            devices_config: List of device configurations, each containing:
                - name: Device name
                - ip_address: Device IP address
                - device_type: Type of device
                - username: Login username
                - password: Login password
                - enable_password: Enable password (optional)
                - port: Connection port (optional)

        Returns:
            List[Tuple[str, bool, Optional[str]]]: List of tuples containing:
                - Device name
                - Success status
                - Error message if failed, None if successful
        """
        logging.info(f"Starting bulk upload of {len(devices_config)} devices")
        results = []
        for device_config in devices_config:
            device_name = device_config.get('name')
            logging.debug(f"Processing device: {device_name}")
            if device_name in self.devices:
                if update_existing:
                    try:
                        device = Device.from_dict(device_config)
                        # Update existing device configuration
                        self.devices[device_name] = device
                        logging.info(f"Updated existing device: {device_name}")
                        results.append((device_name, True, "Updated device configuration"))
                    except Exception as e:
                        logging.error(f"Failed to update device {device_name}: {str(e)}")
                        results.append((device_name, False, str(e)))
                else:
                    logging.warning(f"Device with name {device_name} already exists and update_existing is False")
                    results.append((device_name, False, "Device with this name already exists"))
            else:
                try:
                    device = Device.from_dict(device_config)
                    self.add_device(device)
                    logging.info(f"Added new device: {device_name}")
                    results.append((device_name, True, "Added new device"))
                except Exception as e:
                    logging.error(f"Failed to add device {device_name}: {str(e)}")
                    results.append((device_name, False, str(e)))
        self.save_devices()
        logging.info(f"Completed bulk upload with {len(results)} results")
        return results