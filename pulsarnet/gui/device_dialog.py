"""DeviceDialog class for adding and editing network devices in PulsarNet.

This module implements a dialog for device management operations following
ISO 9241-171:2008 accessibility standards.
"""

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QFormLayout, QLineEdit,
    QComboBox, QPushButton, QDialogButtonBox,
    QSpinBox, QCheckBox, QMessageBox, QGroupBox,
    QLabel, QListWidget, QListWidgetItem, QHBoxLayout
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont, QPalette, QColor

from ..device_management import Device, DeviceType, ConnectionStatus

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
        self.setMinimumWidth(450)

        # Create layouts
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(15, 15, 15, 15)
        main_layout.setSpacing(10)

        self.setup_style(main_layout)

        # Create group boxes for better organization
        basic_info_group = QGroupBox("Basic Information")
        basic_layout = QFormLayout()
        basic_info_group.setLayout(basic_layout)

        auth_info_group = QGroupBox("Authentication")
        auth_layout = QFormLayout()
        auth_info_group.setLayout(auth_layout)

        # Basic information fields
        self.name_edit = QLineEdit(self)
        self.name_edit.setPlaceholderText('Enter device name')
        self.name_edit.setMinimumWidth(250)
        basic_layout.addRow('Name:', self.name_edit)

        self.ip_edit = QLineEdit(self)
        self.ip_edit.setPlaceholderText('Enter IP address')
        basic_layout.addRow('IP Address:', self.ip_edit)

        self.type_combo = QComboBox(self)
        for device_type in DeviceType:
            self.type_combo.addItem(device_type.value.capitalize(), device_type)
        basic_layout.addRow('Device Type:', self.type_combo)

        self.port_spin = QSpinBox(self)
        self.port_spin.setRange(1, 65535)
        self.port_spin.setValue(22)
        basic_layout.addRow('Port:', self.port_spin)

        # Authentication fields
        self.username_edit = QLineEdit(self)
        self.username_edit.setPlaceholderText('Enter username')
        auth_layout.addRow('Username:', self.username_edit)

        self.password_edit = QLineEdit(self)
        self.password_edit.setPlaceholderText('Enter password')
        self.password_edit.setEchoMode(QLineEdit.EchoMode.Password)
        auth_layout.addRow('Password:', self.password_edit)

        self.enable_password_edit = QLineEdit(self)
        self.enable_password_edit.setPlaceholderText('Enter enable password (optional)')
        self.enable_password_edit.setEchoMode(QLineEdit.EchoMode.Password)
        auth_layout.addRow('Enable Password:', self.enable_password_edit)

        # Group selection
        group_box = QGroupBox("Group Assignment")
        group_layout = QVBoxLayout()
        group_box.setLayout(group_layout)

        # Group combobox with "Create New" option
        group_label = QLabel("Select Groups:")
        group_layout.addWidget(group_label)

        self.group_list = QListWidget()
        self.group_list.setSelectionMode(QListWidget.SelectionMode.MultiSelection)
        
        # Add all available groups
        if self.device_manager:
            for group in self.device_manager.groups.values():
                item = QListWidgetItem(group.name)
                self.group_list.addItem(item)
                # Pre-select if device is in group
                if self.device:
                    for device_group in self.device_manager.groups.values():
                        if self.device in device_group.devices and device_group.name == group.name:
                            item.setSelected(True)
        
        group_layout.addWidget(self.group_list)

        # Group management buttons
        group_button_layout = QHBoxLayout()
        
        create_group_btn = QPushButton("Create New Group")
        create_group_btn.clicked.connect(self.show_create_group_dialog)
        
        select_all_btn = QPushButton("Select All")
        select_all_btn.clicked.connect(self.select_all_groups)
        
        clear_all_btn = QPushButton("Clear Selection")
        clear_all_btn.clicked.connect(self.clear_group_selection)
        
        group_button_layout.addWidget(create_group_btn)
        group_button_layout.addWidget(select_all_btn)
        group_button_layout.addWidget(clear_all_btn)
        group_layout.addLayout(group_button_layout)

        # Add all sections to main layout
        main_layout.addWidget(basic_info_group)
        main_layout.addWidget(auth_info_group)
        main_layout.addWidget(group_box)

        # Dialog buttons
        button_box = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | 
            QDialogButtonBox.StandardButton.Cancel
        )
        button_box.accepted.connect(self.validate_and_accept)
        button_box.rejected.connect(self.reject)
        main_layout.addWidget(button_box)

        # Populate fields if editing existing device
        if self.device:
            self.populate_fields()

    def setup_style(self, layout):
        """Set up the dialog's visual style."""
        self.setFont(QFont('Segoe UI', 9))

        palette = QPalette()
        palette.setColor(QPalette.ColorRole.Window, QColor('#f0f0f0'))
        palette.setColor(QPalette.ColorRole.WindowText, QColor('#2c3e50'))
        palette.setColor(QPalette.ColorRole.Button, QColor('#3498db'))
        palette.setColor(QPalette.ColorRole.ButtonText, QColor('white'))
        self.setPalette(palette)

    def populate_fields(self):
        """Populate form fields with existing device data."""
        self.name_edit.setText(self.device.name)
        self.ip_edit.setText(self.device.ip_address)
        self.type_combo.setCurrentText(self.device.device_type.value.capitalize())
        self.username_edit.setText(self.device.username)
        self.port_spin.setValue(self.device.port)

    def validate_and_accept(self):
        """Validate form data before accepting."""
        try:
            # Basic validation
            if not all([self.name_edit.text(),
                       self.ip_edit.text(),
                       self.username_edit.text(),
                       self.password_edit.text()]):
                QMessageBox.warning(
                    self,
                    'Validation Error',
                    'Please fill in all required fields.'
                )
                return

            # IP address validation (basic)
            ip_parts = self.ip_edit.text().split('.')
            if len(ip_parts) != 4 or not all(p.isdigit() and 0 <= int(p) <= 255 for p in ip_parts):
                QMessageBox.warning(
                    self,
                    'Validation Error',
                    'Please enter a valid IP address.'
                )
                return

            # Create or update device object
            device_type = DeviceType(self.type_combo.currentText().lower())
            enable_pass = self.enable_password_edit.text() if self.enable_password_edit.text() else None
            
            if not self.device:
                self.device = Device(
                    name=self.name_edit.text(),
                    ip_address=self.ip_edit.text(),
                    device_type=device_type,
                    username=self.username_edit.text(),
                    password=self.password_edit.text(),
                    enable_password=enable_pass,
                    port=self.port_spin.value()
                )
            else:
                # Update existing device
                self.device.name = self.name_edit.text()
                self.device.ip_address = self.ip_edit.text()
                self.device.device_type = device_type
                self.device.username = self.username_edit.text()
                self.device._password = self.password_edit.text()
                self.device._enable_password = enable_pass
                self.device.port = self.port_spin.value()

            # Handle group assignments if device manager is available
            if self.device_manager:
                # Remove device from all groups first
                for group in self.device_manager.groups.values():
                    if self.device in group.devices:
                        group.remove_device(self.device)
                
                # Add to selected groups
                selected_items = self.group_list.selectedItems()
                for item in selected_items:
                    group_name = item.text()
                    if group_name in self.device_manager.groups:
                        self.device_manager.groups[group_name].add_device(self.device)

            # Initialize backup history with empty list
            self.device.backup_history = []
            self.device.last_backup_attempt = None
            self.device.backup_in_progress = False
            
            # Set initial connection status
            self.device.connection_status = ConnectionStatus.UNKNOWN
            self.device.is_connected = False
            self.device.last_seen = None
            self.device.last_connected = None

            self.accept()

        except Exception as e:
            QMessageBox.critical(
                self,
                'Device Creation Error',
                f'Failed to create device: {str(e)}'
            )

    def show_create_group_dialog(self):
        """Show dialog to create a new group."""
        from .group_dialog import GroupDialog
        dialog = GroupDialog(self, self.device_manager)
        if dialog.exec():
            new_group = dialog.get_group()
            if new_group:
                # Add to device manager
                self.device_manager.add_group(new_group)
                # Add to list and select it
                item = QListWidgetItem(new_group.name)
                self.group_list.addItem(item)
                item.setSelected(True)

    def select_all_groups(self):
        """Select all groups in the list."""
        for i in range(self.group_list.count()):
            self.group_list.item(i).setSelected(True)

    def clear_group_selection(self):
        """Clear all group selections."""
        for i in range(self.group_list.count()):
            self.group_list.item(i).setSelected(False)

    async def test_connection(self):
        """Test connection to the device."""
        # Create temporary device object
        device = Device(
            name=self.name_edit.text(),
            ip_address=self.ip_edit.text(),
            device_type=self.type_combo.currentData(),
            username=self.username_edit.text(),
            password=self.password_edit.text(),
            enable_password=self.enable_password_edit.text() or None,
            port=self.port_spin.value()
        )

        # Get device manager instance from parent window
        device_manager = self.parent().device_manager
        success, error = await device_manager.test_device_connection(device)

        if success:
            QMessageBox.information(
                self,
                'Connection Test',
                'Successfully connected to the device.'
            )
        else:
            QMessageBox.warning(
                self,
                'Connection Test',
                f'Failed to connect to the device:\n{error}'
            )

    def get_device_data(self) -> dict:
        """Return the form data as a dictionary."""
        return {
            'name': self.name_edit.text(),
            'ip_address': self.ip_edit.text(),
            'device_type': self.type_combo.currentData(),
            'username': self.username_edit.text(),
            'password': self.password_edit.text(),
            'enable_password': self.enable_password_edit.text() or None,
            'port': self.port_spin.value()
        }