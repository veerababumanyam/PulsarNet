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

## Usage
1. Copy the template file
2. Fill in your device details
3. Use the Import button in PulsarNet's Device tab
4. Select your filled CSV file
5. Verify imported devices in the device table

## Notes
- The first line must contain the header names
- Fields should be comma-separated
- Text fields containing commas should be enclosed in quotes
- Empty optional fields can be left blank
- Device types are case-insensitive (e.g., both `cisco_ios` and `CISCO_IOS` work)
- Each device must have a unique name

## Example CSV Content
```csv
name,ip_address,device_type,username,password,enable_password,port,description
switch01,192.168.1.1,cisco_ios,admin,admin_pass,enable_pass,22,Core Switch
router01,192.168.1.2,cisco_nxos,admin,admin_pass,enable_pass,22,Edge Router
firewall01,192.168.1.3,cisco_asa,admin,admin_pass,enable_pass,22,Main Firewall
```

## Error Handling
- Missing required fields will be reported
- Invalid device types will show available options
- Connection errors will be displayed with details
- Import results will show success/failure counts
