"""GroupDialog class for managing device groups in PulsarNet."""

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel,
    QLineEdit, QPushButton, QListWidget,
    QMessageBox, QListWidgetItem, QComboBox
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont, QPalette, QColor

from ..device_management import DeviceGroup, Device

class GroupDialog(QDialog):
    """Dialog for creating and editing device groups."""

    def __init__(self, parent=None, device_manager=None, group: DeviceGroup = None):
        """Initialize the group dialog.
        
        Args:
            parent: Parent widget
            device_manager: DeviceManager instance for accessing devices
            group: Optional DeviceGroup to edit
        """
        super().__init__(parent)
        self.device_manager = device_manager
        self._group = group
        self.init_ui()

    def init_ui(self):
        """Initialize the user interface."""
        self.setWindowTitle('Create Group' if not self._group else 'Edit Group')
        self.setMinimumWidth(450)
        
        layout = QVBoxLayout()
        layout.setSpacing(10)
        layout.setContentsMargins(15, 15, 15, 15)
        
        # Group name
        name_layout = QHBoxLayout()
        name_label = QLabel('Group Name:')
        self.name_edit = QLineEdit()
        self.name_edit.setPlaceholderText('Enter group name')
        if self._group:
            self.name_edit.setText(self._group.name)
        name_layout.addWidget(name_label)
        name_layout.addWidget(self.name_edit)
        layout.addLayout(name_layout)

        # Description
        desc_label = QLabel('Description:')
        self.desc_edit = QLineEdit()
        self.desc_edit.setPlaceholderText('Enter group description (optional)')
        if self._group:
            self.desc_edit.setText(self._group.description or '')
        layout.addWidget(desc_label)
        layout.addWidget(self.desc_edit)
        
        # Device selection (if device manager is provided)
        if self.device_manager:
            # Available devices
            devices_label = QLabel('Available Devices:')
            layout.addWidget(devices_label)
            
            self.device_list = QListWidget()
            self.device_list.setSelectionMode(QListWidget.SelectionMode.MultiSelection)
            
            # Add all devices from device manager
            for device in self.device_manager.devices.values():
                item = QListWidgetItem(device.name)
                self.device_list.addItem(item)
                # Pre-select if device is in group
                if self._group and device in self._group.devices:
                    item.setSelected(True)
            
            layout.addWidget(self.device_list)
            
            # Add/Remove device buttons
            button_layout = QHBoxLayout()
            select_all_btn = QPushButton('Select All')
            select_all_btn.clicked.connect(self.select_all_devices)
            clear_all_btn = QPushButton('Clear Selection')
            clear_all_btn.clicked.connect(self.clear_device_selection)
            
            button_layout.addWidget(select_all_btn)
            button_layout.addWidget(clear_all_btn)
            layout.addLayout(button_layout)
        
        # Dialog buttons
        dialog_buttons = QHBoxLayout()
        
        self.save_btn = QPushButton('Save Group')
        self.save_btn.clicked.connect(self.validate_and_accept)
        
        cancel_btn = QPushButton('Cancel')
        cancel_btn.clicked.connect(self.reject)
        
        dialog_buttons.addWidget(self.save_btn)
        dialog_buttons.addWidget(cancel_btn)
        layout.addLayout(dialog_buttons)
        
        self.setLayout(layout)

    def select_all_devices(self):
        """Select all devices in the list."""
        for i in range(self.device_list.count()):
            self.device_list.item(i).setSelected(True)

    def clear_device_selection(self):
        """Clear all device selections."""
        for i in range(self.device_list.count()):
            self.device_list.item(i).setSelected(False)

    def validate_and_accept(self):
        """Validate the input and create/update the group."""
        try:
            # Validate group name
            group_name = self.name_edit.text().strip()
            if not group_name:
                self.show_error('Validation Error', 'Please enter a group name.')
                return

            # Create or update group
            if not self._group:
                self._group = DeviceGroup(
                    name=group_name,
                    description=self.desc_edit.text().strip() or None
                )
            else:
                self._group.name = group_name
                self._group.description = self.desc_edit.text().strip() or None
                self._group.devices.clear()  # Clear existing devices

            # Add selected devices if device manager is available
            if self.device_manager:
                selected_items = self.device_list.selectedItems()
                for item in selected_items:
                    device_name = item.text()
                    if device_name in self.device_manager.devices:
                        self._group.add_device(self.device_manager.devices[device_name])

            self.accept()

        except Exception as e:
            self.show_error('Group Creation Error', f'Failed to create group: {str(e)}')

    def show_error(self, title: str, message: str):
        """Show an error message with copy button."""
        msg_box = QMessageBox(self)
        msg_box.setIcon(QMessageBox.Icon.Critical)
        msg_box.setWindowTitle(title)
        msg_box.setText(message)
        
        # Add copy button
        copy_button = msg_box.addButton('Copy Error', QMessageBox.ButtonRole.ActionRole)
        copy_button.clicked.connect(lambda: self.copy_to_clipboard(f'{title}: {message}'))
        
        msg_box.addButton(QMessageBox.StandardButton.Ok)
        msg_box.exec()

    def copy_to_clipboard(self, text: str):
        """Copy text to clipboard."""
        from PyQt6.QtWidgets import QApplication
        QApplication.clipboard().setText(text)

    def get_group(self) -> DeviceGroup:
        """Return the created/edited group."""
        return self._group
