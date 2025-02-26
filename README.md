# PulsarNet

A robust application designed to streamline the backup processes of various network devices, including those from Cisco, Juniper, HP, and other major network device vendors. PulsarNet provides a comprehensive solution for network device configuration management with automated backup capabilities, real-time monitoring, and advanced configuration comparison features.

## New Features (v1.0.1)

- **SQLite Database Backend** - Improved data integrity, faster queries, and better reliability
- **REST API** - Full-featured API for automation and integration with other systems
- **Device Template Management** - Templatize backup commands and connection settings
- **Enhanced Logging** - Comprehensive logging with syslog forwarding and audit trail
- **Backup Verification** - Automatic verification of backup integrity and content validation
- **Database-backed Scheduler** - More reliable scheduling with enhanced recurrence options
- **Docker Support** - Easy deployment using containers via Docker and docker-compose
- **Modern Async Approach** - Improved concurrency with modern async/await patterns
- **Security Hardening** - Enhanced credential management and encryption

## Features

- **Multi-vendor Support**
  - Compatible with Cisco, Juniper, HP, Arista, Palo Alto, and other major network device vendors
  - Vendor-specific configuration validation
  - Customizable device templates
  - Legacy device support via Telnet
  - Jump host configuration for remote access

- **Flexible Backup Options**
  - Multiple protocol support (TFTP, SCP, SFTP, FTP)
  - Scheduled automated backups
  - On-demand manual backups
  - Batch operations for device groups

- **Advanced Management**
  - Modern PyQt6-based GUI interface
  - Real-time backup monitoring
  - Comprehensive error handling and logging
  - Configuration comparison and validation
  - Device grouping capabilities

- **Storage & Retention**
  - Configurable storage locations
  - Customizable retention policies
  - Backup verification
  - Secure credential management

## Supported Device Types

| Vendor         | Device Type       | Backup Method                     |
|----------------|-------------------|-----------------------------------|
| Cisco          | IOS               | `show running-config`             |
| Cisco          | NX-OS             | `show running-config`             |
| Juniper        | JunOS             | `show configuration | display set` |
| Arista         | EOS               | `show running-config`             |
| Palo Alto      | PAN-OS            | `show config running format xml`   |
| HP             | Comware           | `display current-configuration`   |
| HP             | ProCurve          | `show running-config`             |
| Huawei         | VRP               | `display current-configuration`   |
| Dell           | OS10              | `show running-configuration`       |
| Dell           | PowerConnect      | `show running-config`             |
| CheckPoint     | Gaia              | `show configuration`              |
| Fortinet       | FortiOS           | `show full-configuration`         |

## Backup Process Architecture

PulsarNet implements a robust, secure backup process following ISO/IEC 27001 security standards designed to work reliably in complex enterprise environments with network segmentation and strict firewall policies.

### Configuration Data Flow

```
Target Device → Jump Host (if used) → PulsarNet Application → Storage Location
```

This architecture ensures that:
- Network devices don't need direct access to storage servers
- Minimal firewall exceptions are required
- Security boundaries between network segments are maintained

### Connection Types and Protocol Selection

| Connection Type | Protocol Used | Ideal Use Case |
|----------------|--------------|----------------|
| Direct SSH | SCP | Devices with direct management access |
| Direct Telnet | TFTP | Legacy devices requiring Telnet access |
| Jump Host SSH → Device SSH | SFTP | Secure access to segmented networks |
| Jump Host SSH → Device Telnet | SFTP | Legacy devices in segmented networks |
| Jump Host Telnet → Device SSH/Telnet | SFTP | Complex legacy network topologies |

PulsarNet automatically selects the appropriate protocol based on the device's configured connection type, ensuring optimal security and compatibility.

### Backup Storage Options

- **Local Storage**: Configurations are saved to the local filesystem by default
- **Remote Storage**: Optional transfer to remote servers via SFTP/FTP/TFTP
- **Naming Convention**: `<device_name>_<ip_address>_<timestamp>.cfg`
- **Differential Backups**: Only stores new configurations when changes are detected

### Enterprise Security Considerations

- No outbound connections required from sensitive network devices
- No storage server credentials stored on network equipment
- End-to-end encryption for secure data transfer
- Minimal access requirements for target devices

For more detailed information, please refer to the [help documentation](pulsarnet/docs/help.html) included with the application.

## Installation

### Standard Installation

