"""Storage Tab Controller for PulsarNet GUI.

This controller handles the logic for the storage configuration tab.
"""

from PyQt6.QtWidgets import QFileDialog, QMessageBox, QPushButton
from .base_controller import BaseController
import os
import json
import logging

class StorageTabController(BaseController):
    def connect_signals(self):
        # Connect browse button click
        self.view.browse_btn.clicked.connect(self.browse_local_path)
        
        # Connect save button click
        self.view.save_btn.clicked.connect(self.save_storage_settings)
        
        # Connect test button click if needed
        # self.view.test_btn.clicked.connect(self.test_remote_connection)

    def browse_local_path(self):
        directory = QFileDialog.getExistingDirectory(
            self.main_window, "Select Backup Directory", "",
            QFileDialog.Option.ShowDirsOnly
        )
        if directory:
            self.view.local_path.setText(directory)
            
    def save_storage_settings(self):
        try:
            settings = {
                'local_path': self.view.local_path.text(),
                'remote_type': self.view.remote_type.currentText(),
                'remote_host': self.view.remote_host.text(),
                'remote_port': self.view.remote_port.value(),
                'remote_username': self.view.remote_user.text(),
                'remote_password': self.view.remote_pass.text(),
                'remote_path': self.view.remote_path.text()
            }
            
            settings_file = os.path.expanduser("~/.pulsarnet/settings.json")
            os.makedirs(os.path.dirname(settings_file), exist_ok=True)
            
            with open(settings_file, 'w') as f:
                json.dump(settings, f, indent=4)
            
            # Optionally update storage status in main window
            self.main_window.storage_status.setText("Storage: OK")
            
            QMessageBox.information(self.main_window, 'Success', 'Storage settings saved successfully')
        except Exception as e:
            logging.error(f"Failed to save storage settings: {str(e)}")
            QMessageBox.critical(self.main_window, 'Error', f"Failed to save storage settings: {str(e)}") 