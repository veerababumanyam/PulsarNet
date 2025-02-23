from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, 
    QLineEdit, QPushButton, QComboBox, QSpinBox,
    QFileDialog, QGroupBox, QFormLayout, QMessageBox
)
from PyQt6.QtCore import Qt
import os
import json

class SettingsDialog(QDialog):
    """Dialog for configuring application settings."""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.settings_file = os.path.expanduser("~/.pulsarnet/settings.json")
        self.init_ui()
        self.load_settings()
    
    def init_ui(self):
        """Initialize the dialog UI."""
        self.setWindowTitle('Settings')
        layout = QVBoxLayout()
        
        # Storage Settings Group
        storage_group = QGroupBox("Backup Storage Settings")
        storage_layout = QFormLayout()
        
        # Local Storage
        self.local_path = QLineEdit()
        browse_btn = QPushButton("Browse...")
        browse_btn.clicked.connect(self.browse_local_path)
        local_layout = QHBoxLayout()
        local_layout.addWidget(self.local_path)
        local_layout.addWidget(browse_btn)
        storage_layout.addRow("Local Backup Path:", local_layout)
        
        # Remote Storage Type
        self.remote_type = QComboBox()
        self.remote_type.addItems(["None", "FTP", "SFTP", "TFTP"])
        self.remote_type.currentTextChanged.connect(self.toggle_remote_settings)
        storage_layout.addRow("Remote Storage:", self.remote_type)
        
        # Remote Settings
        self.remote_host = QLineEdit()
        self.remote_port = QSpinBox()
        self.remote_port.setRange(1, 65535)
        self.remote_port.setValue(21)
        self.remote_user = QLineEdit()
        self.remote_pass = QLineEdit()
        self.remote_pass.setEchoMode(QLineEdit.EchoMode.Password)
        self.remote_path = QLineEdit()
        
        storage_layout.addRow("Remote Host:", self.remote_host)
        storage_layout.addRow("Remote Port:", self.remote_port)
        storage_layout.addRow("Remote Username:", self.remote_user)
        storage_layout.addRow("Remote Password:", self.remote_pass)
        storage_layout.addRow("Remote Path:", self.remote_path)
        
        storage_group.setLayout(storage_layout)
        layout.addWidget(storage_group)
        
        # Retention Settings
        retention_group = QGroupBox("Retention Settings")
        retention_layout = QFormLayout()
        
        self.max_backups = QSpinBox()
        self.max_backups.setRange(1, 1000)
        self.max_backups.setValue(10)
        retention_layout.addRow("Maximum backups per device:", self.max_backups)
        
        retention_group.setLayout(retention_layout)
        layout.addWidget(retention_group)
        
        # Buttons
        btn_layout = QHBoxLayout()
        save_btn = QPushButton("Save")
        save_btn.clicked.connect(self.save_settings)
        cancel_btn = QPushButton("Cancel")
        cancel_btn.clicked.connect(self.reject)
        btn_layout.addWidget(save_btn)
        btn_layout.addWidget(cancel_btn)
        layout.addLayout(btn_layout)
        
        self.setLayout(layout)
        
    def browse_local_path(self):
        """Open file dialog to select local backup path."""
        path = QFileDialog.getExistingDirectory(
            self,
            "Select Backup Directory",
            os.path.expanduser("~")
        )
        if path:
            self.local_path.setText(path)
    
    def toggle_remote_settings(self, storage_type):
        """Enable/disable remote settings based on storage type."""
        enabled = storage_type != "None"
        self.remote_host.setEnabled(enabled)
        self.remote_port.setEnabled(enabled)
        self.remote_user.setEnabled(enabled)
        self.remote_pass.setEnabled(enabled)
        self.remote_path.setEnabled(enabled)
    
    def load_settings(self):
        """Load existing settings."""
        try:
            if os.path.exists(self.settings_file):
                with open(self.settings_file, 'r') as f:
                    settings = json.load(f)
                    
                self.local_path.setText(settings.get('local_path', ''))
                self.remote_type.setCurrentText(settings.get('remote_type', 'None'))
                self.remote_host.setText(settings.get('remote_host', ''))
                self.remote_port.setValue(settings.get('remote_port', 21))
                self.remote_user.setText(settings.get('remote_user', ''))
                self.remote_pass.setText(settings.get('remote_pass', ''))
                self.remote_path.setText(settings.get('remote_path', ''))
                self.max_backups.setValue(settings.get('max_backups', 10))
        except Exception as e:
            QMessageBox.warning(self, "Error", f"Failed to load settings: {str(e)}")
    
    def save_settings(self):
        """Save settings to file."""
        try:
            settings = {
                'local_path': self.local_path.text(),
                'remote_type': self.remote_type.currentText(),
                'remote_host': self.remote_host.text(),
                'remote_port': self.remote_port.value(),
                'remote_user': self.remote_user.text(),
                'remote_pass': self.remote_pass.text(),
                'remote_path': self.remote_path.text(),
                'max_backups': self.max_backups.value()
            }
            
            os.makedirs(os.path.dirname(self.settings_file), exist_ok=True)
            with open(self.settings_file, 'w') as f:
                json.dump(settings, f, indent=4)
            
            self.accept()
            
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to save settings: {str(e)}")
