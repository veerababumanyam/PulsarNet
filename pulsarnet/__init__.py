"""PulsarNet - Network Device Backup Management System.

A robust GUI application designed to streamline the backup processes of various
network devices, including those from Cisco, Juniper, and HP.
"""

from .device_management import DeviceManager, Device, DeviceGroup

__version__ = '1.0.0'
__author__ = 'Veera Babu Manyam'
__license__ = 'Apache License 2.0'

__all__ = ['DeviceManager', 'Device', 'DeviceGroup']