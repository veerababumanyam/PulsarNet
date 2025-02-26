"""PulsarNet - Network Device Backup Management System.

A robust application designed to streamline the backup processes of various
network devices, including those from Cisco, Juniper, Arista, and HP.
"""

from .device_management import DeviceManager, Device, DeviceGroup, DeviceTemplateManager
from .database import DatabaseManager
from .scheduler import DBScheduleManager
from .verification import BackupVerifier
from .utils.logging_config import LoggingManager, AuditLogger, MetricLogger
from .backup_operations import BackupManager
from .consolidation import DeviceConsolidationManager, ConsolidationPlan, ConsolidationGroup

__version__ = '1.0.1'
__author__ = 'Veera Babu Manyam'
__license__ = 'Apache License 2.0'

__all__ = [
    'DeviceManager', 'Device', 'DeviceGroup', 'DeviceTemplateManager',
    'DatabaseManager', 'DBScheduleManager', 'BackupManager', 'BackupVerifier',
    'LoggingManager', 'AuditLogger', 'MetricLogger',
    'DeviceConsolidationManager', 'ConsolidationPlan', 'ConsolidationGroup'
]