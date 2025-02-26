"""Legacy Device Module for PulsarNet.

This module defines the LegacyDevice class for managing legacy Cisco devices
that require Telnet access, potentially through jump hosts.
"""

from dataclasses import dataclass
from enum import Enum
from typing import Optional, List

class ConnectionType(Enum):
    """Supported connection types for legacy devices."""
    DIRECT_TELNET = "direct_telnet"
    VIA_JUMP_HOST = "via_jump_host"

@dataclass
class LegacyDevice:
    """Represents a legacy Cisco device that requires Telnet access.
    
    This class extends the base device functionality to support Telnet
    connections and access through jump hosts.
    """
    name: str
    ip_address: str
    username: str
    password: str
    enable_password: Optional[str] = None
    port: int = 23  # Default Telnet port
    connection_type: ConnectionType = ConnectionType.DIRECT_TELNET
    device_type: str = 'Legacy Telnet'  # Add device type attribute
    jump_host_ip: Optional[str] = None
    jump_host_username: Optional[str] = None
    jump_host_password: Optional[str] = None
    jump_host_enable_password: Optional[str] = None
    command_timeout: int = 30
    connection_timeout: int = 10
    custom_commands: List[str] = None

    def __post_init__(self):
        """Initialize additional attributes after instance creation."""
        self.custom_commands = self.custom_commands or []
        self.connection_status = "disconnected"
        self.last_backup_status = None
        self.last_backup_time = None
        self.last_error = None

    def validate(self) -> bool:
        """Validate device configuration.

        Returns:
            bool: True if configuration is valid, False otherwise.
        """
        if not all([self.name, self.ip_address, self.username, self.password]):
            return False

        if self.connection_type == ConnectionType.VIA_JUMP_HOST:
            if not all([self.jump_host_ip, self.jump_host_username, 
                        self.jump_host_password]):
                return False

        return True

    def to_dict(self) -> dict:
        """Convert device information to dictionary format.

        Returns:
            dict: Device information in dictionary format.
        """
        return {
            'name': self.name,
            'ip_address': self.ip_address,
            'username': self.username,
            'password': self.password,
            'enable_password': self.enable_password,
            'port': self.port,
            'connection_type': self.connection_type.value,
            'jump_host_ip': self.jump_host_ip,
            'jump_host_username': self.jump_host_username,
            'jump_host_password': self.jump_host_password,
            'jump_host_enable_password': self.jump_host_enable_password,
            'command_timeout': self.command_timeout,
            'connection_timeout': self.connection_timeout,
            'custom_commands': self.custom_commands,
            'connection_status': self.connection_status,
            'last_backup_status': self.last_backup_status,
            'last_backup_time': self.last_backup_time,
            'last_error': self.last_error
        }

    @classmethod
    def from_dict(cls, data: dict) -> 'LegacyDevice':
        """Create a LegacyDevice instance from dictionary data.

        Args:
            data (dict): Dictionary containing device information.

        Returns:
            LegacyDevice: New instance created from dictionary data.
        """
        # Convert connection_type string to enum
        if 'connection_type' in data:
            data['connection_type'] = ConnectionType(data['connection_type'])

        return cls(**{k: v for k, v in data.items() if k in cls.__annotations__})