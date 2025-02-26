"""Legacy Device Support Module for PulsarNet.

This module provides support for legacy Cisco devices that rely on Telnet
and require access through intermediary routers (jump hosts).
"""

from .legacy_device import LegacyDevice, ConnectionType
from .legacy_manager import LegacyDeviceManager
from .telnet_session import TelnetSession
from .jump_host import JumpHost

__all__ = ['LegacyDevice', 'ConnectionType', 'LegacyDeviceManager', 'TelnetSession', 'JumpHost']