1. Clone the repository:
```bash
git clone https://github.com/yourusername/PulsarNet.git
cd PulsarNet
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Configure the application:
- Copy `.env.example` to `.env`
- Update the configuration settings in `.env`

4. Run the application:
```bash
python -m pulsarnet
```

### Docker Installation

1. Clone the repository:
```bash
git clone https://github.com/yourusername/PulsarNet.git
cd PulsarNet
```

2. Build and run with Docker Compose:
```bash
docker-compose up -d
```

3. Access the API at http://localhost:8000

## Usage

### Basic Operations

1. **Adding Devices**
   - Launch PulsarNet
   - Click "Add Device" in the main window
   - Enter device details (IP, credentials, vendor)
   - Select backup protocol and schedule
   - For legacy devices, use the "Legacy Devices" tab
   - Configure jump host settings if required for remote access

2. **Creating Device Groups**
   - Use the "Groups" menu to create and manage device groups
   - Add devices to groups for batch operations

3. **Configuring Backups**
   - Select devices or groups
   - Choose backup protocol (TFTP/SCP/SFTP/FTP)
   - Set backup schedule and retention policy
   - Configure storage location

### Advanced Features

- **Configuration Comparison**
  - Compare backup versions
  - View detailed configuration changes
  - Export comparison reports

- **Backup Verification**
  - Verify backup integrity with checksums
  - Validate configuration content against expected patterns
  - Compare configurations for compliance

- **API Integration**
  - Use the REST API for automation and integration
  - Full documentation available at `/docs` endpoint

- **Monitoring**
  - Track backup status in real-time
  - View detailed operation logs
  - Configure email notifications
  - Forward logs to syslog server

## Project Structure

```
pulsarnet/
├── api/                  # REST API implementation
├── backup_operations/    # Backup protocol implementations
├── database/             # Database access and schema
├── device_management/    # Device and group management
├── gui/                  # PyQt6 GUI components
├── monitoring/           # Logging and monitoring
├── verification/         # Backup verification
├── scheduler/            # Backup scheduling
├── utils/                # Utility functions and logging
└── storage_management/   # Storage and retention
```

## API Endpoints

The REST API provides the following endpoints:

- `/health` - API health check
- `/devices` - Manage network devices
- `/groups` - Manage device groups
- `/templates` - Manage device templates
- `/backups` - Manage and trigger backup operations
- `/backups/verify/{id}` - Verify backup integrity
- `/schedules` - Manage backup schedules

Full API documentation is available when running the server:

```
http://localhost:8000/docs
```

# Device Import Template
This directory contains templates for importing devices into PulsarNet.

## CSV Template Format
The `devices_template.csv` file shows the format for bulk device imports. Here's the field description:

### Required Fields
- `name`: Unique device name
- `ip_address`: IP address of the device
- `device_type`: Type of device (see supported types below)
- `username`: SSH username
- `password`: SSH password

### Optional Fields
- `enable_password`: Enable password for privileged mode
- `port`: SSH port number (default: 22)
- `description`: Device description

### Supported Device Types
The following device types are supported (case-insensitive):

#### Legacy Devices
- `legacy_cisco`: Legacy Cisco devices (Telnet)
- `legacy_juniper`: Legacy Juniper devices (Telnet)
- `legacy_hp`: Legacy HP devices (Telnet)

#### Jump Host Configuration
- `jump_host`: Intermediate server for remote device access
- `jump_host_telnet`: Telnet-based jump host
- `jump_host_ssh`: SSH-based jump host

#### Cisco Devices
- `cisco_ios`: Cisco IOS devices
- `cisco_nxos`: Cisco Nexus devices
- `cisco_xe`: Cisco IOS-XE devices
- `cisco_asa`: Cisco ASA firewalls
- `cisco_wlc`: Cisco Wireless LAN Controllers
- `cisco_xr`: Cisco IOS-XR devices

#### Juniper Devices
- `juniper`: Juniper devices (Generic)
- `juniper_junos`: Juniper JunOS devices

#### Arista Devices
- `arista_eos`: Arista EOS switches

#### HP Devices
- `hp_procurve`: HP ProCurve switches
- `hp_comware`: HP Comware devices

#### Huawei Devices
- `huawei`: Huawei devices (Generic)
- `huawei_vrpv8`: Huawei VRP v8 devices

#### Other Network Vendors
- `f5_ltm`: F5 LTM load balancers
- `fortinet`: Fortinet devices
- `paloalto_panos`: Palo Alto PAN-OS firewalls
- `checkpoint_gaia`: Check Point Gaia firewalls
- `alcatel_aos`: Alcatel AOS switches
- `dell_force10`: Dell Force10 switches
- `extreme`: Extreme Networks devices
- `mikrotik_routeros`: MikroTik RouterOS devices
- `ubiquiti_edge`: Ubiquiti EdgeOS devices
- `brocade_nos`: Brocade NOS devices

#### System Devices
- `linux`: Linux systems
- `unix`: Unix systems

## Contributing
1. Fork the repository
2. Create a feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit your changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

## License
Apache License 2.0

## Author
Veera Babu Manyam / veerababumanyam@gmail.com
