"""Backup Dialog Module for PulsarNet.

This module provides the UI components for configuring backup operations,
displaying progress, and managing backup protocols.
"""

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QComboBox,
    QProgressBar, QPushButton, QFormLayout, QLineEdit,
    QGroupBox, QSpinBox, QTextEdit, QStyle
)
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QFont, QPalette, QColor, QIcon
from typing import Dict, Optional
from pathlib import Path

from ..backup_operations import BackupManager, BackupJob
from ..backup_operations.backup_protocol import ProtocolType

class BackupDialog(QDialog):
    """Dialog for configuring and monitoring backup operations."""

    def __init__(self, backup_manager: BackupManager, parent=None):
        super().__init__(parent)
        self.backup_manager = backup_manager
        self.current_job: Optional[BackupJob] = None
        self.update_timer = QTimer(self)
        self.update_timer.timeout.connect(self.update_progress)
        
        self.setup_ui()

    def setup_ui(self):
        """Initialize the dialog's user interface."""
        self.setWindowTitle("Backup Configuration")
        self.setMinimumWidth(500)
        self.setup_style()

        layout = QVBoxLayout(self)
        layout.setContentsMargins(15, 15, 15, 15)
        layout.setSpacing(10)

    def setup_style(self):
        """Set up the dialog's visual style."""
        self.setFont(QFont('Segoe UI', 9))

        palette = QPalette()
        palette.setColor(QPalette.ColorRole.Window, QColor('#f0f0f0'))
        palette.setColor(QPalette.ColorRole.WindowText, QColor('#2c3e50'))
        palette.setColor(QPalette.ColorRole.Button, QColor('#3498db'))
        palette.setColor(QPalette.ColorRole.ButtonText, QColor('white'))
        self.setPalette(palette)

        # Protocol Configuration
        protocol_group = QGroupBox("Protocol Settings")
        protocol_group.setStyleSheet('QGroupBox { font-weight: bold; }')
        protocol_layout = QFormLayout()
        protocol_layout.setContentsMargins(10, 15, 10, 10)
        protocol_layout.setSpacing(8)

        self.protocol_combo = QComboBox()
        for protocol in ProtocolType:
            self.protocol_combo.addItem(protocol.value)
        protocol_layout.addRow("Protocol:", self.protocol_combo)

        self.server_edit = QLineEdit()
        protocol_layout.addRow("Server:", self.server_edit)

        self.port_spin = QSpinBox()
        self.port_spin.setRange(1, 65535)
        self.port_spin.setValue(69)  # Default TFTP port
        protocol_layout.addRow("Port:", self.port_spin)

        protocol_group.setLayout(protocol_layout)
        layout.addWidget(protocol_group)

        # Progress Section
        progress_group = QGroupBox("Backup Progress")
        progress_group.setStyleSheet('QGroupBox { font-weight: bold; }')
        progress_layout = QVBoxLayout()
        progress_layout.setContentsMargins(10, 15, 10, 10)
        progress_layout.setSpacing(8)

        self.status_label = QLabel("Ready")
        progress_layout.addWidget(self.status_label)

        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        progress_layout.addWidget(self.progress_bar)

        self.details_text = QTextEdit()
        self.details_text.setReadOnly(True)
        self.details_text.setMaximumHeight(100)
        progress_layout.addWidget(self.details_text)

        progress_group.setLayout(progress_layout)
        layout.addWidget(progress_group)

        # Buttons
        button_layout = QHBoxLayout()
        button_layout.setSpacing(10)

        self.start_button = QPushButton("Start Backup")
        self.start_button.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_MediaPlay))
        self.start_button.setMinimumWidth(120)
        self.start_button.clicked.connect(self.start_backup)
        button_layout.addWidget(self.start_button)

        self.close_button = QPushButton("Close")
        self.close_button.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_DialogCloseButton))
        self.close_button.setMinimumWidth(100)
        self.close_button.clicked.connect(self.close)
        button_layout.addWidget(self.close_button)

        layout.addLayout(button_layout)

    def get_protocol_config(self) -> Dict:
        """Get the current protocol configuration from the UI."""
        return {
            "server": self.server_edit.text(),
            "port": self.port_spin.value()
        }

    async def start_backup(self):
        """Start a backup operation with the current configuration."""
        self.start_button.setEnabled(False)
        self.protocol_combo.setEnabled(False)

        try:
            config = self.get_protocol_config()
            self.current_job = self.backup_manager.create_backup_job(
                "192.168.1.1",  # Example device IP
                self.protocol_combo.currentText(),
                config
            )

            self.update_timer.start(100)  # Update every 100ms
            await self.backup_manager.start_backup(self.current_job.job_id)

        except Exception as e:
            self.details_text.append(f"Error: {str(e)}")
            self.status_label.setText("Failed")
        finally:
            self.start_button.setEnabled(True)
            self.protocol_combo.setEnabled(True)
            self.update_timer.stop()

    def update_progress(self):
        """Update the progress display from the current backup job."""
        if not self.current_job:
            return

        job_status = self.backup_manager.get_job_status(self.current_job.job_id)
        if not job_status:
            return

        progress = job_status["progress"]
        self.status_label.setText(f"Status: {job_status['status']}")
        self.progress_bar.setValue(int(progress["percentage_complete"]))
        
        # Update details
        phase = progress["current_phase"]
        if phase != self.details_text.toPlainText().split('\n')[-1]:
            self.details_text.append(f"Phase: {phase}")

        if progress["error_message"]:
            self.details_text.append(f"Error: {progress['error_message']}")
            self.update_timer.stop()