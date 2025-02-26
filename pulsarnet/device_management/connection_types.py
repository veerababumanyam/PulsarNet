from enum import Enum

class DeviceConnectionType(Enum):
    """Enum representing various device connection scenarios."""
    DIRECT_TELNET = "direct_telnet"
    DIRECT_SSH = "direct_ssh"
    JUMP_TELNET_DEVICE_TELNET = "jump_telnet/telnet"
    JUMP_TELNET_DEVICE_SSH = "jump_telnet/ssh"
    JUMP_SSH_DEVICE_TELNET = "jump_ssh/telnet"
    JUMP_SSH_DEVICE_SSH = "jump_ssh/ssh"
    
class ConnectionStatus(Enum):
    """Enum representing device connection status."""
    UNKNOWN = "Unknown"
    CONNECTED = "Connected"
    DISCONNECTED = "Disconnected"
    FAILED = "Failed"
    IN_PROGRESS = "In Progress"
    BACKUP_FAILED = "Backup Failed"
    BACKUP_SUCCESS = "Backup Success"
    BACKUP_IN_PROGRESS = "Backup In Progress"
    ERROR = "Error"
    TIMEOUT = "Timeout" 