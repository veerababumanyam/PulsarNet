"""DeviceDialog class for adding and editing network devices in PulsarNet.

This module implements a dialog for device management operations following
ISO 9241-171:2008 accessibility standards.
"""

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QFormLayout, QLineEdit,
    QComboBox, QPushButton, QDialogButtonBox,
    QSpinBox, QCheckBox, QMessageBox, QGroupBox,
    QLabel, QListWidget, QListWidgetItem, QTabWidget, QWidget
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont, QPalette, QColor

from ..device_management import Device, DeviceType, ConnectionStatus
from ..device_management.connection_types import DeviceConnectionType

class ConnectionType:
    """Connection types supported by the application."""
    SSH = "SSH"
    TELNET = "Telnet"
    JUMP_HOST = "Via Jump Host"

class DeviceDialog(QDialog):
    """Dialog for adding or editing network devices."""

    def __init__(self, parent=None, device_manager=None, device: Device = None):
        """Initialize the dialog.
        
        Args:
            parent: Parent widget
            device_manager: DeviceManager instance for accessing groups
            device: Optional device to edit
        """
        super().__init__(parent)
        self.device = device
        self.device_manager = device_manager
        self.init_ui()

    def init_ui(self):
        """Initialize the user interface."""
        self.setWindowTitle('Add Device' if not self.device else 'Edit Device')
        self.setMinimumWidth(500)

        # Create layouts
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(15, 15, 15, 15)
        main_layout.setSpacing(10)

        self.setup_style(main_layout)
        
        # Create tab widget for better organization
        tab_widget = QTabWidget()
        
        # Basic info tab
        basic_tab = QWidget()
        basic_layout = QVBoxLayout(basic_tab)
        
        # Create group boxes for basic info organization
        basic_info_group = QGroupBox("Basic Information")
        basic_info_layout = QFormLayout()
        basic_info_group.setLayout(basic_info_layout)
        
        # Authentication group
        auth_info_group = QGroupBox("Authentication")
        auth_layout = QFormLayout()
        auth_info_group.setLayout(auth_layout)

        # Basic information fields
        self.name_edit = QLineEdit(self)
        self.name_edit.setPlaceholderText('Enter device name')
        self.name_edit.setMinimumWidth(250)
        basic_info_layout.addRow('Name:', self.name_edit)

        self.ip_edit = QLineEdit(self)
        self.ip_edit.setPlaceholderText('Enter IP address')
        basic_info_layout.addRow('IP Address:', self.ip_edit)

        self.type_combo = QComboBox(self)
        device_types = [
            # Cisco Devices
            'cisco_ios', 'cisco_nxos', 'cisco_xe', 'cisco_asa', 'cisco_wlc', 'cisco_xr',
            # Juniper Devices
            'juniper', 'juniper_junos',
            # Arista Devices
            'arista_eos',
            # HP Devices
            'hp_procurve', 'hp_comware',
            # Huawei Devices
            'huawei', 'huawei_vrpv8',
            # Other Network Vendors
            'f5_ltm', 'fortinet', 'paloalto_panos', 'checkpoint_gaia',
            'alcatel_aos', 'dell_force10', 'extreme', 'mikrotik_routeros',
            'ubiquiti_edge', 'brocade_nos',
            # System Devices
            'linux', 'unix'
        ]
        self.type_combo.addItems(device_types)
        self.type_combo.setCurrentText('cisco_ios')  # Set default selection
        self.type_combo.currentTextChanged.connect(self.on_device_type_changed)
        basic_info_layout.addRow('Device Type:', self.type_combo)

        # Connection type selection with SSH, Telnet, and Jump Host options
        self.connection_type_combo = QComboBox(self)
        self.connection_type_combo.addItems([
            ConnectionType.SSH, 
            ConnectionType.TELNET, 
            ConnectionType.JUMP_HOST
        ])
        self.connection_type_combo.currentTextChanged.connect(self.on_connection_type_changed)
        basic_info_layout.addRow('Connection Type:', self.connection_type_combo)

        # Device Protocol
        self.device_protocol_label = QLabel("Device Protocol:")
        self.device_protocol_combo = QComboBox(self)
        self.device_protocol_combo.addItem("SSH", "ssh")
        self.device_protocol_combo.addItem("Telnet", "telnet")
        basic_info_layout.insertRow(4, self.device_protocol_label, self.device_protocol_combo)

        # Connection parameters
        self.port_spin = QSpinBox(self)
        self.port_spin.setRange(1, 65535)
        self.port_spin.setValue(22)  # Default SSH port
        basic_info_layout.addRow('Port:', self.port_spin)
        
        # Add connection timeout
        self.timeout_spin = QSpinBox(self)
        self.timeout_spin.setRange(1, 300)  # 1-300 seconds
        self.timeout_spin.setValue(30)  # Default 30 seconds
        basic_info_layout.addRow('Timeout (seconds):', self.timeout_spin)
        
        # Authentication fields
        self.username_edit = QLineEdit(self)
        self.username_edit.setPlaceholderText('Enter username')
        auth_layout.addRow('Username:', self.username_edit)

        self.password_edit = QLineEdit(self)
        self.password_edit.setEchoMode(QLineEdit.EchoMode.Password)
        self.password_edit.setPlaceholderText('Enter password')
        auth_layout.addRow('Password:', self.password_edit)

        self.enable_password_edit = QLineEdit(self)
        self.enable_password_edit.setEchoMode(QLineEdit.EchoMode.Password)
        self.enable_password_edit.setPlaceholderText('Enter enable password (optional)')
        auth_layout.addRow('Enable Password:', self.enable_password_edit)
        
        # Jump host configuration group
        self.jump_host_group = QGroupBox("Jump Host Configuration")
        self.jump_host_group.setObjectName("Jump Host Configuration")
        jump_host_layout = QFormLayout()
        self.jump_host_group.setLayout(jump_host_layout)
        self.jump_host_group.setVisible(False)  # Hide by default

        self.jump_host_name = QLineEdit(self)
        self.jump_host_name.setPlaceholderText('Enter jump host name (optional)')
        jump_host_layout.addRow('Jump Host Name:', self.jump_host_name)

        self.jump_host_ip = QLineEdit(self)
        self.jump_host_ip.setPlaceholderText('Enter jump host IP address')
        jump_host_layout.addRow('Jump Host IP:', self.jump_host_ip)

        self.jump_host_port = QSpinBox(self)
        self.jump_host_port.setRange(1, 65535)
        self.jump_host_port.setValue(22)
        jump_host_layout.addRow('Jump Host Port:', self.jump_host_port)

        self.jump_host_username = QLineEdit(self)
        self.jump_host_username.setPlaceholderText('Enter jump host username')
        jump_host_layout.addRow('Jump Host Username:', self.jump_host_username)

        self.jump_host_password = QLineEdit(self)
        self.jump_host_password.setEchoMode(QLineEdit.EchoMode.Password)
        self.jump_host_password.setPlaceholderText('Enter jump host password')
        jump_host_layout.addRow('Jump Host Password:', self.jump_host_password)
        
        # Jump Connection Type
        self.jump_host_protocol_label = QLabel("Jump Protocol:")
        self.jump_host_protocol_combo = QComboBox(self)
        self.jump_host_protocol_combo.addItem("SSH", "ssh")
        self.jump_host_protocol_combo.addItem("Telnet", "telnet")
        jump_host_layout.addRow(self.jump_host_protocol_label, self.jump_host_protocol_combo)

        # Add the groups to the basic tab
        basic_layout.addWidget(basic_info_group)
        basic_layout.addWidget(auth_info_group)
        basic_layout.addWidget(self.jump_host_group)
        
        # Add the basic tab to the tab widget
        tab_widget.addTab(basic_tab, "Basic Settings")
        
        # Advanced tab
        advanced_tab = QWidget()
        advanced_layout = QVBoxLayout(advanced_tab)
        
        # Connection retry settings
        retry_group = QGroupBox("Connection Retry Settings")
        retry_layout = QFormLayout()
        retry_group.setLayout(retry_layout)
        
        self.retry_count_spin = QSpinBox(self)
        self.retry_count_spin.setRange(0, 10)
        self.retry_count_spin.setValue(3)  # Default 3 retries
        retry_layout.addRow('Retry Count:', self.retry_count_spin)
        
        self.retry_delay_spin = QSpinBox(self)
        self.retry_delay_spin.setRange(1, 60)
        self.retry_delay_spin.setValue(5)  # Default 5 seconds
        retry_layout.addRow('Retry Delay (seconds):', self.retry_delay_spin)
        
        # Connection settings based on device type
        conn_settings_group = QGroupBox("Device-Specific Settings")
        conn_settings_layout = QFormLayout()
        conn_settings_group.setLayout(conn_settings_layout)
        
        self.use_keys_checkbox = QCheckBox("Use SSH Keys")
        self.use_keys_checkbox.setChecked(False)
        conn_settings_layout.addRow('', self.use_keys_checkbox)
        
        self.key_file_edit = QLineEdit(self)
        self.key_file_edit.setPlaceholderText('SSH key file path (optional)')
        self.key_file_edit.setEnabled(False)
        key_file_layout = QHBoxLayout()
        key_file_layout.addWidget(self.key_file_edit)
        
        key_browse_btn = QPushButton("Browse...")
        key_browse_btn.clicked.connect(self.browse_key_file)
        key_file_layout.addWidget(key_browse_btn)
        conn_settings_layout.addRow('Key File:', key_file_layout)
        
        self.use_keys_checkbox.toggled.connect(self.key_file_edit.setEnabled)
        self.use_keys_checkbox.toggled.connect(key_browse_btn.setEnabled)
        
        # Add custom fields for advanced settings
        self.custom_settings_label = QLabel("Custom Configuration Commands:")
        self.custom_commands_edit = QLineEdit(self)
        self.custom_commands_edit.setPlaceholderText('Enter custom config commands separated by semicolons')
        conn_settings_layout.addRow(self.custom_settings_label, self.custom_commands_edit)
        
        # Add the groups to the advanced tab
        advanced_layout.addWidget(retry_group)
        advanced_layout.addWidget(conn_settings_group)
        advanced_layout.addStretch()
        
        # Add the advanced tab to the tab widget
        tab_widget.addTab(advanced_tab, "Advanced Settings")
        
        # Groups tab
        groups_tab = QWidget()
        groups_layout = QVBoxLayout(groups_tab)
        
        # Device Groups
        groups_group = QGroupBox("Device Groups")
        groups_layout_inner = QVBoxLayout()
        groups_group.setLayout(groups_layout_inner)
        
        self.groups_list = QListWidget(self)
        groups_layout_inner.addWidget(self.groups_list)
        
        # Populate groups list
        if self.device_manager and self.device_manager.groups:
            for group_name in self.device_manager.groups:
                item = QListWidgetItem(group_name)
                item.setFlags(item.flags() | Qt.ItemFlag.ItemIsUserCheckable)
                item.setCheckState(Qt.CheckState.Unchecked)
                self.groups_list.addItem(item)
        
        # Group management buttons
        groups_btn_layout = QHBoxLayout()
        select_all_btn = QPushButton("Select All")
        select_all_btn.clicked.connect(self.select_all_groups)
        clear_all_btn = QPushButton("Clear All")
        clear_all_btn.clicked.connect(self.clear_group_selection)
        new_group_btn = QPushButton("New Group...")
        new_group_btn.clicked.connect(self.show_create_group_dialog)
        
        groups_btn_layout.addWidget(select_all_btn)
        groups_btn_layout.addWidget(clear_all_btn)
        groups_btn_layout.addWidget(new_group_btn)
        groups_layout_inner.addLayout(groups_btn_layout)
        
        groups_layout.addWidget(groups_group)
        
        # Add the groups tab to the tab widget
        tab_widget.addTab(groups_tab, "Groups")
        
        # Add the tab widget to the main layout
        main_layout.addWidget(tab_widget)
        
        # Button box
        button_box = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | 
            QDialogButtonBox.StandardButton.Cancel
        )
        button_box.accepted.connect(self.validate_and_accept)
        button_box.rejected.connect(self.reject)

        # Add Test Connection button
        test_button = QPushButton("Test Connection")
        test_button.clicked.connect(self.test_connection)
        button_box.addButton(test_button, QDialogButtonBox.ButtonRole.ActionRole)

        main_layout.addWidget(button_box)
        
        # If editing an existing device, populate fields
        if self.device:
            self.populate_fields()
        
        # Set initial connection type behavior
        self.on_connection_type_changed(self.connection_type_combo.currentText())
        self.on_device_type_changed(self.type_combo.currentText())

    def setup_style(self, layout):
        """Setup styling for the dialog."""
        # Set form spacing and margins
        layout.setSpacing(10)
        
        # Set font for better readability
        font = QFont()
        font.setPointSize(10)
        self.setFont(font)
        
        # Set some base styling
        self.setStyleSheet("""
            QGroupBox {
                font-weight: bold;
                border: 1px solid #ccc;
                border-radius: 6px;
                margin-top: 12px;
                padding-top: 10px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 3px;
            }
        """)

    def browse_key_file(self):
        """Browse for SSH key file."""
        from PyQt6.QtWidgets import QFileDialog
        import os
        
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Select SSH Key File",
            os.path.expanduser("~/.ssh/"),
            "All Files (*)"
        )
        
        if file_path:
            self.key_file_edit.setText(file_path)

    def on_connection_type_changed(self, connection_type: str):
        """Handle connection type changes."""
        # Show/hide jump host configuration
        self.jump_host_group.setVisible(connection_type == ConnectionType.JUMP_HOST)
        
        # Update port based on connection type
        if connection_type == ConnectionType.SSH:
            self.port_spin.setValue(22)
        elif connection_type == ConnectionType.TELNET:
            self.port_spin.setValue(23)
            
        # Update SSH key options visibility
        ssh_keys_visible = connection_type == ConnectionType.SSH
        self.use_keys_checkbox.setVisible(ssh_keys_visible)
        self.key_file_edit.setVisible(ssh_keys_visible)
        
        # Adjust dialog size based on visible widgets
        self.adjustSize()

        # Show/hide jump host protocol selection if not needed
        self.jump_host_protocol_combo.hide()
        self.device_protocol_combo.hide()

        if connection_type == ConnectionType.JUMP_HOST:
            # Show additional combo boxes for jump host and device protocols
            self.jump_host_protocol_combo.show()
            self.device_protocol_combo.show()

    def populate_fields(self):
        """Populate form fields when editing an existing device."""
        if not self.device:
            return
            
        # Basic info
        self.name_edit.setText(self.device.name)
        self.ip_edit.setText(self.device.ip_address)
        
        # Try to set device type
        if hasattr(self.device.device_type, 'value'):
            device_type = self.device.device_type.value
        else:
            device_type = str(self.device.device_type)
        
        index = self.type_combo.findText(device_type)
        if index >= 0:
            self.type_combo.setCurrentIndex(index)
        
        # Connection type
        if hasattr(self.device, 'use_jump_server') and self.device.use_jump_server:
            self.connection_type_combo.setCurrentText(ConnectionType.JUMP_HOST)
            
            # Populate jump host fields
            if hasattr(self.device, 'jump_host_name'):
                self.jump_host_name.setText(self.device.jump_host_name)
            if hasattr(self.device, 'jump_server'):
                self.jump_host_ip.setText(self.device.jump_server)
            if hasattr(self.device, 'jump_port'):
                self.jump_host_port.setValue(self.device.jump_port)
            elif hasattr(self.device, 'jump_server_port'):
                self.jump_host_port.setValue(self.device.jump_server_port)
            if hasattr(self.device, 'jump_username'):
                self.jump_host_username.setText(self.device.jump_username)
            elif hasattr(self.device, 'jump_server_username'):
                self.jump_host_username.setText(self.device.jump_server_username)
            if hasattr(self.device, 'jump_password'):
                self.jump_host_password.setText(self.device.jump_password)
            elif hasattr(self.device, 'jump_server_password'):
                self.jump_host_password.setText(self.device.jump_server_password)
            
            # Set jump connection type
            if hasattr(self.device, 'jump_connection_type'):
                idx = self.jump_host_protocol_combo.findData(self.device.jump_connection_type)
                if idx >= 0:
                    self.jump_host_protocol_combo.setCurrentIndex(idx)
            
            # Set device protocol based on connection type
            from pulsarnet.device_management.connection_types import DeviceConnectionType
            if self.device.connection_type in [DeviceConnectionType.JUMP_SSH_DEVICE_SSH, DeviceConnectionType.JUMP_TELNET_DEVICE_SSH]:
                self.device_protocol_combo.setCurrentText("SSH")
            elif self.device.connection_type in [DeviceConnectionType.JUMP_SSH_DEVICE_TELNET, DeviceConnectionType.JUMP_TELNET_DEVICE_TELNET]:
                self.device_protocol_combo.setCurrentText("Telnet")
        else:
            # Determine if SSH or Telnet from connection_type
            if hasattr(self.device, 'connection_type'):
                conn_type = self.device.connection_type
                if hasattr(conn_type, 'value'):
                    conn_value = conn_type.value
                else:
                    conn_value = str(conn_type)
                if 'telnet' in conn_value.lower():
                    self.connection_type_combo.setCurrentText(ConnectionType.TELNET)
                else:
                    self.connection_type_combo.setCurrentText(ConnectionType.SSH)
        
        # Authentication
        if hasattr(self.device, 'username'):
            self.username_edit.setText(self.device.username)
        if hasattr(self.device, 'password'):
            self.password_edit.setText(self.device.password)
        if hasattr(self.device, 'enable_password'):
            self.enable_password_edit.setText(self.device.enable_password)
        
        # Port
        if hasattr(self.device, 'port'):
            self.port_spin.setValue(self.device.port)
        
        # SSH Keys
        if hasattr(self.device, 'use_keys'):
            self.use_keys_checkbox.setChecked(self.device.use_keys)
        if hasattr(self.device, 'key_file'):
            self.key_file_edit.setText(self.device.key_file)
        
        # Custom commands
        if hasattr(self.device, 'custom_settings') and isinstance(self.device.custom_settings, dict):
            if 'commands' in self.device.custom_settings:
                self.custom_commands_edit.setText(self.device.custom_settings['commands'])
        
        # Timeout and retry settings
        if hasattr(self.device, 'timeout'):
            self.timeout_spin.setValue(self.device.timeout)
        if hasattr(self.device, 'retry_count'):
            self.retry_count_spin.setValue(self.device.retry_count)
        if hasattr(self.device, 'retry_delay'):
            self.retry_delay_spin.setValue(self.device.retry_delay)
        
        # Check device groups
        if self.device_manager and hasattr(self.device, 'groups'):
            for i in range(self.groups_list.count()):
                item = self.groups_list.item(i)
                if item.text() in self.device.groups:
                    item.setCheckState(Qt.CheckState.Checked)

        # Optionally call on_connection_type_changed to update visibility
        self.on_connection_type_changed(self.connection_type_combo.currentText())

    def on_device_type_changed(self, device_type: str):
        """Update UI based on selected device type."""
        # Show/hide device-specific settings
        is_cisco = device_type.startswith('cisco_')
        self.enable_password_edit.setEnabled(is_cisco)
        
        # Update custom settings label based on device type
        if device_type.startswith('cisco_'):
            self.custom_settings_label.setText("Cisco Custom Commands:")
        elif device_type.startswith('juniper'):
            self.custom_settings_label.setText("Juniper Custom Commands:")
        elif device_type.startswith('arista'):
            self.custom_settings_label.setText("Arista Custom Commands:")
        else:
            self.custom_settings_label.setText("Custom Commands:")

    def validate_and_accept(self):
        """Validate input fields and accept dialog."""
        # Basic validation
        if not self.name_edit.text().strip():
            QMessageBox.warning(self, "Validation Error", "Device name is required.")
            return
            
        if not self.ip_edit.text().strip():
            QMessageBox.warning(self, "Validation Error", "IP address is required.")
            return
            
        if not self.username_edit.text().strip():
            QMessageBox.warning(self, "Validation Error", "Username is required.")
            return
            
        # Only require password if not using SSH keys
        if not self.use_keys_checkbox.isChecked() and not self.password_edit.text():
            QMessageBox.warning(self, "Validation Error", "Password is required unless using SSH keys.")
            return
            
        # If using SSH keys, validate key file exists
        if self.use_keys_checkbox.isChecked() and self.key_file_edit.text():
            import os
            if not os.path.exists(self.key_file_edit.text()):
                QMessageBox.warning(self, "Validation Error", "SSH key file does not exist.")
                return
        
        # Jump host validation if applicable
        if self.connection_type_combo.currentText() == ConnectionType.JUMP_HOST:
            if not self.jump_host_ip.text().strip():
                QMessageBox.warning(self, "Validation Error", "Jump host IP is required.")
                return
                
            if not self.jump_host_username.text().strip():
                QMessageBox.warning(self, "Validation Error", "Jump host username is required.")
                return
                
            if not self.jump_host_password.text():
                QMessageBox.warning(self, "Validation Error", "Jump host password is required.")
                return
        
        # Convert connection type string from the combo box to proper enum
        from pulsarnet.device_management.connection_types import DeviceConnectionType
        connection_type_str = self.connection_type_combo.currentText().strip()
        if connection_type_str in ["Direct SSH", "SSH"]:
            connection_type = DeviceConnectionType.DIRECT_SSH
        elif connection_type_str in ["Direct Telnet", "Telnet"]:
            connection_type = DeviceConnectionType.DIRECT_TELNET
        elif connection_type_str in ["Jump Host", "Via Jump Host"]:
            # Use jump host and device protocol combo boxes
            jump_host_protocol = self.jump_host_protocol_combo.currentText().strip()
            device_protocol = self.device_protocol_combo.currentText().strip()
            if jump_host_protocol in ["SSH", "Direct SSH"] and device_protocol in ["SSH", "Direct SSH"]:
                connection_type = DeviceConnectionType.JUMP_SSH_DEVICE_SSH
            elif jump_host_protocol in ["SSH", "Direct SSH"] and device_protocol in ["Telnet", "Direct Telnet"]:
                connection_type = DeviceConnectionType.JUMP_SSH_DEVICE_TELNET
            elif jump_host_protocol in ["Telnet", "Direct Telnet"] and device_protocol in ["SSH", "Direct SSH"]:
                connection_type = DeviceConnectionType.JUMP_TELNET_DEVICE_SSH
            elif jump_host_protocol in ["Telnet", "Direct Telnet"] and device_protocol in ["Telnet", "Direct Telnet"]:
                connection_type = DeviceConnectionType.JUMP_TELNET_DEVICE_TELNET
            else:
                raise ValueError("Invalid combination of jump host and device protocols")
        else:
            raise ValueError(f"Invalid device connection type: {connection_type_str}")
        
        # Determine if jump server is used based on connection type
        use_jump_server = connection_type in [
            DeviceConnectionType.JUMP_SSH_DEVICE_SSH,
            DeviceConnectionType.JUMP_SSH_DEVICE_TELNET,
            DeviceConnectionType.JUMP_TELNET_DEVICE_SSH,
            DeviceConnectionType.JUMP_TELNET_DEVICE_TELNET
        ]
        
        # Create the device with proper parameters (assuming the existence of UI elements: name_edit, ip_address_edit, username_edit, etc.)
        device = Device(
            name=self.name_edit.text().strip(),
            ip_address=self.ip_edit.text().strip(),
            device_type=DeviceType(self.type_combo.currentText().strip()),
            username=self.username_edit.text().strip(),
            password=self.password_edit.text(),
            enable_password=self.enable_password_edit.text(),
            port=int(self.port_spin.value()),
            connection_type=connection_type,
            use_jump_server=use_jump_server,
            jump_server=self.jump_host_ip.text().strip(),
            jump_host_name=self.jump_host_name.text().strip(),
            jump_username=self.jump_host_username.text().strip(),
            jump_password=self.jump_host_password.text().strip(),
            jump_protocol=self.jump_host_protocol_combo.currentText().strip().lower(),
            jump_port=int(self.jump_host_port.value())
        )
        
        # Set timeout and retry parameters
        device.timeout = self.timeout_spin.value()
        device.retry_count = self.retry_count_spin.value()
        device.retry_delay = self.retry_delay_spin.value()
        
        # Set SSH keys if applicable
        if self.use_keys_checkbox.isChecked():
            device.use_keys = True
            device.key_file = self.key_file_edit.text()
        
        # Set device type
        device.device_type = DeviceType(self.type_combo.currentText())
        
        # Set groups
        device.groups = [item.text() for i in range(self.groups_list.count()) if self.groups_list.item(i).checkState() == Qt.CheckState.Checked]
        
        # All validation passed, accept the dialog
        self.device = device
        self.accept()

    def show_create_group_dialog(self):
        """Show dialog to create a new device group."""
        from .group_dialog import GroupDialog
        
        dialog = GroupDialog(self)
        if dialog.exec():
            group_name = dialog.get_group_name()
            if self.device_manager and group_name:
                from ..device_management import DeviceGroup
                new_group = DeviceGroup(name=group_name, description=dialog.get_group_description())
                self.device_manager.add_group(new_group)
                
                # Add to the list widget
                item = QListWidgetItem(group_name)
                item.setFlags(item.flags() | Qt.ItemFlag.ItemIsUserCheckable)
                item.setCheckState(Qt.CheckState.Checked)  # Check by default
                self.groups_list.addItem(item)

    def select_all_groups(self):
        """Select all groups in the list."""
        for i in range(self.groups_list.count()):
            self.groups_list.item(i).setCheckState(Qt.CheckState.Checked)

    def clear_group_selection(self):
        """Clear all group selections."""
        for i in range(self.groups_list.count()):
            self.groups_list.item(i).setCheckState(Qt.CheckState.Unchecked)

    async def test_connection(self):
        """Test connection to the device."""
        from PyQt6.QtCore import QCoreApplication
        
        # Get device data
        device_data = self.get_device_data()
        
        # Create temporary device for testing
        if self.device_manager:
            temp_device = Device(
                name=device_data.get('name', 'temp_test_device'),
                ip_address=device_data.get('ip_address', ''),
                device_type=DeviceType(device_data.get('device_type', 'cisco_ios')),
                username=device_data.get('username', ''),
                password=device_data.get('password', ''),
                enable_password=device_data.get('enable_password', ''),
                port=device_data.get('port', 22)
            )
            
            # Set jump host if applicable
            if device_data.get('connection_type') == ConnectionType.JUMP_HOST:
                temp_device.jump_host = {
                    'ip': device_data.get('jump_server', ''),
                    'port': device_data.get('jump_port', 22),
                    'username': device_data.get('jump_username', ''),
                    'password': device_data.get('jump_password', '')
                }
            
            # Set SSH key settings if applicable
            if device_data.get('use_keys', False):
                temp_device.use_keys = True
                temp_device.key_file = device_data.get('key_file', '')
            
            # Set timeout
            temp_device.timeout = device_data.get('timeout', 30)
            
            # Display testing message
            QMessageBox.information(self, "Testing Connection", 
                                   f"Testing connection to {temp_device.ip_address}...\n"
                                   f"This may take up to {temp_device.timeout} seconds.")
            
            # Process events to update UI
            QCoreApplication.processEvents()
            
            # Test connection
            success, message = await self.device_manager.test_device_connection(temp_device)
            
            if success:
                QMessageBox.information(self, "Connection Test", 
                                      "Connection successful!")
            else:
                QMessageBox.warning(self, "Connection Test", 
                                   f"Connection failed:\n{message}")
        else:
            QMessageBox.warning(self, "Error", "Device manager not available for testing.")

    def get_device_data(self) -> dict:
        """Get device data from form fields."""
        data = {
            'name': self.name_edit.text().strip(),
            'ip_address': self.ip_edit.text().strip(),
            'device_type': self.type_combo.currentText(),
            'username': self.username_edit.text().strip(),
            'password': self.password_edit.text(),
            'enable_password': self.enable_password_edit.text(),
            'port': self.port_spin.value(),
            'connection_type': self.connection_type_combo.currentText(),
            'timeout': self.timeout_spin.value(),
            'retry_count': self.retry_count_spin.value(),
            'retry_delay': self.retry_delay_spin.value(),
            'use_keys': self.use_keys_checkbox.isChecked(),
            'key_file': self.key_file_edit.text() if self.use_keys_checkbox.isChecked() else '',
            'custom_commands': self.custom_commands_edit.text().strip()
        }
        
        # Add jump host settings if applicable
        if data['connection_type'] == ConnectionType.JUMP_HOST:
            data.update({
                'jump_host_name': self.jump_host_name.text().strip(),
                'jump_server': self.jump_host_ip.text().strip(),
                'jump_port': self.jump_host_port.value(),
                'jump_username': self.jump_host_username.text().strip(),
                'jump_password': self.jump_host_password.text(),
                'jump_connection_type': self.jump_host_protocol_combo.currentData()
            })
            
        # Get selected groups
        data['groups'] = []
        for i in range(self.groups_list.count()):
            item = self.groups_list.item(i)
            if item.checkState() == Qt.CheckState.Checked:
                data['groups'].append(item.text())
        
        return data