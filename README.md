# PulsarNet

A robust GUI application designed to streamline the backup processes of various network devices, including those from Cisco, Juniper, HP, and other major network device vendors. PulsarNet provides a comprehensive solution for network device configuration management with automated backup capabilities, real-time monitoring, and advanced configuration comparison features.

## Features

- **Multi-vendor Support**
  - Compatible with Cisco, Juniper, HP, Arista, Palo Alto, and other major network device vendors
  - Vendor-specific configuration validation
  - Customizable device templates

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

## Backup Features

- Real-time status updates
- Color-coded status indicators (green=success, red=failure)
- Automatic paging/terminal length adjustment
- Config saved with timestamp
- Backup files stored in `~/.pulsarnet/backups/`

## Installation

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

## Usage

### Basic Operations

1. **Adding Devices**
   - Launch PulsarNet
   - Click "Add Device" in the main window
   - Enter device details (IP, credentials, vendor)
   - Select backup protocol and schedule

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

- **Monitoring**
  - Track backup status in real-time
  - View detailed operation logs
  - Configure email notifications

## Project Structure

```
pulsarnet/
├── backup_operations/    # Backup protocol implementations
├── device_management/    # Device and group management
├── gui/                  # PyQt6 GUI components
├── monitoring/           # Logging and monitoring
├── scheduler/            # Backup scheduling
└── storage_management/   # Storage and retention
```

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
