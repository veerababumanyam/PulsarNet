"""DeviceGroup class for managing groups of network devices in PulsarNet.

This module provides functionality for organizing devices into logical groups
for easier management and batch operations.
"""

from typing import List, Dict, Optional
from .device import Device

class DeviceGroup:
    """Class representing a group of network devices."""

    def __init__(self, name: str, description: Optional[str] = None):
        self.name = name
        self.description = description
        self.devices: List[Device] = []
        self.custom_attributes: Dict[str, str] = {}

    def add_device(self, device: Device) -> None:
        """Adds a device to the group."""
        if device not in self.devices:
            self.devices.append(device)

    def remove_device(self, device: Device) -> None:
        """Removes a device from the group."""
        if device in self.devices:
            self.devices.remove(device)

    def get_devices(self) -> List[Device]:
        """Returns all devices in the group."""
        return self.devices

    def get_device_by_name(self, name: str) -> Optional[Device]:
        """Retrieves a device by its name."""
        for device in self.devices:
            if device.name == name:
                return device
        return None

    def get_devices_by_type(self, device_type: str) -> List[Device]:
        """Returns all devices of a specific type in the group."""
        return [device for device in self.devices 
                if device.device_type.value == device_type]

    def set_custom_attribute(self, key: str, value: str) -> None:
        """Sets a custom attribute for the group."""
        self.custom_attributes[key] = value

    def get_custom_attribute(self, key: str) -> Optional[str]:
        """Retrieves a custom attribute value."""
        return self.custom_attributes.get(key)

    def to_dict(self) -> Dict:
        """Converts the group instance to a dictionary for serialization."""
        return {
            "name": self.name,
            "description": self.description,
            "devices": [device.to_dict() for device in self.devices],
            "custom_attributes": self.custom_attributes
        }

    @classmethod
    def from_dict(cls, data: Dict) -> 'DeviceGroup':
        """Creates a DeviceGroup instance from a dictionary."""
        group = cls(
            name=data["name"],
            description=data.get("description")
        )
        group.custom_attributes = data.get("custom_attributes", {})
        
        # Devices should be added separately to maintain proper object references
        return group

    @property
    def members(self) -> List[Device]:
        return self.devices

    @members.setter
    def members(self, value: List[Device]) -> None:
        self.devices = value