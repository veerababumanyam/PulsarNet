from enum import Enum

class DeviceType(Enum):
    """Enumeration of supported network device types."""
    CISCO_IOS = "cisco_ios"
    CISCO_NXOS = "cisco_nxos"
    CISCO_XE = "cisco_xe"
    CISCO_ASA = "cisco_asa"
    CISCO_WLC = "cisco_wlc"
    CISCO_XR = "cisco_xr"
    JUNIPER = "juniper"
    HP = "hp"
    ARISTA = "arista"
    PALOALTO = "paloalto"
    FORTINET = "fortinet"
    CHECKPOINT = "checkpoint"
    LINUX = "linux"
    UNIX = "unix"

    @classmethod
    def get_display_name(cls, device_type: str) -> str:
        """Get a human-readable display name for a device type."""
        display_names = {
            cls.CISCO_IOS.value: "Cisco IOS",
            cls.CISCO_NXOS.value: "Cisco Nexus",
            cls.CISCO_XE.value: "Cisco IOS-XE",
            cls.CISCO_ASA.value: "Cisco ASA",
            cls.CISCO_WLC.value: "Cisco WLC",
            cls.CISCO_XR.value: "Cisco IOS-XR",
            cls.JUNIPER.value: "Juniper",
            cls.HP.value: "HP",
            cls.ARISTA.value: "Arista",
            cls.PALOALTO.value: "Palo Alto",
            cls.FORTINET.value: "Fortinet",
            cls.CHECKPOINT.value: "CheckPoint",
            cls.LINUX.value: "Linux",
            cls.UNIX.value: "Unix"
        }
        return display_names.get(device_type, device_type)