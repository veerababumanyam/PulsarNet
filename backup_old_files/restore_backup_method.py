"""
Fix issues with backup functionality in main_window.py by:
1. Adding back the start_backup_filtered method that was accidentally removed
2. Initializing backup components properly
"""

import re

filepath = r"c:\Users\admin\Desktop\PulsarNet\pulsarnet\gui\main_window.py"

with open(filepath, 'r') as f:
    content = f.read()

# Add initialization of backup components in __init__
init_pattern = r"def __init__\(self, parent=None\):\n        \"\"\"Initialize the main window.\"\"\"\n        super\(\).__init__\(parent\)\n        \n        self.setWindowTitle\('PulsarNet Network Management Suite'\)\n        self.resize\(1200, 800\)  # Set initial size"
init_replacement = """def __init__(self, parent=None):
        \"\"\"Initialize the main window.\"\"\"
        super().__init__(parent)
        
        self.setWindowTitle('PulsarNet Network Management Suite')
        self.resize(1200, 800)  # Set initial size
        
        # Initialize backup filter components to None
        self.backup_group_combo = None
        self.backup_device_type_combo = None
        self.backup_status_label = None
        self.backup_filter_combo = None
        self.backup_table = None"""

content = re.sub(init_pattern, init_replacement, content)

# Add back the start_backup_filtered method at the end of the file
start_backup_method = """
    def start_backup_filtered(self):
        \"\"\"Start backup based on the current table and filter settings.\"\"\"
        # Check if backup UI components are initialized
        if not hasattr(self, 'backup_table') or not hasattr(self, 'backup_status_label'):
            logging.error("Backup UI components not initialized")
            return
            
        try:
            self.backup_status_label.setText("Starting backup...")
            self.backup_status_label.setStyleSheet("color: blue;")
            
            # Get all checked devices from the backup table
            devices = []
            for row in range(self.backup_table.rowCount()):
                checkbox_item = self.backup_table.item(row, 0)
                if checkbox_item and checkbox_item.checkState() == Qt.CheckState.Checked:
                    device_name = self.backup_table.item(row, 1).text()
                    if device_name in self.device_manager.devices:
                        devices.append(self.device_manager.devices[device_name])
            
            # Check if any devices are selected
            if not devices:
                # If no devices are checked, show a confirmation dialog
                response = QMessageBox.question(
                    self,
                    "No Devices Selected",
                    "No devices are checked for backup. Do you want to backup all devices currently shown in the table?",
                    QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                    QMessageBox.StandardButton.No
                )
                
                if response == QMessageBox.StandardButton.Yes:
                    # Get all devices currently shown in the table
                    for row in range(self.backup_table.rowCount()):
                        device_name = self.backup_table.item(row, 1).text()
                        if device_name in self.device_manager.devices:
                            devices.append(self.device_manager.devices[device_name])
                else:
                    self.backup_status_label.setText("Backup cancelled - no devices selected")
                    self.backup_status_label.setStyleSheet("color: orange;")
                    return
            
            if not devices:
                self.backup_status_label.setText("No valid devices found for backup")
                self.backup_status_label.setStyleSheet("color: red;")
                return
                
            # Show a confirmation dialog with device count
            response = QMessageBox.question(
                self,
                "Confirm Backup",
                f"Do you want to backup {len(devices)} device(s)?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.Yes
            )
            
            if response == QMessageBox.StandardButton.Yes:
                self.backup_status_label.setText(f"Backing up {len(devices)} device(s)...")
                self.start_backup(devices)
            else:
                self.backup_status_label.setText("Backup cancelled by user")
                self.backup_status_label.setStyleSheet("color: orange;")
                
        except Exception as e:
            logging.error(f"Error starting backup: {str(e)}")
            self.backup_status_label.setText(f"Error: {str(e)}")
            self.backup_status_label.setStyleSheet("color: red;")
            QMessageBox.critical(self, "Backup Error", f"An error occurred while starting the backup:\\n{str(e)}")
"""

content = content + start_backup_method

# Write the fixed content back
with open(filepath, 'w') as f:
    f.write(content)

print("Fixed backup functionality in main_window.py by restoring the start_backup_filtered method")
