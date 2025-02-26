"""Storage Tab View for PulsarNet GUI.

This module provides the view components for the storage configuration tab.
"""

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QFormLayout, 
    QLineEdit, QPushButton, QComboBox, QSpinBox, 
    QGroupBox, QFileDialog
)
from .base_view import BaseTabView

class StorageTabView(BaseTabView):
    """View class for the storage configuration tab."""
    
    def setup_ui(self):
        """Set up the UI components for the storage tab."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(10)
        
        # Local storage settings
        local_group = QGroupBox("Local Backup Storage")
        local_layout = QFormLayout()
        
        self.local_path = QLineEdit()
        self.browse_btn = QPushButton("Browse...")
        
        path_layout = QHBoxLayout()
        path_layout.addWidget(self.local_path)
        path_layout.addWidget(self.browse_btn)
        
        local_layout.addRow("Backup Directory:", path_layout)
        local_group.setLayout(local_layout)
        layout.addWidget(local_group)
        
        # Remote storage settings
        remote_group = QGroupBox("Remote Backup Storage")
        remote_layout = QFormLayout()
        
        self.remote_type = QComboBox()
        self.remote_type.addItems(["None", "FTP", "SFTP", "SCP"])
        remote_layout.addRow("Remote Type:", self.remote_type)
        
        self.remote_host = QLineEdit()
        remote_layout.addRow("Remote Host:", self.remote_host)
        
        self.remote_port = QSpinBox()
        self.remote_port.setRange(1, 65535)
        self.remote_port.setValue(21)  # Default FTP port
        remote_layout.addRow("Remote Port:", self.remote_port)
        
        self.remote_user = QLineEdit()
        remote_layout.addRow("Username:", self.remote_user)
        
        self.remote_pass = QLineEdit()
        self.remote_pass.setEchoMode(QLineEdit.EchoMode.Password)
        remote_layout.addRow("Password:", self.remote_pass)
        
        self.remote_path = QLineEdit()
        remote_layout.addRow("Remote Path:", self.remote_path)
        
        # Test connection button
        self.test_btn = QPushButton("Test Connection")
        remote_layout.addRow("", self.test_btn)
        
        remote_group.setLayout(remote_layout)
        layout.addWidget(remote_group)
        
        # Save settings button
        self.save_btn = QPushButton("Save Settings")
        
        layout.addWidget(self.save_btn)
        layout.addStretch()
        
        self.setLayout(layout) 