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

class DeviceManager:
    """Class for managing network devices and their operations."""

    def __init__(self):
        """Initialize DeviceManager."""
        self.devices: Dict[str, Device] = {}
        self.groups: Dict[str, DeviceGroup] = {}
        self._discovery_running = False
        self._connection_pool: Dict[str, asyncio.Queue] = {}
        self._encryption_key = Fernet.generate_key()
        self._cipher_suite = Fernet(self._encryption_key)
        self._max_pool_size = 10
        
        # Create data directory if it doesn't exist
        self.data_dir = os.path.join(os.path.expanduser('~'), '.pulsarnet')
        os.makedirs(self.data_dir, exist_ok=True)
        
        # Load saved data
        self.load_devices()
        self.load_groups()

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
        """
        if device.ip_address not in self._connection_pool:
            self._connection_pool[device.ip_address] = asyncio.Queue(maxsize=self._max_pool_size)

        try:
            connection = await self._connection_pool[device.ip_address].get()
            return connection
        except asyncio.QueueEmpty:
            # Create new connection if pool is empty
            connection_params = {
                'device_type': device.device_type.value,
                'host': device.ip_address,
                'username': device.username,
                'password': self._decrypt_credentials(device.password),
                'port': device.port
            }
            return netmiko.ConnectHandler(**connection_params)

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
        """Tests connection to a device and updates its status."""
        connection = None
        try:
            connection = await self._get_connection(device)
            await connection.send_command('show version')
            device.update_connection_status(ConnectionStatus.CONNECTED)
            return True, None
        except Exception as e:
            device.update_connection_status(ConnectionStatus.ERROR)
            return False, str(e)
        finally:
            if connection:
                await self._release_connection(device.name, connection)

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
        """Returns all devices of a specific type."""
        return [device for device in self.devices.values()
                if device.device_type == device_type]

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

    async def bulk_upload_devices(self, devices_config: List[Dict[str, str]]) -> List[Tuple[str, bool, Optional[str]]]:
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
        results = []
        tasks = []

        for config in devices_config:
            try:
                device = Device(
                    name=config['name'],
                    ip_address=config['ip_address'],
                    device_type=DeviceType(config['device_type']),
                    username=config['username'],
                    password=config['password'],
                    enable_password=config.get('enable_password'),
                    port=config.get('port', 22)
                )
                self.add_device(device)
                tasks.append(self.test_device_connection(device))
            except Exception as e:
                results.append((config.get('name', 'Unknown'), False, str(e)))
                continue

        # Test connections concurrently
        if tasks:
            connection_results = await asyncio.gather(*tasks, return_exceptions=True)
            for device, (success, error) in zip(devices_config, connection_results):
                results.append((device['name'], success, error))

        return results