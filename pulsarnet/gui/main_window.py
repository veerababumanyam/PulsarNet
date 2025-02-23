"""MainWindow class for PulsarNet's graphical user interface.

This module implements the main application window following ISO 9241-171:2008
accessibility standards and provides a modern, user-friendly interface.
"""

from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QPushButton,
    QTableWidget, QTableWidgetItem, QMessageBox, QTabWidget,
    QLabel, QLineEdit, QComboBox, QProgressDialog, QFileDialog,
    QApplication, QMenuBar, QStatusBar, QToolBar, QCheckBox,
    QStyle, QSpinBox, QTimeEdit, QGroupBox, QFormLayout, QDialog,
    QDialogButtonBox, QHeaderView, QMenu, QTextBrowser
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal, QTimer, QSize
from PyQt6.QtGui import QAction, QFont, QPalette, QColor
import csv
import logging
import asyncio
from datetime import datetime
import threading
import os
import json
from ..scheduler import ScheduleManager, BackupSchedule, ScheduleType

# Import device management components
from ..device_management.device_manager import DeviceManager
from ..device_management.device import Device, DeviceType, ConnectionStatus
from ..device_management.device_group import DeviceGroup

# Import dialogs
from .device_dialog import DeviceDialog
from .group_dialog import GroupDialog
from .settings_dialog import SettingsDialog

