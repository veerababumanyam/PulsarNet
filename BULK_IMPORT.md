# Bulk Import Devices for PulsarNet

This document explains how to bulk import devices into PulsarNet using either a CSV or JSON template file.

## Overview

PulsarNet supports bulk import of devices to streamline the configuration process. You can use a CSV file (default) or a JSON file to define the device configurations. The bulk import feature also supports devices that use a jump host for access.

## CSV Template Format

The CSV file should include the following columns:

- **name**: The unique name of the device.
- **ip_address**: The device's IP address.
- **device_type**: The type of device (e.g., `cisco_ios`, `juniper_junos`, etc.).
- **username**: The login username.
- **password**: The login password.
- **enable_password**: The enable password (if applicable).
- **port**: The connection port (default is 22 for SSH, 23 for Telnet).
- **protocol**: The protocol to use for the device connection (`ssh` or `telnet`).
- **connection_type**: The connection type (`direct_ssh`, `direct_telnet`, or `jump_host`).
- **jump_server**: The jump host's IP address (required if `connection_type` is `jump_host`).
- **jump_host_name**: A friendly name for the jump host.
- **jump_username**: The username for the jump host.
- **jump_password**: The password for the jump host.
- **jump_protocol**: The protocol for connecting to the jump host (`ssh` or `telnet`).
- **jump_port**: The port for connecting to the jump host (default is 22 for SSH, 23 for Telnet).
- **use_keys**: Set to `true` to use SSH key authentication, otherwise `false`.
- **key_file**: The path to the SSH key file (required if `use_keys` is `true`).
- **groups**: Comma-separated list of device groups to add this device to.

### Example CSV Template

```csv
name,ip_address,device_type,username,password,enable_password,port,protocol,connection_type,jump_server,jump_host_name,jump_username,jump_password,jump_protocol,jump_port,use_keys,key_file,groups
Router-1,192.168.1.1,cisco_ios,admin,password123,enable123,22,ssh,direct_ssh,,,,,,,,false,,Core,Production
Switch-1,10.0.0.1,cisco_ios,admin,password123,enable123,22,ssh,jump_host,192.168.1.100,JumpServer1,jump_user,jump_pass,ssh,22,false,,Access,Production
```

## Jump Host Configuration

When using a jump host, set `connection_type` to `jump_host` and provide the following:

1. **Device connection details**:
   - `protocol`: Protocol to connect to the end device (`ssh` or `telnet`)
   - `port`: Port to connect to the end device

2. **Jump host connection details**:
   - `jump_server`: IP address of the jump host
   - `jump_host_name`: Name of the jump host
   - `jump_username`: Username for the jump host
   - `jump_password`: Password for the jump host
   - `jump_protocol`: Protocol to connect to the jump host (`ssh` or `telnet`)
   - `jump_port`: Port to connect to the jump host

The system will automatically determine the appropriate connection type based on the protocols specified:
- SSH jump host to SSH device: `jump_ssh/ssh`
- SSH jump host to Telnet device: `jump_ssh/telnet`
- Telnet jump host to SSH device: `jump_telnet/ssh`
- Telnet jump host to Telnet device: `jump_telnet/telnet`

## JSON Template Format

Alternatively, you can use a JSON file with the following structure:

```json
{
  "devices": [
    {
      "name": "Router-1",
      "ip_address": "192.168.1.1",
      "device_type": "cisco_ios",
      "username": "admin",
      "password": "password123",
      "enable_password": "enable123",
      "port": 22,
      "protocol": "ssh",
      "connection_type": "direct_ssh",
      "use_keys": false,
      "key_file": "",
      "groups": ["Core", "Production"]
    },
    {
      "name": "Switch-1",
      "ip_address": "10.0.0.1",
      "device_type": "cisco_ios",
      "username": "admin",
      "password": "password123",
      "enable_password": "enable123",
      "port": 22,
      "protocol": "ssh",
      "connection_type": "jump_host",
      "jump_server": "192.168.1.100",
      "jump_host_name": "JumpServer1",
      "jump_username": "jump_user",
      "jump_password": "jump_pass",
      "jump_protocol": "ssh",
      "jump_port": 22,
      "use_keys": false,
      "key_file": "",
      "groups": ["Access", "Production"]
    }
  ]
}
```

## Running the Bulk Import

To run the bulk import, use the following command:

```bash
python bulk_import.py [template_file]
```

If no template file is specified, the script defaults to `bulk_import_template.csv`. If the template file doesn't exist, a new template file will be created.

## Notes

- Ensure that device names are unique.
- The `device_type` must match one of the valid types supported by PulsarNet (e.g., `cisco_ios`, `juniper_junos`, etc.).
- For devices using a jump host, the following fields must be provided:
  - `connection_type`: Set to `jump_host`.
  - `jump_server`, `jump_username`, and `jump_password`.
  - `jump_protocol`: Must be one of the supported options: `ssh` or `telnet`.
- When using SSH key authentication, both `use_keys` must be set to `true` and the `key_file` must contain a valid path to an SSH key file.

For further details, please refer to the PulsarNet documentation. 