class MainWindow(QMainWindow):
    """Main application window for PulsarNet."""

    def __init__(self):
        """Initialize the main window."""
        super().__init__()
        self.setWindowTitle('PulsarNet - Network Device Management')
        
        # Initialize managers
        self.device_manager = DeviceManager()
        self.schedule_manager = ScheduleManager()
        
        # Initialize event loop for async operations
        self.loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self.loop)
        
        # Initialize scheduler timer
        self.scheduler_timer = QTimer()
        self.scheduler_timer.timeout.connect(self.check_schedules)
        self.scheduler_timer.start(60000)  # Check every minute
        
        # Initialize UI
        self.init_ui()
        
        # Show backup location in status bar
        self.update_backup_location_status()
        
        # Load and display devices
        try:
            self.update_device_table()
            # Also update backup table since we have devices
            if hasattr(self, 'backup_table'):
                self.update_backup_table()
        except Exception as e:
            self.show_message_with_copy(
                'Load Error',
                f'Failed to load saved devices and groups: {str(e)}',
                QMessageBox.Icon.Critical
            )

    def init_ui(self):
        """Initialize the user interface following ISO 9241-171:2008."""
        # Get screen geometry
        screen = QApplication.primaryScreen().geometry()
        
        # Set minimum size following ISO standards for readability
        self.setMinimumSize(1024, 768)
        
        # Calculate window size (80% of screen height, maintaining min width)
        window_height = int(screen.height() * 0.8)
        window_height = max(window_height, 768)  # Ensure minimum height
        
        # Calculate window position to center it
        window_x = (screen.width() - 1024) // 2
        window_y = (screen.height() - window_height) // 2
        
        # Set window geometry
        self.setGeometry(window_x, window_y, 1024, window_height)
        self.setWindowTitle('PulsarNet - Network Device Backup Management')
        
        # Create central widget and layout
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        layout = QVBoxLayout(central_widget)
        
        # Create tab widget
        self.tab_widget = QTabWidget()
        layout.addWidget(self.tab_widget)
        
        # Create tabs
        self.create_device_tab(self.tab_widget)
        self.create_backup_tab(self.tab_widget)
        self.create_monitoring_tab(self.tab_widget)
        self.create_scheduler_tab(self.tab_widget)
        self.create_storage_tab(self.tab_widget)
        
        # Create menu bar
        self.create_menu_bar()
        
        # Create status bar
        self.statusBar = QStatusBar()
        self.setStatusBar(self.statusBar)
        
        # Show backup location in status bar
        self.update_backup_location_status()
        
        # Set up refresh timer for device status
        self.refresh_timer = QTimer()
        self.refresh_timer.timeout.connect(self.refresh_device_status)
        self.refresh_timer.start(30000)  # Refresh every 30 seconds

    def setup_style(self):
        """Set up the application's visual style."""
        # Keep existing style and just enhance it
        existing_style = self.styleSheet()
        
        # Add ISO-compliant styling while preserving existing
        enhanced_style = existing_style + """
            QPushButton {
                background-color: #007bff;
                color: white;
                padding: 6px 12px;
                border-radius: 4px;
                min-width: 80px;
            }
            QPushButton:hover {
                background-color: #0056b3;
            }
            QTableWidget {
                gridline-color: #dee2e6;
            }
            QHeaderView::section {
                background-color: #f8f9fa;
                padding: 6px;
            }
        """
        self.setStyleSheet(enhanced_style)

        # Set font
        app_font = QFont('Segoe UI', 9)
        self.setFont(app_font)

        # Create and set stylesheet for consistent styling
        self.setStyleSheet("""
            QMainWindow {
                background-color: #f0f0f0;
            }
            QMenuBar {
                background-color: #f8f9fa;
                color: black;
                border-bottom: 1px solid #dee2e6;
            }
            QMenuBar::item {
                background-color: transparent;
                padding: 5px 10px;
            }
            QMenuBar::item:selected {
                background-color: #e9ecef;
                color: black;
            }
            QMenu {
                background-color: #ffffff;
                color: black;
                border: 1px solid #dee2e6;
            }
            QMenu::item:selected {
                background-color: #e9ecef;
                color: black;
            }
            QPushButton {
                background-color: #007bff;
                color: white;
                border: none;
                padding: 5px 15px;
                border-radius: 4px;
            }
            QPushButton:hover {
                background-color: #e9ecef;
                color: black;
            }
            QPushButton:pressed {
                background-color: #0056b3;
                color: white;
            }
            QPushButton:disabled {
                background-color: #6c757d;
                color: #dee2e6;
            }
            QTableWidget {
                background-color: white;
                color: black;
                gridline-color: #dee2e6;
                selection-background-color: #e9ecef;
                selection-color: black;
            }
            QTableWidget::item {
                padding: 5px;
            }
            QTableWidget::item:selected {
                background-color: #e9ecef;
                color: black;
            }
            QHeaderView::section {
                background-color: #f8f9fa;
                color: black;
                padding: 5px;
                border: none;
                border-right: 1px solid #dee2e6;
                border-bottom: 1px solid #dee2e6;
            }
            QCheckBox {
                color: black;
            }
            QLabel {
                color: black;
            }
            QStatusBar {
                background-color: #f8f9fa;
                color: black;
            }
        """)

        # Set window palette for consistent colors
        palette = QPalette()
        palette.setColor(QPalette.ColorRole.Window, QColor('#f0f0f0'))
        palette.setColor(QPalette.ColorRole.WindowText, QColor('black'))
        palette.setColor(QPalette.ColorRole.Base, QColor('white'))
        palette.setColor(QPalette.ColorRole.AlternateBase, QColor('#f8f9fa'))
        palette.setColor(QPalette.ColorRole.Text, QColor('black'))
        palette.setColor(QPalette.ColorRole.Button, QColor('#007bff'))
        palette.setColor(QPalette.ColorRole.ButtonText, QColor('white'))
        palette.setColor(QPalette.ColorRole.Highlight, QColor('#e9ecef'))
        palette.setColor(QPalette.ColorRole.HighlightedText, QColor('black'))
        self.setPalette(palette)

    def create_toolbar(self):
        """Create the main application toolbar."""
        toolbar = QToolBar()
        toolbar.setMovable(False)
        toolbar.setIconSize(QSize(24, 24))
        self.addToolBar(toolbar)

        # Add device action
        add_device_action = QAction('Add Device', self)
        add_device_action.setStatusTip('Add a new network device')
        add_device_action.triggered.connect(self.show_add_device_dialog)
        toolbar.addAction(add_device_action)

        # Add group action
        add_group_action = QAction('Add Group', self)
        add_group_action.setStatusTip('Create a new device group')
        add_group_action.triggered.connect(self.show_add_group_dialog)
        toolbar.addAction(add_group_action)

        toolbar.addSeparator()

        # Refresh action
        refresh_action = QAction('Refresh', self)
        refresh_action.setStatusTip('Refresh device status')
        refresh_action.triggered.connect(self.refresh_device_status)
        toolbar.addAction(refresh_action)

    def create_device_tab(self, tab_widget):
        """Create the device management tab."""
        device_widget = QWidget()
        layout = QVBoxLayout(device_widget)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(10)

        # Device controls
        controls = QHBoxLayout()
        controls.setSpacing(8)  # ISO standard spacing

        # Left-aligned controls group
        left_controls = QHBoxLayout()
        left_controls.setSpacing(8)

        add_device_btn = QPushButton('Add Device')
        add_device_btn.setToolTip('Add a new network device')
        add_device_btn.clicked.connect(self.show_add_device_dialog)
        add_device_btn.setAccessibleName('Add Device Button')
        add_device_btn.setAccessibleDescription('Button to add a new network device')
        left_controls.addWidget(add_device_btn)

        add_group_btn = QPushButton('Add Group')
        add_group_btn.setToolTip('Create a new device group')
        add_group_btn.clicked.connect(self.show_add_group_dialog)
        add_group_btn.setAccessibleName('Add Group Button')
        add_group_btn.setAccessibleDescription('Button to create a new device group')
        left_controls.addWidget(add_group_btn)

        import_btn = QPushButton('Import')
        import_btn.setToolTip('Import devices from CSV file')
        import_btn.clicked.connect(self.import_devices)
        import_btn.setAccessibleName('Import Devices Button')
        import_btn.setAccessibleDescription('Button to import devices from CSV file')
        left_controls.addWidget(import_btn)

        test_conn_btn = QPushButton('Test Connection')
        test_conn_btn.setToolTip('Test connection to selected device')
        test_conn_btn.clicked.connect(self.test_selected_device_connection)
        test_conn_btn.setAccessibleName('Test Connection Button')
        test_conn_btn.setAccessibleDescription('Button to test connection to selected device')
        left_controls.addWidget(test_conn_btn)

        remove_device_btn = QPushButton('Remove Device')
        remove_device_btn.setToolTip('Remove selected devices')
        remove_device_btn.clicked.connect(self.remove_selected_device)
        remove_device_btn.setAccessibleName('Remove Device Button')
        remove_device_btn.setAccessibleDescription('Button to remove selected devices')
        left_controls.addWidget(remove_device_btn)

        controls.addLayout(left_controls)
        controls.addStretch()

        # Right-aligned controls group
        right_controls = QHBoxLayout()
        right_controls.setSpacing(8)

        upload_btn = QPushButton('Upload Config')
        upload_btn.setToolTip('Upload configuration to selected devices')
        upload_btn.clicked.connect(self.upload_config)
        upload_btn.setAccessibleName('Upload Config Button')
        upload_btn.setAccessibleDescription('Button to upload configuration to selected devices')
        right_controls.addWidget(upload_btn)

        refresh_btn = QPushButton('Refresh Status')
        refresh_btn.setToolTip('Refresh connection status of all devices')
        refresh_btn.clicked.connect(self.refresh_device_status)
        refresh_btn.setAccessibleName('Refresh Status Button')
        refresh_btn.setAccessibleDescription('Button to refresh connection status of all devices')
        right_controls.addWidget(refresh_btn)

        controls.addLayout(right_controls)
        layout.addLayout(controls)

        # Device table
        self.device_table = QTableWidget()
        self.device_table.setColumnCount(7)
        self.device_table.setHorizontalHeaderLabels([
            'Select', 'Name', 'IP Address', 'Type', 'Username', 'Port', 'Status'
        ])
        self.device_table.horizontalHeader().setStretchLastSection(True)
        self.device_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.device_table.setSelectionMode(QTableWidget.SelectionMode.SingleSelection)
        layout.addWidget(self.device_table)

        tab_widget.addTab(device_widget, 'Devices')

    def import_devices(self):
        """Import devices from CSV file."""
        try:
            # Show file dialog
            file_dialog = QFileDialog(self)
            file_dialog.setWindowTitle('Import Devices')
            file_dialog.setNameFilter('CSV files (*.csv)')
            file_dialog.setFileMode(QFileDialog.FileMode.ExistingFile)
            
            if file_dialog.exec():
                file_path = file_dialog.selectedFiles()[0]
                logging.info(f"Importing devices from: {file_path}")
                
                # Read CSV file
                with open(file_path, 'r') as f:
                    reader = csv.DictReader(f)
                    
                    # Validate headers
                    required_fields = ['name', 'ip_address', 'device_type', 'username', 'password']
                    missing_fields = [field for field in required_fields if field not in reader.fieldnames]
                    if missing_fields:
                        msg = f'Missing required fields in CSV: {", ".join(missing_fields)}'
                        logging.error(msg)
                        self.show_message_with_copy(
                            'Import Error',
                            msg,
                            QMessageBox.Icon.Critical
                        )
                        return
                    
                    # Import devices
                    success_count = 0
                    error_count = 0
                    errors = []
                    
                    # Get valid device types
                    valid_types = {t.value.lower(): t for t in DeviceType}
                    logging.info(f"Valid device types: {list(valid_types.keys())}")
                    
                    for row_num, row in enumerate(reader, start=1):
                        try:
                            # Skip empty rows
                            if not any(row.values()):
                                continue
                                
                            # Skip comment rows
                            if row['name'].startswith('#'):
                                continue
                            
                            # Log row being processed
                            logging.info(f"Processing row {row_num}: {row}")
                            
                            # Clean and validate device type
                            raw_type = row.get('device_type', '').strip()
                            if not raw_type:
                                raise ValueError("Device type is empty")
                            
                            device_type = raw_type.lower()
                            if device_type not in valid_types:
                                raise ValueError(
                                    f"Invalid device type '{raw_type}'. "
                                    f"Valid types are: {', '.join(sorted(valid_types.keys()))}"
                                )
                            
                            # Create device
                            device = Device(
                                name=row['name'].strip(),
                                ip_address=row['ip_address'].strip(),
                                device_type=valid_types[device_type],
                                username=row['username'].strip(),
                                password=row['password'].strip(),
                                enable_password=row.get('enable_password', '').strip() or None,
                                port=int(row.get('port', 22))
                            )
                            
                            # Add device
                            self.device_manager.devices[device.name] = device
                            success_count += 1
                            logging.info(f"Successfully imported device: {device.name}")
                            
                        except Exception as e:
                            error_count += 1
                            error_msg = f"Row {row_num}: {str(e)}"
                            errors.append(error_msg)
                            logging.error(error_msg)
                    
                    # Save devices
                    if success_count > 0:
                        self.device_manager.save_devices()
                        logging.info("Saved devices to disk")
                    
                    # Update table
                    self.update_device_table()
                    
                    # Show results
                    message = f"Successfully imported {success_count} devices."
                    if error_count > 0:
                        message += f"\n\nFailed to import {error_count} devices:\n"
                        message += "\n".join(errors)
                    
                    self.show_message_with_copy(
                        'Import Results',
                        message,
                        QMessageBox.Icon.Information
                    )
                    
        except Exception as e:
            error_msg = f'Failed to import devices: {str(e)}'
            logging.error(error_msg)
            self.show_message_with_copy(
                'Import Error',
                error_msg,
                QMessageBox.Icon.Critical
            )

    def update_device_table(self):
        """Update the device table with current devices."""
        try:
            # Update main device table
            self.device_table.setRowCount(len(self.device_manager.devices))
            for row, (name, device) in enumerate(sorted(self.device_manager.devices.items())):
                # Selection checkbox
                checkbox = QCheckBox()
                checkbox.setStyleSheet("QCheckBox { margin: 5px; }")  # Add some padding
                self.device_table.setCellWidget(row, 0, checkbox)
                
                # Device details with proper flags
                name_item = QTableWidgetItem(device.name)
                name_item.setFlags(Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsSelectable)
                self.device_table.setItem(row, 1, name_item)
                
                ip_item = QTableWidgetItem(device.ip_address)
                ip_item.setFlags(Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsSelectable)
                self.device_table.setItem(row, 2, ip_item)
                
                type_item = QTableWidgetItem(device.device_type.value)
                type_item.setFlags(Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsSelectable)
                self.device_table.setItem(row, 3, type_item)
                
                user_item = QTableWidgetItem(device.username)
                user_item.setFlags(Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsSelectable)
                self.device_table.setItem(row, 4, user_item)
                
                port_item = QTableWidgetItem(str(device.port))
                port_item.setFlags(Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsSelectable)
                self.device_table.setItem(row, 5, port_item)
                
                status_item = QTableWidgetItem(device.connection_status.value)
                status_item.setFlags(Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsSelectable)
                self.device_table.setItem(row, 6, status_item)
            
            # Update backup table if it exists
            if hasattr(self, 'backup_table'):
                self.update_backup_table()
                
        except Exception as e:
            error_msg = f"Error updating device table: {str(e)}"
            logging.error(error_msg)
            self.show_message_with_copy(
                'Update Error',
                error_msg,
                QMessageBox.Icon.Critical
            )

    def update_backup_table(self):
        """Update the backup table with current device information."""
        if not hasattr(self, 'backup_table'):
            return
            
        try:
            self.backup_table.setRowCount(len(self.device_manager.devices))
            
            for row, (name, device) in enumerate(sorted(self.device_manager.devices.items())):
                # Checkbox for selection
                checkbox = QCheckBox()
                checkbox.setStyleSheet("QCheckBox { margin: 5px; }")  # Add some padding
                self.backup_table.setCellWidget(row, 0, checkbox)
                
                # Device info
                self.backup_table.setItem(row, 1, QTableWidgetItem(name))
                self.backup_table.setItem(row, 2, QTableWidgetItem(device.ip_address))
                self.backup_table.setItem(row, 3, QTableWidgetItem(device.device_type.value))
                
                # Status with color coding
                status_text = device.connection_status.value
                if hasattr(device, 'backup_status') and device.backup_status:
                    status_text += f" - {device.backup_status}"
                status_item = QTableWidgetItem(status_text)
                
                if device.connection_status in [ConnectionStatus.BACKUP_SUCCESS]:
                    status_item.setForeground(QColor('green'))
                elif device.connection_status in [ConnectionStatus.ERROR, ConnectionStatus.BACKUP_FAILED, 
                                               ConnectionStatus.TIMEOUT, ConnectionStatus.AUTH_FAILED]:
                    status_item.setForeground(QColor('red'))
                self.backup_table.setItem(row, 4, status_item)
                
                # Last backup time
                last_backup = device.last_backup.strftime('%Y-%m-%d %H:%M:%S') if hasattr(device, 'last_backup') and device.last_backup else 'Never'
                if device.backup_history:
                    last_backup = device.backup_history[-1].timestamp.strftime('%Y-%m-%d %H:%M:%S')
                self.backup_table.setItem(row, 5, QTableWidgetItem(last_backup))
                
            # Adjust column widths
            self.backup_table.resizeColumnsToContents()
            
        except Exception as e:
            error_msg = f"Error updating backup table: {str(e)}"
            logging.error(error_msg)
            self.show_message_with_copy(
                'Update Error',
                error_msg,
                QMessageBox.Icon.Critical
            )

    def create_backup_tab(self, tab_widget):
        """Create the backup operations tab."""
        backup_widget = QWidget()
        layout = QVBoxLayout()
        
        # Create table
        self.backup_table = QTableWidget()
        self.backup_table.setColumnCount(6)
        self.backup_table.setHorizontalHeaderLabels([
            'Select', 'Name', 'IP Address', 'Device Type', 'Status', 'Last Backup'
        ])
        
        # Set column widths
        header = self.backup_table.horizontalHeader()
        header.setSectionResizeMode(0, header.ResizeMode.Fixed)  # Checkbox
        header.setSectionResizeMode(1, header.ResizeMode.Stretch)  # Name
        header.setSectionResizeMode(2, header.ResizeMode.Stretch)  # IP
        header.setSectionResizeMode(3, header.ResizeMode.Stretch)  # Type
        header.setSectionResizeMode(4, header.ResizeMode.Stretch)  # Status
        header.setSectionResizeMode(5, header.ResizeMode.Fixed)  # Last Backup
        
        self.backup_table.setColumnWidth(0, 50)  # Checkbox
        self.backup_table.setColumnWidth(5, 150)  # Last Backup
        
        # Update with current devices
        self.update_backup_table()
        
        # Add table to layout
        layout.addWidget(self.backup_table)
        
        # Create button controls
        button_layout = QHBoxLayout()
        
        backup_btn = QPushButton('Backup Selected')
        backup_btn.setToolTip('Backup configuration of selected devices')
        backup_btn.clicked.connect(self.start_backup)
        button_layout.addWidget(backup_btn)
        
        restore_btn = QPushButton('Restore Selected')
        restore_btn.setToolTip('Restore configuration to selected devices')
        restore_btn.clicked.connect(self.restore_selected_devices)
        button_layout.addWidget(restore_btn)
        
        layout.addLayout(button_layout)
        
        # Set layout
        backup_widget.setLayout(layout)
        tab_widget.addTab(backup_widget, 'Backup')

    def create_monitoring_tab(self, tab_widget):
        """Create the device monitoring tab."""
        monitoring_widget = QWidget()
        layout = QVBoxLayout()
        
        # Create monitoring table
        self.monitoring_table = QTableWidget()
        self.monitoring_table.setColumnCount(7)  # Added Error Message column
        self.monitoring_table.setHorizontalHeaderLabels([
            'Name', 'IP Address', 'Type', 'Status', 'Last Error', 'Uptime', 'Last Seen'
        ])
        
        # Set column widths
        header = self.monitoring_table.horizontalHeader()
        header.setSectionResizeMode(0, header.ResizeMode.Fixed)  # Name
        header.setSectionResizeMode(1, header.ResizeMode.Fixed)  # IP
        header.setSectionResizeMode(2, header.ResizeMode.Fixed)  # Type
        header.setSectionResizeMode(3, header.ResizeMode.Fixed)  # Status
        header.setSectionResizeMode(4, header.ResizeMode.Stretch)  # Last Error
        header.setSectionResizeMode(5, header.ResizeMode.Fixed)  # Uptime
        header.setSectionResizeMode(6, header.ResizeMode.Fixed)  # Last Seen
        
        self.monitoring_table.setColumnWidth(0, 150)  # Name
        self.monitoring_table.setColumnWidth(1, 150)  # IP
        self.monitoring_table.setColumnWidth(2, 150)  # Type
        self.monitoring_table.setColumnWidth(3, 100)  # Status
        self.monitoring_table.setColumnWidth(5, 120)  # Uptime
        self.monitoring_table.setColumnWidth(6, 150)  # Last Seen
        
        # Add refresh button
        btn_layout = QHBoxLayout()
        refresh_btn = QPushButton('Refresh Status')
        refresh_btn.clicked.connect(self.update_monitoring_table)
        btn_layout.addWidget(refresh_btn)
        
        # Add auto-refresh toggle
        self.auto_refresh = QCheckBox('Auto Refresh (every 60s)')
        self.auto_refresh.stateChanged.connect(self.toggle_auto_refresh)
        btn_layout.addWidget(self.auto_refresh)
        btn_layout.addStretch()
        
        # Add clear errors button
        clear_btn = QPushButton('Clear Errors')
        clear_btn.clicked.connect(self.clear_monitoring_errors)
        btn_layout.addWidget(clear_btn)
        
        # Add widgets to layout
        layout.addWidget(self.monitoring_table)
        layout.addLayout(btn_layout)
        
        monitoring_widget.setLayout(layout)
        tab_widget.addTab(monitoring_widget, 'Monitoring')
        
        # Initialize refresh timer
        self.refresh_timer = QTimer()
        self.refresh_timer.timeout.connect(self.update_monitoring_table)
        
        # Initial update
        self.update_monitoring_table()

    def toggle_auto_refresh(self, state):
        """Toggle automatic refresh of monitoring table."""
        if state == Qt.CheckState.Checked.value:
            self.refresh_timer.start(60000)  # Refresh every 60 seconds
            logging.info("Enabled auto-refresh for monitoring table")
        else:
            self.refresh_timer.stop()
            logging.info("Disabled auto-refresh for monitoring table")

    def update_monitoring_table(self):
        """Update the monitoring table with current device status."""
        try:
            self.monitoring_table.setRowCount(len(self.device_manager.devices))
            
            for row, (name, device) in enumerate(self.device_manager.devices.items()):
                # Device info
                self.monitoring_table.setItem(row, 0, QTableWidgetItem(device.name))
                self.monitoring_table.setItem(row, 1, QTableWidgetItem(device.ip_address))
                self.monitoring_table.setItem(row, 2, QTableWidgetItem(device.device_type.value))
                
                # Status with color coding
                status_item = QTableWidgetItem(device.connection_status.value)
                if device.connection_status == ConnectionStatus.CONNECTED:
                    status_item.setForeground(QColor('green'))
                elif device.connection_status in [ConnectionStatus.ERROR, ConnectionStatus.TIMEOUT]:
                    status_item.setForeground(QColor('red'))
                self.monitoring_table.setItem(row, 3, status_item)
                
                # Last error
                last_error = device.last_error if hasattr(device, 'last_error') else 'None'
                self.monitoring_table.setItem(row, 4, QTableWidgetItem(last_error))
                
                # Uptime
                uptime = device.uptime if hasattr(device, 'uptime') else 'N/A'
                self.monitoring_table.setItem(row, 5, QTableWidgetItem(str(uptime)))
                
                # Last seen
                last_seen = device.last_seen.strftime('%Y-%m-%d %H:%M:%S') if device.last_seen else 'Never'
                self.monitoring_table.setItem(row, 6, QTableWidgetItem(last_seen))
            
        except Exception as e:
            error_msg = f"Error updating monitoring table: {str(e)}"
            logging.error(error_msg)
            self.show_message_with_copy(
                'Update Error',
                error_msg,
                QMessageBox.Icon.Critical
            )

    def clear_monitoring_errors(self):
        """Clear error messages from monitoring table."""
        try:
            for device in self.device_manager.devices.values():
                device.last_error = None
            self.update_monitoring_table()
            
        except Exception as e:
            error_msg = f"Error clearing monitoring errors: {str(e)}"
            logging.error(error_msg)
            self.show_message_with_copy(
                'Error',
                error_msg,
                QMessageBox.Icon.Critical
            )

    def create_scheduler_tab(self, tab_widget):
        """Create the backup scheduler tab."""
        scheduler_widget = QWidget()
        layout = QVBoxLayout(scheduler_widget)

        # Create table
        self.scheduler_table = self.create_scheduler_table()
        layout.addWidget(self.scheduler_table)

        # Create button controls
        button_layout = QHBoxLayout()
        add_schedule_btn = QPushButton('Add Schedule')
        add_schedule_btn.setToolTip('Add a new backup schedule')
        add_schedule_btn.clicked.connect(self.show_add_schedule_dialog)
        button_layout.addWidget(add_schedule_btn)

        layout.addLayout(button_layout)

        # Set layout
        scheduler_widget.setLayout(layout)
        tab_widget.addTab(scheduler_widget, 'Scheduler')

    def create_scheduler_table(self):
        """Create the scheduler table widget."""
        table = QTableWidget()
        table.setColumnCount(7)
        table.setHorizontalHeaderLabels([
            'Name', 'Type', 'Time', 'Days', 'Devices', 'Last Run', 'Next Run'
        ])
        
        # Set column widths per ISO standards
        header = table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)  # Name
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)  # Type
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.Fixed)  # Time
        table.setColumnWidth(2, 80)
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)  # Days
        header.setSectionResizeMode(4, QHeaderView.ResizeMode.Stretch)  # Devices
        header.setSectionResizeMode(5, QHeaderView.ResizeMode.ResizeToContents)  # Last Run
        header.setSectionResizeMode(6, QHeaderView.ResizeMode.ResizeToContents)  # Next Run
        
        # Keep existing context menu functionality
        table.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        table.customContextMenuRequested.connect(self.show_scheduler_context_menu)
        
        self.update_scheduler_table(table)
        return table

    def update_scheduler_table(self, table=None):
        """Update the scheduler table with current schedules."""
        if table is None:
            table = self.scheduler_table
            
        table.setRowCount(len(self.schedule_manager.schedules))
        
        for row, (name, schedule) in enumerate(sorted(self.schedule_manager.schedules.items())):
            # Name
            name_item = QTableWidgetItem(name)
            table.setItem(row, 0, name_item)
            
            # Type
            type_item = QTableWidgetItem(schedule.schedule_type.value)
            table.setItem(row, 1, type_item)
            
            # Time
            time_item = QTableWidgetItem(schedule.time)
            table.setItem(row, 2, time_item)
            
            # Days
            if schedule.schedule_type == ScheduleType.WEEKLY:
                days = [['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'][d] for d in schedule.days]
                days_item = QTableWidgetItem(', '.join(days))
            else:
                days_item = QTableWidgetItem('Daily' if schedule.schedule_type == ScheduleType.DAILY else 'Custom')
            table.setItem(row, 3, days_item)
            
            # Devices
            devices_item = QTableWidgetItem(', '.join(schedule.devices))
            table.setItem(row, 4, devices_item)
            
            # Last Run
            last_run = schedule.last_run.strftime('%Y-%m-%d %H:%M') if schedule.last_run else 'Never'
            last_run_item = QTableWidgetItem(last_run)
            table.setItem(row, 5, last_run_item)
            
            # Next Run
            next_run = schedule.next_run.strftime('%Y-%m-%d %H:%M') if schedule.next_run else 'Not scheduled'
            next_run_item = QTableWidgetItem(next_run)
            table.setItem(row, 6, next_run_item)
            
        table.resizeColumnsToContents()

    def show_scheduler_context_menu(self, pos):
        """Show context menu for scheduler table."""
        menu = QMenu(self)
        
        add_action = menu.addAction("Add Schedule")
        add_action.triggered.connect(self.show_add_schedule_dialog)
        
        # Only enable edit/remove if row is selected
        selected_rows = self.scheduler_table.selectedIndexes()
        if selected_rows:
            edit_action = menu.addAction("Edit Schedule")
            edit_action.triggered.connect(self.show_edit_schedule_dialog)
            
            remove_action = menu.addAction("Remove Schedule")
            remove_action.triggered.connect(self.remove_selected_schedule)
            
        menu.exec(self.scheduler_table.mapToGlobal(pos))

    def show_add_schedule_dialog(self):
        """Show dialog to add a new schedule."""
        dialog = QDialog(self)
        dialog.setWindowTitle("Add Backup Schedule")
        layout = QFormLayout()
        
        # Name
        name_edit = QLineEdit()
        layout.addRow("Name:", name_edit)
        
        # Type
        type_combo = QComboBox()
        type_combo.addItems([t.value for t in ScheduleType])
        layout.addRow("Type:", type_combo)
        
        # Time
        time_edit = QTimeEdit()
        time_edit.setDisplayFormat("HH:mm")
        layout.addRow("Time:", time_edit)
        
        # Days (for weekly)
        days_group = QGroupBox("Days")
        days_layout = QVBoxLayout()
        day_checks = []
        for day in ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']:
            check = QCheckBox(day)
            day_checks.append(check)
            days_layout.addWidget(check)
        days_group.setLayout(days_layout)
        days_group.setVisible(False)
        layout.addRow(days_group)
        
        def on_type_changed(type_text):
            days_group.setVisible(type_text == ScheduleType.WEEKLY.value)
        type_combo.currentTextChanged.connect(on_type_changed)
        
        # Devices
        devices_group = QGroupBox("Devices")
        devices_layout = QVBoxLayout()
        device_checks = []
        for name in sorted(self.device_manager.devices.keys()):
            check = QCheckBox(name)
            device_checks.append(check)
            devices_layout.addWidget(check)
        devices_group.setLayout(devices_layout)
        layout.addRow(devices_group)
        
        # Buttons
        button_box = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | 
            QDialogButtonBox.StandardButton.Cancel
        )
        button_box.accepted.connect(dialog.accept)
        button_box.rejected.connect(dialog.reject)
        layout.addRow(button_box)
        
        dialog.setLayout(layout)
        
        if dialog.exec():
            try:
                # Get selected devices
                devices = [check.text() for check in device_checks if check.isChecked()]
                if not devices:
                    raise ValueError("Please select at least one device")
                
                # Get selected days for weekly schedule
                days = None
                if type_combo.currentText() == ScheduleType.WEEKLY.value:
                    days = [i for i, check in enumerate(day_checks) if check.isChecked()]
                    if not days:
                        raise ValueError("Please select at least one day for weekly schedule")
                
                schedule = BackupSchedule(
                    name=name_edit.text(),
                    schedule_type=ScheduleType(type_combo.currentText()),
                    devices=devices,
                    time=time_edit.time().toString("HH:mm"),
                    days=days
                )
                
                self.schedule_manager.add_schedule(schedule)
                self.update_scheduler_table()
                
            except Exception as e:
                self.show_message_with_copy(
                    "Error",
                    str(e),
                    QMessageBox.Icon.Critical
                )

    def show_edit_schedule_dialog(self):
        """Show dialog to edit selected schedule."""
        selected_rows = self.scheduler_table.selectedIndexes()
        if not selected_rows:
            return
            
        schedule_name = self.scheduler_table.item(selected_rows[0].row(), 0).text()
        schedule = self.schedule_manager.schedules.get(schedule_name)
        if not schedule:
            return
            
        dialog = QDialog(self)
        dialog.setWindowTitle("Edit Backup Schedule")
        layout = QFormLayout()
        
        # Name (read-only for existing schedules)
        name_edit = QLineEdit(schedule.name)
        name_edit.setReadOnly(True)
        layout.addRow("Name:", name_edit)
        
        # Type
        type_combo = QComboBox()
        type_combo.addItems([t.value for t in ScheduleType])
        type_combo.setCurrentText(schedule.schedule_type.value)
        layout.addRow("Type:", type_combo)
        
        # Time
        time_edit = QTimeEdit()
        time_edit.setDisplayFormat("HH:mm")
        time_edit.setTime(QTime.fromString(schedule.time, "HH:mm"))
        layout.addRow("Time:", time_edit)
        
        # Days (for weekly)
        days_group = QGroupBox("Days")
        days_layout = QVBoxLayout()
        day_checks = []
        for i, day in enumerate(['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']):
            check = QCheckBox(day)
            check.setChecked(i in (schedule.days or []))
            day_checks.append(check)
            days_layout.addWidget(check)
        days_group.setLayout(days_layout)
        days_group.setVisible(schedule.schedule_type == ScheduleType.WEEKLY)
        layout.addRow(days_group)
        
        def on_type_changed(type_text):
            days_group.setVisible(type_text == ScheduleType.WEEKLY.value)
        type_combo.currentTextChanged.connect(on_type_changed)
        
        # Devices
        devices_group = QGroupBox("Devices")
        devices_layout = QVBoxLayout()
        device_checks = []
        for name in sorted(self.device_manager.devices.keys()):
            check = QCheckBox(name)
            check.setChecked(name in schedule.devices)
            device_checks.append(check)
            devices_layout.addWidget(check)
        devices_group.setLayout(devices_layout)
        layout.addRow(devices_group)
        
        # Buttons
        button_box = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | 
            QDialogButtonBox.StandardButton.Cancel
        )
        button_box.accepted.connect(dialog.accept)
        button_box.rejected.connect(dialog.reject)
        layout.addRow(button_box)
        
        dialog.setLayout(layout)
        
        if dialog.exec():
            try:
                # Get selected devices
                devices = [check.text() for check in device_checks if check.isChecked()]
                if not devices:
                    raise ValueError("Please select at least one device")
                
                # Get selected days for weekly schedule
                days = None
                if type_combo.currentText() == ScheduleType.WEEKLY.value:
                    days = [i for i, check in enumerate(day_checks) if check.isChecked()]
                    if not days:
                        raise ValueError("Please select at least one day for weekly schedule")
                
                schedule = BackupSchedule(
                    name=name_edit.text(),
                    schedule_type=ScheduleType(type_combo.currentText()),
                    devices=devices,
                    time=time_edit.time().toString("HH:mm"),
                    days=days,
                    enabled=schedule.enabled,
                    last_run=schedule.last_run
                )
                
                self.schedule_manager.update_schedule(schedule)
                self.update_scheduler_table()
                
            except Exception as e:
                self.show_message_with_copy(
                    "Error",
                    str(e),
                    QMessageBox.Icon.Critical
                )

    def remove_selected_schedule(self):
        """Remove the selected schedule."""
        selected_rows = self.scheduler_table.selectedIndexes()
        if not selected_rows:
            return
            
        schedule_name = self.scheduler_table.item(selected_rows[0].row(), 0).text()
        
        reply = QMessageBox.question(
            self,
            'Confirm Removal',
            f'Are you sure you want to remove the schedule "{schedule_name}"?',
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            try:
                self.schedule_manager.remove_schedule(schedule_name)
                self.update_scheduler_table()
            except Exception as e:
                self.show_message_with_copy(
                    'Error',
                    f'Failed to remove schedule: {str(e)}',
                    QMessageBox.Icon.Critical
                )

    def check_schedules(self):
        """Check for and execute due schedules."""
        try:
            due_schedules = self.schedule_manager.get_due_schedules()
            for schedule in due_schedules:
                # Update last run time before starting backup
                self.schedule_manager.update_schedule_time(schedule.name)
                
                # Start backup for scheduled devices
                self.backup_devices(schedule.devices)
                
            if due_schedules:
                self.update_scheduler_table()
                
        except Exception as e:
            error_msg = f"Error checking schedules: {str(e)}"
            logging.error(error_msg)
            self.show_message_with_copy(
                'Error',
                error_msg,
                QMessageBox.Icon.Critical
            )

    def create_storage_tab(self, tab_widget):
        """Create the storage settings tab."""
        storage_widget = QWidget()
        storage_layout = QVBoxLayout()
        
        # Local Storage Group
        local_group = QGroupBox("Local Backup Storage")
        local_layout = QFormLayout()
        
        self.local_path = QLineEdit()
        browse_btn = QPushButton("Browse...")
        browse_btn.clicked.connect(self.browse_local_path)
        local_path_layout = QHBoxLayout()
        local_path_layout.addWidget(self.local_path)
        local_path_layout.addWidget(browse_btn)
        local_layout.addRow("Local Backup Path:", local_path_layout)
        
        local_group.setLayout(local_layout)
        storage_layout.addWidget(local_group)
        
        # Remote Storage Group
        remote_group = QGroupBox("Remote Storage")
        remote_layout = QFormLayout()
        
        self.remote_type = QComboBox()
        self.remote_type.addItems(["None", "FTP", "SFTP", "TFTP"])
        self.remote_type.currentTextChanged.connect(self.toggle_remote_settings)
        remote_layout.addRow("Storage Type:", self.remote_type)
        
        self.remote_host = QLineEdit()
        self.remote_port = QSpinBox()
        self.remote_port.setRange(1, 65535)
        self.remote_port.setValue(21)
        self.remote_user = QLineEdit()
        self.remote_pass = QLineEdit()
        self.remote_pass.setEchoMode(QLineEdit.EchoMode.Password)
        self.remote_path = QLineEdit()
        
        remote_layout.addRow("Host:", self.remote_host)
        remote_layout.addRow("Port:", self.remote_port)
        remote_layout.addRow("Username:", self.remote_user)
        remote_layout.addRow("Password:", self.remote_pass)
        remote_layout.addRow("Remote Path:", self.remote_path)
        
        remote_group.setLayout(remote_layout)
        storage_layout.addWidget(remote_group)
        
        # Retention Group
        retention_group = QGroupBox("Retention Policy")
        retention_layout = QFormLayout()
        
        self.max_backups = QSpinBox()
        self.max_backups.setRange(1, 1000)
        self.max_backups.setValue(10)
        retention_layout.addRow("Maximum backups per device:", self.max_backups)
        
        retention_group.setLayout(retention_layout)
        storage_layout.addWidget(retention_group)
        
        # Save Button
        save_btn = QPushButton("Save Storage Settings")
        save_btn.clicked.connect(self.save_storage_settings)
        storage_layout.addWidget(save_btn)
        
        storage_layout.addStretch()
        storage_widget.setLayout(storage_layout)
        tab_widget.addTab(storage_widget, 'Storage')

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

    def create_menu_bar(self):
        """Create the main menu bar following ISO standards."""
        menubar = self.menuBar()
        
        # File Menu - Basic application operations
        file_menu = menubar.addMenu('&File')
        
        # Device operations submenu
        device_menu = file_menu.addMenu('Device Operations')
        
        import_action = QAction('Import Devices', self)
        import_action.setStatusTip('Import devices from CSV file')
        import_action.setShortcut('Ctrl+I')
        import_action.triggered.connect(self.import_devices)
        device_menu.addAction(import_action)
        
        add_device_action = QAction('Add Device', self)
        add_device_action.setStatusTip('Add a new network device')
        add_device_action.setShortcut('Ctrl+N')
        add_device_action.triggered.connect(self.show_add_device_dialog)
        device_menu.addAction(add_device_action)
        
        add_group_action = QAction('Add Group', self)
        add_group_action.setStatusTip('Create a new device group')
        add_group_action.setShortcut('Ctrl+G')
        add_group_action.triggered.connect(self.show_add_group_dialog)
        device_menu.addAction(add_group_action)
        
        remove_device_action = QAction('Remove Device', self)
        remove_device_action.setStatusTip('Remove selected device')
        remove_device_action.setShortcut('Del')
        remove_device_action.triggered.connect(self.remove_selected_device)
        device_menu.addAction(remove_device_action)
        
        file_menu.addSeparator()
        
        exit_action = QAction('Exit', self)
        exit_action.setStatusTip('Exit application')
        exit_action.setShortcut('Alt+F4')
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)
        
        # Operations Menu - Core functionality
        operations_menu = menubar.addMenu('&Operations')
        
        backup_menu = operations_menu.addMenu('Backup')
        
        backup_selected_action = QAction('Backup Selected', self)
        backup_selected_action.setStatusTip('Backup configuration of selected devices')
        backup_selected_action.setShortcut('Ctrl+B')
        backup_selected_action.triggered.connect(self.backup_selected_devices)
        backup_menu.addAction(backup_selected_action)
        
        backup_all_action = QAction('Backup All', self)
        backup_all_action.setStatusTip('Backup configuration of all devices')
        backup_all_action.setShortcut('Ctrl+Shift+B')
        backup_all_action.triggered.connect(self.backup_all_devices)
        backup_menu.addAction(backup_all_action)
        
        operations_menu.addSeparator()
        
        test_connection_action = QAction('Test Connection', self)
        test_connection_action.setStatusTip('Test connection to selected device')
        test_connection_action.setShortcut('Ctrl+T')
        test_connection_action.triggered.connect(self.test_selected_device_connection)
        operations_menu.addAction(test_connection_action)
        
        # View Menu - Display options
        view_menu = menubar.addMenu('&View')
        
        refresh_action = QAction('Refresh', self)
        refresh_action.setStatusTip('Refresh device status')
        refresh_action.setShortcut('F5')
        refresh_action.triggered.connect(self.refresh_device_status)
        view_menu.addAction(refresh_action)
        
        # Tools Menu - Configuration and utilities
        tools_menu = menubar.addMenu('&Tools')
        
        scheduler_action = QAction('Scheduler', self)
        scheduler_action.setStatusTip('Configure backup schedules')
        scheduler_action.triggered.connect(self.show_scheduler)
        tools_menu.addAction(scheduler_action)
        
        storage_action = QAction('Storage Settings', self)
        storage_action.setStatusTip('Configure backup storage locations')
        storage_action.triggered.connect(self.show_storage_settings)
        tools_menu.addAction(storage_action)
        
        tools_menu.addSeparator()
        
        settings_action = QAction('Preferences', self)
        settings_action.setStatusTip('Configure application settings')
        settings_action.setShortcut('Ctrl+,')
        settings_action.triggered.connect(self.show_settings)
        tools_menu.addAction(settings_action)
        
        # Help Menu
        help_menu = menubar.addMenu('&Help')
        
        help_action = QAction('Help', self)
        help_action.setStatusTip('View help documentation')
        help_action.setShortcut('F1')
        help_action.triggered.connect(self.show_help)
        help_menu.addAction(help_action)
        
        help_menu.addSeparator()
        
        about_action = QAction('About', self)
        about_action.setStatusTip('About PulsarNet')
        about_action.triggered.connect(self.show_about)
        help_menu.addAction(about_action)

    def show_add_device_dialog(self):
        """Show dialog for adding a new device."""
        dialog = DeviceDialog(self, self.device_manager)
        if dialog.exec():
            device = dialog.device
            if device:
                self.device_manager.add_device(device)
                self.update_device_table()
                self.update_backup_table()

    def show_add_group_dialog(self):
        """Show dialog for creating a new device group."""
        dialog = GroupDialog(self, self.device_manager)
        if dialog.exec():
            group = dialog.get_group()
            if group:
                self.device_manager.add_group(group)
                self.update_device_table()
                self.update_backup_table()

    def show_edit_device_dialog(self, device: Device):
        """Show dialog for editing an existing device."""
        dialog = DeviceDialog(self, self.device_manager, device)
        if dialog.exec():
            self.device_manager.save_data()  # Save changes to disk
            self.update_device_table()
            self.update_backup_table()

    def show_edit_group_dialog(self, group: DeviceGroup):
        """Show dialog for editing an existing group."""
        dialog = GroupDialog(self, self.device_manager, group)
        if dialog.exec():
            self.device_manager.save_data()  # Save changes to disk
            self.update_device_table()
            self.update_backup_table()

    def remove_selected_device(self):
        """Remove the selected device."""
        try:
            selected_devices = self.get_selected_devices_from_device_table()
            if not selected_devices:
                self.show_message_with_copy(
                    'Selection Error',
                    'Please select at least one device to remove',
                    QMessageBox.Icon.Warning
                )
                return

            device_names = [d.name for d in selected_devices]
            devices_str = ", ".join(device_names)
            
            msg_box = QMessageBox(self)
            msg_box.setWindowTitle('Confirm Removal')
            msg_box.setText(f'Are you sure you want to remove these devices?\n{devices_str}')
            msg_box.setIcon(QMessageBox.Icon.Question)
            
            # Add copy button
            copy_button = msg_box.addButton(
                'Copy List',
                QMessageBox.ButtonRole.ActionRole
            )
            copy_button.clicked.connect(
                lambda: QApplication.clipboard().setText(devices_str)
            )
            
            # Add Yes/No buttons
            msg_box.addButton(QMessageBox.StandardButton.Yes)
            msg_box.addButton(QMessageBox.StandardButton.No)
            
            response = msg_box.exec()
            
            if response == QMessageBox.StandardButton.Yes:
                for device in selected_devices:
                    self.device_manager.remove_device(device.name)
                self.update_device_table()
                
        except Exception as e:
            error_msg = f"Error removing device: {str(e)}"
            logging.error(error_msg)
            self.show_message_with_copy(
                'Remove Error',
                error_msg,
                QMessageBox.Icon.Critical
            )

    def refresh_device_status(self):
        """Refresh the status of all devices."""
        # Implementation for refreshing device status
        pass

    def select_all_devices(self):
        """Select all devices in the backup table."""
        try:
            for row in range(self.backup_table.rowCount()):
                checkbox = self.backup_table.cellWidget(row, 0)
                if checkbox:
                    checkbox.setChecked(True)
        except Exception as e:
            self.show_message_with_copy(
                'Selection Error',
                f'Failed to select all devices: {str(e)}',
                QMessageBox.Icon.Warning
            )

    def deselect_all_devices(self):
        """Deselect all devices in the backup table."""
        try:
            for row in range(self.backup_table.rowCount()):
                checkbox = self.backup_table.cellWidget(row, 0)
                if checkbox:
                    checkbox.setChecked(False)
        except Exception as e:
            self.show_message_with_copy(
                'Selection Error',
                f'Failed to deselect all devices: {str(e)}',
                QMessageBox.Icon.Warning
            )

    def get_selected_devices(self):
        """Get list of selected devices for backup."""
        selected_devices = []
        try:
            for row in range(self.backup_table.rowCount()):
                checkbox = self.backup_table.cellWidget(row, 0)
                if checkbox and checkbox.isChecked():
                    device_name = self.backup_table.item(row, 1).text()
                    if device_name in self.device_manager.devices:
                        selected_devices.append(self.device_manager.devices[device_name])
        except Exception as e:
            self.show_message_with_copy(
                'Selection Error',
                f'Failed to get selected devices: {str(e)}',
                QMessageBox.Icon.Warning
            )
        return selected_devices

    def get_selected_devices_from_device_table(self):
        """Get list of selected devices from device table."""
        selected_devices = []
        try:
            for row in range(self.device_table.rowCount()):
                checkbox = self.device_table.cellWidget(row, 0)
                if checkbox and checkbox.isChecked():
                    device_name = self.device_table.item(row, 1).text()
                    if device_name in self.device_manager.devices:
                        selected_devices.append(self.device_manager.devices[device_name])
        except Exception as e:
            self.show_message_with_copy(
                'Selection Error',
                f'Failed to get selected devices: {str(e)}',
                QMessageBox.Icon.Warning
            )
        return selected_devices

    def start_backup(self):
        """Start the backup process."""
        try:
            # Get selected devices
            selected_devices = []
            for row in range(self.backup_table.rowCount()):
                checkbox = self.backup_table.item(row, 0)
                if checkbox and checkbox.checkState() == Qt.CheckState.Checked:
                    device_name = self.backup_table.item(row, 1).text()
                    if device_name in self.device_manager.devices:
                        selected_devices.append(self.device_manager.devices[device_name])
            
            if not selected_devices:
                self.show_message_with_copy(
                    'No Selection',
                    'Please select at least one device to backup',
                    QMessageBox.Icon.Warning
                )
                return
            
            # Run backup in event loop
            if not self.loop.is_running():
                # Start event loop if not running
                def run_loop():
                    asyncio.set_event_loop(self.loop)
                    self.loop.run_forever()
                
                self.loop_thread = threading.Thread(target=run_loop, daemon=True)
                self.loop_thread.start()
            
            # Schedule backup task
            future = asyncio.run_coroutine_threadsafe(
                self._backup_devices(selected_devices),
                self.loop
            )
            
            # Add callback to handle completion
            def backup_done(fut):
                try:
                    fut.result()
                except Exception as e:
                    logging.error(f"Backup failed: {str(e)}")
            
            future.add_done_callback(backup_done)
            
        except Exception as e:
            error_msg = f"Error starting backup: {str(e)}"
            logging.error(error_msg)
            self.show_message_with_copy(
                'Backup Error',
                error_msg,
                QMessageBox.Icon.Critical
            )

    def verify_backup(self):
        """Verify backup integrity for selected devices."""
        # Implementation for backup verification
        pass

    def add_schedule(self):
        """Show dialog for adding a new backup schedule."""
        # Implementation for adding schedule
        pass

    def show_settings(self):
        """Show the settings dialog."""
        dialog = SettingsDialog(self)
        if dialog.exec():
            self.update_backup_location_status()

    def show_about(self):
        """Show about dialog."""
        about_text = """
        <h2>PulsarNet - Network Device Management</h2>
        <p>Version 1.0.0</p>
        <p>A comprehensive solution for network device configuration management.</p>
        <p>Features:</p>
        <ul>
            <li>Device Management</li>
            <li>Automated Backups</li>
            <li>Multiple Storage Options</li>
            <li>Flexible Scheduling</li>
        </ul>
        <p>Author: Veera Babu Manyam<br>
        Email: veerababumanyam@gmail.com</p>
        <p>Licensed under Apache License 2.0</p>
        """
        QMessageBox.about(self, "About PulsarNet", about_text)

    def show_help(self):
        """Show help documentation in a dialog."""
        help_text = """
        <html>
        <head>
        <style>
            body { font-family: Arial, sans-serif; line-height: 1.6; }
            h1, h2, h3 { color: #2c3e50; }
            .section { margin-bottom: 20px; }
            .shortcut { 
                background-color: #f8f9fa;
                padding: 2px 5px;
                border-radius: 3px;
                font-family: monospace;
            }
        </style>
        </head>
        <body>
        <h1>PulsarNet - Network Device Management System</h1>
        
        <div class="section">
            <h2>1. Overview</h2>
            <p>PulsarNet is a comprehensive network device management system designed for efficient backup, monitoring, and configuration of network devices. The application follows ISO/IEC 9126 standards for software quality.</p>
        </div>

        <div class="section">
            <h2>2. Main Features</h2>
            
            <h3>2.1 Device Management</h3>
            <ul>
                <li>Add, edit, and remove network devices</li>
                <li>Group devices for organized management</li>
                <li>Import devices from CSV files</li>
                <li>Real-time device status monitoring</li>
            </ul>

            <h3>2.2 Backup Management</h3>
            <ul>
                <li>Manual and automated configuration backups</li>
                <li>Local and remote storage options (FTP, SFTP, TFTP)</li>
                <li>Flexible scheduling options (daily, weekly, custom)</li>
                <li>Retention policy management</li>
            </ul>
        </div>

        <div class="section">
            <h2>3. Keyboard Shortcuts</h2>
            <table style="border-collapse: collapse; width: 100%;">
                <tr style="background-color: #f5f5f5;">
                    <th style="border: 1px solid #ddd; padding: 8px; text-align: left;">Action</th>
                    <th style="border: 1px solid #ddd; padding: 8px; text-align: left;">Shortcut</th>
                </tr>
                <tr>
                    <td style="border: 1px solid #ddd; padding: 8px;">Import Devices</td>
                    <td style="border: 1px solid #ddd; padding: 8px;"><span class="shortcut">Ctrl+I</span></td>
                </tr>
                <tr>
                    <td style="border: 1px solid #ddd; padding: 8px;">Add Device</td>
                    <td style="border: 1px solid #ddd; padding: 8px;"><span class="shortcut">Ctrl+N</span></td>
                </tr>
                <tr>
                    <td style="border: 1px solid #ddd; padding: 8px;">Add Group</td>
                    <td style="border: 1px solid #ddd; padding: 8px;"><span class="shortcut">Ctrl+G</span></td>
                </tr>
                <tr>
                    <td style="border: 1px solid #ddd; padding: 8px;">Remove Device</td>
                    <td style="border: 1px solid #ddd; padding: 8px;"><span class="shortcut">Del</span></td>
                </tr>
                <tr>
                    <td style="border: 1px solid #ddd; padding: 8px;">Backup Selected</td>
                    <td style="border: 1px solid #ddd; padding: 8px;"><span class="shortcut">Ctrl+B</span></td>
                </tr>
                <tr>
                    <td style="border: 1px solid #ddd; padding: 8px;">Backup All</td>
                    <td style="border: 1px solid #ddd; padding: 8px;"><span class="shortcut">Ctrl+Shift+B</span></td>
                </tr>
                <tr>
                    <td style="border: 1px solid #ddd; padding: 8px;">Test Connection</td>
                    <td style="border: 1px solid #ddd; padding: 8px;"><span class="shortcut">Ctrl+T</span></td>
                </tr>
            </table>
        </div>
        </body>
        </html>
        """
        
        help_dialog = QDialog(self)
        help_dialog.setWindowTitle("PulsarNet Help")
        help_dialog.setMinimumSize(800, 600)
        
        layout = QVBoxLayout()
        
        help_text_browser = QTextBrowser()
        help_text_browser.setHtml(help_text)
        layout.addWidget(help_text_browser)
        
        button_box = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok)
        button_box.accepted.connect(help_dialog.accept)
        layout.addWidget(button_box)
        
        help_dialog.setLayout(layout)
        help_dialog.exec()

    def create_status_summary(self):
        """Create the status summary section."""
        # Implementation for status summary
        pass

    def create_log_viewer(self):
        """Create the log viewer section."""
        # Implementation for log viewer
        pass

    def create_device_toolbar(self):
        """Create the device management toolbar."""
        toolbar = QToolBar()
        toolbar.setMovable(False)
        toolbar.setIconSize(QSize(24, 24))
        
        # Add Device button
        add_device_action = QAction('Add Device', self)
        add_device_action.triggered.connect(self.show_add_device_dialog)
        toolbar.addAction(add_device_action)

        # Add Group button
        add_group_action = QAction('Add Group', self)
        add_group_action.triggered.connect(self.show_add_group_dialog)
        toolbar.addAction(add_group_action)

        # Test Connection button
        test_connection_action = QAction('Test Connection', self)
        test_connection_action.triggered.connect(self.test_selected_device_connection)
        toolbar.addAction(test_connection_action)
        
        toolbar.addSeparator()
        
        # Upload Config button
        upload_config_action = QAction('Upload Config', self)
        upload_config_action.triggered.connect(self.upload_config)
        toolbar.addAction(upload_config_action)
        
        # Refresh button
        refresh_action = QAction('Refresh', self)
        refresh_action.triggered.connect(self.refresh_device_status)
        toolbar.addAction(refresh_action)
        
        return toolbar

    def test_selected_device_connection(self):
        """Test connection for selected device."""
        try:
            # Get selected device
            selected_rows = self.device_table.selectionModel().selectedRows()
            if not selected_rows:
                self.show_message_with_copy(
                    'No Device Selected',
                    'Please select a device to test connection',
                    QMessageBox.Icon.Warning
                )
                return

            # Get device name from the name column (index 1)
            row = selected_rows[0].row()
            device_name = self.device_table.item(row, 1).text()
            
            # Debug log
            logging.info(f"Testing connection for device: {device_name}")
            logging.info(f"Available devices: {list(self.device_manager.devices.keys())}")
            
            device = self.device_manager.devices.get(device_name)
            if not device:
                self.show_message_with_copy(
                    'Device Not Found',
                    f'Device {device_name} not found in device manager',
                    QMessageBox.Icon.Critical
                )
                return

            # Create progress dialog
            progress = QProgressDialog(
                f'Testing connection to {device_name}...',
                'Cancel',
                0,
                0,
                self
            )
            progress.setWindowModality(Qt.WindowModality.WindowModal)
            progress.show()
            QApplication.processEvents()

            try:
                # Run test connection in event loop
                success, message = self.loop.run_until_complete(device.test_connection())
                
                # Process events to prevent freezing
                QApplication.processEvents()
                
                # Show result
                if success:
                    self.show_message_with_copy(
                        'Connection Success',
                        message,
                        QMessageBox.Icon.Information
                    )
                else:
                    msg_box = QMessageBox(self)
                    msg_box.setIcon(QMessageBox.Icon.Warning)
                    msg_box.setWindowTitle('Connection Failed')
                    msg_box.setText(message)
                    msg_box.setStandardButtons(QMessageBox.StandardButton.Ok)
                    msg_box.setMinimumWidth(400)
                    msg_box.exec()

            finally:
                progress.close()
                # Update device table to reflect new status
                self.update_device_table()

        except Exception as e:
            error_msg = f"Test connection error: {str(e)}"
            logging.error(error_msg)
            self.show_message_with_copy(
                'Test Connection Error',
                error_msg,
                QMessageBox.Icon.Critical
            )

    def upload_config(self):
        """Upload configuration to selected devices."""
        selected_devices = self.get_selected_devices_from_device_table()
        if not selected_devices:
            self.show_message_with_copy(
                'No Selection',
                'Please select at least one device for configuration upload',
                QMessageBox.Icon.Warning
            )
            return

        try:
            # TODO: Implement actual config upload process
            self.show_message_with_copy(
                'Upload Started',
                f'Starting configuration upload for {len(selected_devices)} selected device(s)',
                QMessageBox.Icon.Information
            )

        except Exception as e:
            self.show_message_with_copy(
                'Upload Error',
                f'Failed to start configuration upload: {str(e)}',
                QMessageBox.Icon.Critical
            )

    def closeEvent(self, event):
        """Handle application close event."""
        try:
            # Stop event loop
            if hasattr(self, 'loop') and self.loop.is_running():
                self.loop.call_soon_threadsafe(self.loop.stop)
                if hasattr(self, 'loop_thread'):
                    self.loop_thread.join(timeout=1.0)
            
            # Save devices
            self.device_manager.save_devices()
            self.device_manager.save_groups()
            
        except Exception as e:
            logging.error(f"Error during shutdown: {str(e)}")
        
        event.accept()

    def backup_selected_devices(self):
        """Backup configuration of selected devices."""
        try:
            # Get selected devices from backup table
            selected_devices = []
            for row in range(self.backup_table.rowCount()):
                checkbox = self.backup_table.item(row, 0)
                if checkbox and checkbox.checkState() == Qt.CheckState.Checked:
                    device_name = self.backup_table.item(row, 1).text()
                    if device_name in self.device_manager.devices:
                        selected_devices.append(self.device_manager.devices[device_name])
            
            if not selected_devices:
                self.show_message_with_copy(
                    'No Selection',
                    'Please select at least one device to backup',
                    QMessageBox.Icon.Warning
                )
                return
            
            # Run backup in event loop
            if not self.loop.is_running():
                # Start event loop if not running
                def run_loop():
                    asyncio.set_event_loop(self.loop)
                    self.loop.run_forever()
                
                self.loop_thread = threading.Thread(target=run_loop, daemon=True)
                self.loop_thread.start()
            
            # Schedule backup task
            future = asyncio.run_coroutine_threadsafe(
                self._backup_devices(selected_devices),
                self.loop
            )
            
            # Add callback to handle completion
            def backup_done(fut):
                try:
                    fut.result()
                except Exception as e:
                    logging.error(f"Backup failed: {str(e)}")
            
            future.add_done_callback(backup_done)
            
        except Exception as e:
            error_msg = f"Error starting backup: {str(e)}"
            logging.error(error_msg)
            self.show_message_with_copy(
                'Backup Error',
                error_msg,
                QMessageBox.Icon.Critical
            )

    async def _backup_devices(self, devices):
        """Perform backup of selected devices with real-time updates."""
        try:
            for device in devices:
                try:
                    # Start backup
                    logging.info(f"Starting backup for {device.name}")
                    await device.backup_config()
                    
                    # Update UI after each operation
                    self.update_backup_table()
                    QApplication.processEvents()
                    
                except Exception as e:
                    logging.error(f"Error backing up device {device.name}: {str(e)}")
                    device.connection_status = ConnectionStatus.BACKUP_FAILED
                    device.backup_status = f"Backup failed: {str(e)}"
                    self.update_backup_table()
                    QApplication.processEvents()
            
            # Final update
            self.update_backup_table()
            
        except Exception as e:
            error_msg = f"Error in backup process: {str(e)}"
            logging.error(error_msg)
            self.show_message_with_copy(
                'Backup Error',
                error_msg,
                QMessageBox.Icon.Critical
            )

    def restore_selected_devices(self):
        """Restore configuration to selected devices."""
        try:
            # Get selected devices from backup table
            selected_devices = []
            for row in range(self.backup_table.rowCount()):
                checkbox = self.backup_table.item(row, 0)
                if checkbox and checkbox.checkState() == Qt.CheckState.Checked:
                    device_name = self.backup_table.item(row, 1).text()
                    if device_name in self.device_manager.devices:
                        selected_devices.append(self.device_manager.devices[device_name])
            
            if not selected_devices:
                self.show_message_with_copy(
                    'No Selection',
                    'Please select at least one device to restore',
                    QMessageBox.Icon.Warning
                )
                return
            
            # Confirm restore
            result = QMessageBox.warning(
                self,
                'Confirm Restore',
                'Are you sure you want to restore the selected devices to their last backup?\n'
                'This will overwrite their current configuration.',
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No
            )
            
            if result != QMessageBox.StandardButton.Yes:
                return
            
            # Create progress dialog
            progress = QProgressDialog('Restoring devices...', 'Cancel', 0, len(selected_devices), self)
            progress.setWindowModality(Qt.WindowModality.WindowModal)
            progress.setMinimumDuration(0)
            
            # Start restore process
            for i, device in enumerate(selected_devices):
                if progress.wasCanceled():
                    break
                
                try:
                    # Update progress
                    progress.setValue(i)
                    progress.setLabelText(f'Restoring {device.name}...')
                    
                    # TODO: Implement actual restore logic here
                    # For now, just simulate restore
                    QThread.msleep(1000)  # Simulate work
                    
                except Exception as e:
                    logging.error(f"Error restoring device {device.name}: {str(e)}")
                    self.show_message_with_copy(
                        'Restore Error',
                        f'Failed to restore {device.name}: {str(e)}',
                        QMessageBox.Icon.Critical
                    )
            
            # Complete progress
            progress.setValue(len(selected_devices))
            
            # Update tables
            self.update_device_table()
            
            self.show_message_with_copy(
                'Restore Complete',
                'Selected devices have been restored successfully',
                QMessageBox.Icon.Information
            )
            
        except Exception as e:
            error_msg = f"Error in restore process: {str(e)}"
            logging.error(error_msg)
            self.show_message_with_copy(
                'Restore Error',
                error_msg,
                QMessageBox.Icon.Critical
            )

    def update_backup_location_status(self):
        """Update status bar with backup location."""
        try:
            settings_file = os.path.expanduser("~/.pulsarnet/settings.json")
            if os.path.exists(settings_file):
                with open(settings_file, 'r') as f:
                    settings = json.load(f)
                    local_path = settings.get('local_path', os.path.expanduser("~/.pulsarnet/backups"))
                    remote_type = settings.get('remote_type', 'None')
                    
                    status_msg = f"Backup Location: {local_path}"
                    if remote_type != 'None':
                        status_msg += f" | Remote: {remote_type}"
                    
                    self.statusBar.showMessage(status_msg)
            else:
                self.statusBar.showMessage("Backup Location: ~/.pulsarnet/backups (Default)")
        except Exception as e:
            logging.error(f"Failed to update backup location status: {e}")

    def save_storage_settings(self):
        """Save storage settings to file."""
        try:
            settings = {
                'local_path': self.local_path.text(),
                'remote_type': self.remote_type.currentText(),
                'remote_host': self.remote_host.text(),
                'remote_port': self.remote_port.value(),
                'remote_username': self.remote_user.text(),
                'remote_password': self.remote_pass.text(),
                'remote_path': self.remote_path.text()
            }
            
            settings_file = os.path.expanduser("~/.pulsarnet/settings.json")
            os.makedirs(os.path.dirname(settings_file), exist_ok=True)
            
            with open(settings_file, 'w') as f:
                json.dump(settings, f, indent=4)
                
            self.update_backup_location_status()
            self.show_message_with_copy(
                'Success',
                'Storage settings saved successfully',
                QMessageBox.Icon.Information
            )
            
        except Exception as e:
            error_msg = f"Failed to save storage settings: {str(e)}"
            logging.error(error_msg)
            self.show_message_with_copy(
                'Error',
                error_msg,
                QMessageBox.Icon.Critical
            )
            
    def load_storage_settings(self):
        """Load storage settings from file."""
        try:
            settings_file = os.path.expanduser("~/.pulsarnet/settings.json")
            if os.path.exists(settings_file):
                with open(settings_file, 'r') as f:
                    settings = json.load(f)
                    
                    self.local_path.setText(settings.get('local_path', ''))
                    self.remote_type.setCurrentText(settings.get('remote_type', 'None'))
                    self.remote_host.setText(settings.get('remote_host', ''))
                    self.remote_port.setValue(settings.get('remote_port', 21))
                    self.remote_user.setText(settings.get('remote_username', ''))
                    self.remote_pass.setText(settings.get('remote_password', ''))
                    self.remote_path.setText(settings.get('remote_path', ''))
                
        except Exception as e:
            error_msg = f"Failed to load storage settings: {str(e)}"
            logging.error(error_msg)
            self.show_message_with_copy(
                'Error',
                error_msg,
                QMessageBox.Icon.Critical
            )

    def show_scheduler(self):
        """Show scheduler tab."""
        tab_widget = self.findChild(QTabWidget)
        if tab_widget:
            for i in range(tab_widget.count()):
                if tab_widget.tabText(i).lower() == 'scheduler':
                    tab_widget.setCurrentIndex(i)
                    return

    def show_storage_settings(self):
        """Show storage settings tab."""
        tab_widget = self.findChild(QTabWidget)
        if tab_widget:
            for i in range(tab_widget.count()):
                if tab_widget.tabText(i).lower() == 'storage':
                    tab_widget.setCurrentIndex(i)
                    return

    def show_backup_tab(self):
        """Show backup tab."""
        if hasattr(self, 'tab_widget'):
            for i in range(self.tab_widget.count()):
                if self.tab_widget.tabText(i).lower() == 'backup':
                    self.tab_widget.setCurrentIndex(i)
                    break

    def show_monitoring_tab(self):
        """Show monitoring tab."""
        if hasattr(self, 'tab_widget'):
            for i in range(self.tab_widget.count()):
                if self.tab_widget.tabText(i).lower() == 'monitoring':
                    self.tab_widget.setCurrentIndex(i)
                    break

    def show_devices_tab(self):
        """Show devices tab."""
        if hasattr(self, 'tab_widget'):
            for i in range(self.tab_widget.count()):
                if self.tab_widget.tabText(i).lower() == 'devices':
                    self.tab_widget.setCurrentIndex(i)
                    break

    def backup_selected_devices(self):
        """Backup configuration of selected devices."""
        selected_rows = self.device_table.selectedIndexes()
        if not selected_rows:
            self.show_message_with_copy(
                'No Devices Selected',
                'Please select devices to backup',
                QMessageBox.Icon.Warning
            )
            return
            
        self.backup_devices([self.device_table.item(row.row(), 1).text() 
                           for row in selected_rows if row.column() == 1])
        
    def backup_all_devices(self):
        """Backup configuration of all devices."""
        device_names = [self.device_table.item(row, 1).text() 
                       for row in range(self.device_table.rowCount())]
        self.backup_devices(device_names)

    def show_message_with_copy(self, title, message, icon=QMessageBox.Icon.Information):
        """Show a message box with copy functionality."""
        msg_box = QMessageBox(self)
        msg_box.setWindowTitle(title)
        msg_box.setText(message)
        msg_box.setIcon(icon)
        
        # Add copy button
        copy_button = msg_box.addButton(
            'Copy Message',
            QMessageBox.ButtonRole.ActionRole
        )
        copy_button.clicked.connect(
            lambda: QApplication.clipboard().setText(message)
        )
        
        # Add standard OK button
        msg_box.addButton(QMessageBox.StandardButton.Ok)
        
        msg_box.exec()