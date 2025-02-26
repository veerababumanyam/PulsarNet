from PyQt6.QtWidgets import QGridLayout
"""MainWindow class for PulsarNet's graphical user interface.

This module implements the main application window following ISO 9241-171:2008
accessibility standards and provides a modern, user-friendly interface.
"""

import sys
import json
import csv
import tempfile
import shutil
import time
from datetime import datetime, timedelta
from pathlib import Path
import logging
import asyncio
import threading
import os

from PyQt6.QtCore import (
    Qt, QMetaObject, pyqtSlot, QTimer, QTime, Q_ARG,
    QSettings, QCoreApplication, QSize, QThread, QDateTime, QItemSelectionModel,
    QModelIndex, QSortFilterProxyModel, QUrl, QMarginsF, pyqtSignal
)
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QTabWidget, QWidget, QVBoxLayout,
    QHBoxLayout, QLabel, QPushButton, QLineEdit, QTableWidget, QTableWidgetItem, QHeaderView,
    QDialog, QDialogButtonBox, QFormLayout, QGroupBox, QCheckBox, QComboBox,
    QStackedWidget, QTextEdit, QMessageBox, QSpinBox, QFileDialog, QTimeEdit,
    QMenu, QToolBar, QStatusBar, QStyleFactory, QTextBrowser, QProgressDialog,
    QInputDialog, QProgressBar, QDockWidget, QFrame, QListWidget, QListWidgetItem,
    QStyle, QGridLayout
)
from PyQt6.QtGui import (
    QPalette, QColor, QIcon, QFont, QPixmap, QCursor, QBrush, QAction
)

# Import all scheduler components in one line
from pulsarnet.scheduler.scheduler import ScheduleManager, BackupSchedule, ScheduleType, TargetType
# Update import path to use device_management
from pulsarnet.device_management.device import Device 
from pulsarnet.device_management.device_types import DeviceType
from pulsarnet.device_management.connection_types import ConnectionStatus
from pulsarnet.device_management.device_group import DeviceGroup
from pulsarnet.device_management.device_manager import DeviceManager
from pulsarnet.gui.device_dialog import DeviceDialog
from pulsarnet.gui.group_dialog import GroupDialog
from pulsarnet.gui.settings_dialog import SettingsDialog
from pulsarnet.gui.group_manager import GroupManager
from pulsarnet.gui.views.storage_view import StorageTabView
from pulsarnet.gui.controllers.storage_controller import StorageTabController
from pulsarnet.gui.views.scheduler_view import SchedulerTabView
from pulsarnet.gui.controllers.scheduler_controller import SchedulerTabController

class MainWindow(QMainWindow):
    """Main application window for PulsarNet."""
    
    # Signal definitions for thread-safe UI updates
    update_backup_table_signal = pyqtSignal()
    backup_success_signal = pyqtSignal(int)
    backup_partial_signal = pyqtSignal(int, int)
    show_message_signal = pyqtSignal(str, str, object)
    
    def __init__(self):
        """Initialize the main window."""
        super().__init__()
        
        # Set default size and window title
        self.resize(1200, 800)
        self.setWindowTitle("PulsarNet - Network Device Management")
        
        # Initialize managers needed for UI
        self.device_manager = DeviceManager()
        self.device_manager.load_devices()
        self.schedule_manager = ScheduleManager()
        self.group_manager = GroupManager(self)
        
        # Initialize core components
        self.init_components()
        
        # Connect signals to slots
        self.connect_signals()
        
        # Initialize event loop for async operations
        self.loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self.loop)
        
        # Initialize scheduler timer
        self.scheduler_timer = QTimer()
        self.scheduler_timer.timeout.connect(self.check_schedules)
        self.scheduler_timer.start(60000)  # Check every minute
        
        # Initialize backup_manager attribute for backup operations
        from pulsarnet.backup_operations.backup_manager import BackupManager
        from pathlib import Path
        self.backup_manager = BackupManager(Path("backups"))
        
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
        
        # Register device manager callback to auto-update backup tab when device list changes
        try:
            if hasattr(self, 'device_manager'):
                self.device_manager.on_devices_changed = self.update_backup_table
        except Exception as e:
            import logging
            logging.error(f"Error setting device manager update callback: {e}")
        # Initial update of backup table to reflect current devices
        self.update_backup_table()

    def init_components(self):
        """Initialize core components."""
        # Initialize UI components
        self.init_ui()
        
        # Setup connections
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.check_schedules)
        self.timer.start(60000)  # Check schedules every minute

    def connect_signals(self):
        """Connect signals to their respective slots."""
        # Connect the backup table update signal
        self.update_backup_table_signal.connect(self.update_backup_table_safe)
        
        # Connect backup result signals
        self.backup_success_signal.connect(self.show_backup_success)
        self.backup_partial_signal.connect(self.show_backup_partial)
        
        # Connect message signal
        self.show_message_signal.connect(self.show_message_with_copy)

    def init_ui(self):
        """Initialize the user interface."""
        self.setWindowTitle('PulsarNet - Network Device Management')
        self.setMinimumSize(900, 600)
        
        # Apply stylesheet
        self.setup_style()
        
        # Create central widget
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        layout = QVBoxLayout(central_widget)
        
        # Create tab widget
        self.tab_widget = QTabWidget()
        layout.addWidget(self.tab_widget)
        
        # Create tabs
        self.create_device_tab(self.tab_widget)
        self.create_groups_tab(self.tab_widget)  # Add Groups tab
        self.create_backup_tab(self.tab_widget)
        
        # Create storage and scheduler tabs explicitly
        try:
            # Create storage tab
            self.storage_view = StorageTabView(self)
            self.storage_controller = StorageTabController(self, self.storage_view)
            self.tab_widget.addTab(self.storage_view, "Storage")
            
            # Create scheduler tab
            self.scheduler_view = SchedulerTabView(self)
            self.scheduler_controller = SchedulerTabController(self, self.scheduler_view)
            self.tab_widget.addTab(self.scheduler_view, "Scheduler")
            
            # Initialize the scheduler controller
            self.scheduler_controller.initialize()
        except Exception as e:
            logging.error(f"Error creating modular tabs: {str(e)}")
            QMessageBox.critical(self, "Tab Creation Error", f"An error occurred while creating tabs:\n{str(e)}")
            
        self.create_monitoring_tab(self.tab_widget)
        
        # Create status bar
        self.create_status_summary()
        
        # Create menu bar and toolbar
        self.create_menu()
        self.create_toolbar()
        
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
        self.toolbar = QToolBar()
        self.toolbar.setMovable(False)
        self.toolbar.setIconSize(QSize(24, 24))
        self.addToolBar(self.toolbar)

    def create_status_summary(self):
        """Create and setup the status bar summary widgets."""
        # Create status bar elements
        self.statusBar().showMessage("Ready")
        
        # Add storage status indicator
        self.storage_status = QLabel("Storage: OK")
        self.storage_status.setToolTip("Storage location status")
        self.statusBar().addPermanentWidget(self.storage_status)
        
        # Add device count indicator
        self.device_count = QLabel("Devices: 0")
        self.device_count.setToolTip("Number of configured devices")
        self.statusBar().addPermanentWidget(self.device_count)
        
        # Add backup status indicator
        self.backup_status = QLabel("No backups run")
        self.backup_status.setToolTip("Last backup status")
        self.statusBar().addPermanentWidget(self.backup_status)
        
    def create_menu(self):
        """Create the main menu bar."""
        menu_bar = self.menuBar()
        
        # File menu
        file_menu = menu_bar.addMenu("&File")
        
        # Add device action
        add_device_action = QAction('Add Device', self)
        add_device_action.triggered.connect(self.show_add_device_dialog)
        file_menu.addAction(add_device_action)
        
        # Import devices action
        import_action = QAction('Import Devices', self)
        import_action.triggered.connect(self.import_devices)
        file_menu.addAction(import_action)
        
        # Export devices action
        export_action = QAction('Export Devices', self)
        export_action.triggered.connect(self.upload_config)
        file_menu.addAction(export_action)
        
        file_menu.addSeparator()
        
        # Add exit action
        exit_action = QAction('Exit', self)
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)
        
    def create_device_tab(self, tab_widget):
        """Create the device management tab with combined modern and legacy device functionality."""
        device_widget = QWidget()
        layout = QVBoxLayout(device_widget)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(10)

        # Device controls
        controls = QHBoxLayout()
        controls.setSpacing(8)

        add_device_btn = QPushButton('Add Device')
        add_device_btn.setToolTip('Add a new network device')
        add_device_btn.clicked.connect(self.show_add_device_dialog)
        add_device_btn.setAccessibleName('Add Device Button')
        add_device_btn.setAccessibleDescription('Button to add a new network device')
        controls.addWidget(add_device_btn)
        
        edit_device_btn = QPushButton('Edit Device')
        edit_device_btn.setToolTip('Edit selected device')
        edit_device_btn.clicked.connect(self.edit_selected_device)
        edit_device_btn.setAccessibleName('Edit Device Button')
        edit_device_btn.setAccessibleDescription('Button to edit the selected device')
        controls.addWidget(edit_device_btn)

        add_group_btn = QPushButton('Add Group')
        add_group_btn.setToolTip('Create a new device group')
        add_group_btn.clicked.connect(self.show_add_group_dialog)
        add_group_btn.setAccessibleName('Add Group Button')
        add_group_btn.setAccessibleDescription('Button to create a new device group')
        controls.addWidget(add_group_btn)

        import_btn = QPushButton('Import')
        import_btn.setToolTip('Import devices from CSV file')
        import_btn.clicked.connect(self.import_devices)
        import_btn.setAccessibleName('Import Devices Button')
        import_btn.setAccessibleDescription('Button to import devices from CSV file')
        controls.addWidget(import_btn)

        test_conn_btn = QPushButton('Test Connection')
        test_conn_btn.setToolTip('Test connection to selected device')
        test_conn_btn.clicked.connect(self.test_selected_device_connection)
        test_conn_btn.setAccessibleName('Test Connection Button')
        test_conn_btn.setAccessibleDescription('Button to test connection to selected device')
        controls.addWidget(test_conn_btn)

        remove_device_btn = QPushButton('Remove Device')
        remove_device_btn.setToolTip('Remove selected devices')
        remove_device_btn.clicked.connect(self.remove_selected_device)
        remove_device_btn.setAccessibleName('Remove Device Button')
        remove_device_btn.setAccessibleDescription('Button to remove selected devices')
        controls.addWidget(remove_device_btn)

        controls.addStretch()

        # Right-aligned controls group
        right_controls = QHBoxLayout()
        right_controls.setSpacing(8)

        upload_btn = QPushButton('Export to CSV')
        upload_btn.setToolTip('Export selected devices to CSV file')
        upload_btn.clicked.connect(self.upload_config)
        upload_btn.setAccessibleName('Export to CSV Button')
        upload_btn.setAccessibleDescription('Button to export selected devices to a CSV file')
        right_controls.addWidget(upload_btn)

        refresh_btn = QPushButton('Refresh Status')
        refresh_btn.setToolTip('Refresh connection status of all devices')
        refresh_btn.clicked.connect(self.refresh_device_status)
        refresh_btn.setAccessibleName('Refresh Status Button')
        refresh_btn.setAccessibleDescription('Button to refresh connection status of all devices')
        right_controls.addWidget(refresh_btn)

        controls.addLayout(right_controls)
        layout.addLayout(controls)

        # Device filter controls
        filter_layout = QHBoxLayout()
        filter_layout.setSpacing(8)
        
        filter_label = QLabel("Filter by:")
        filter_layout.addWidget(filter_label)
        
        self.device_filter_combo = QComboBox()
        self.device_filter_combo.addItems(["All Devices", "Standard Devices"])
        self.device_filter_combo.currentTextChanged.connect(self.update_device_table)
        filter_layout.addWidget(self.device_filter_combo)
        
        self.connection_filter_combo = QComboBox()
        self.connection_filter_combo.addItems(["All Connections", "Direct", "Jump Host"])
        self.connection_filter_combo.currentTextChanged.connect(self.update_device_table)
        filter_layout.addWidget(self.connection_filter_combo)
        
        filter_layout.addStretch()
        layout.addLayout(filter_layout)

        # Device table
        self.device_table = QTableWidget()
        self.device_table.setColumnCount(20)
        self.device_table.setHorizontalHeaderLabels([
            'Select', 'Name', 'IP Address', 'Type', 'Username', 
            'Password', 'Protocol', 'Port', 'Connection Type', 
            'Jump Server IP', 'Jump Server Name', 'Jump Username', 
            'Jump Password', 'Jump Protocol', 'Jump Port', 
            'Enable Password', 'Use Keys', 'Key File', 
            'Connection Status', 'Last Connected'
        ])
        self.device_table.horizontalHeader().setStretchLastSection(True)
        self.device_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.device_table.setSelectionMode(QTableWidget.SelectionMode.SingleSelection)
        # Add context menu support
        self.device_table.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.device_table.customContextMenuRequested.connect(self.show_device_context_menu)
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
                    
                    # Track groups for each device
                    device_groups = {}
                    
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
                            
                            # Process connection type and jump host configuration
                            connection_type = row.get('connection_type', 'direct_ssh').lower()
                            use_jump_server = False
                            
                            # Convert use_jump_server to boolean
                            if 'use_jump_server' in row:
                                use_jump_server_val = row['use_jump_server'].lower().strip()
                                use_jump_server = use_jump_server_val in ['true', 'yes', '1']
                            
                            # Handle jump host connection types
                            if connection_type.startswith('jump_') or connection_type == 'jump_host':
                                use_jump_server = True
                                logging.info(f"Setting use_jump_server=True based on connection_type={connection_type}")
                                
                                # Validate jump host fields
                                if not row.get('jump_server'):
                                    logging.warning(f"Jump server not specified for {row['name']} with connection type {connection_type}")
                                
                                # Special handling for 'jump_host' connection type
                                if connection_type == 'jump_host':
                                    device_protocol = row.get('protocol', 'ssh').lower()
                                    jump_protocol = row.get('jump_protocol', 'ssh').lower()
                                    
                                    if jump_protocol == 'telnet' and device_protocol == 'telnet':
                                        connection_type = 'jump_telnet/telnet'
                                    elif jump_protocol == 'telnet' and device_protocol == 'ssh':
                                        connection_type = 'jump_telnet/ssh'
                                    elif jump_protocol == 'ssh' and device_protocol == 'telnet':
                                        connection_type = 'jump_ssh/telnet'
                                    else:  # Default: SSH jump host to SSH device
                                        connection_type = 'jump_ssh/ssh'
                                    
                                    logging.info(f"Converted 'jump_host' to '{connection_type}' based on protocols")
                            
                            # Create device using Device.from_dict to ensure proper handling of all fields
                            device_data = {
                                'name': row['name'].strip(),
                                'ip_address': row['ip_address'].strip(),
                                'device_type': valid_types[device_type],
                                'username': row['username'].strip(),
                                'password': row['password'].strip(),
                                'enable_password': row.get('enable_password', '').strip() or None,
                                'port': int(row.get('port', 22)),
                                'connection_type': connection_type,
                                'use_jump_server': use_jump_server,
                                'jump_server': row.get('jump_server', '').strip(),
                                'jump_username': row.get('jump_username', '').strip(),
                                'jump_password': row.get('jump_password', '').strip(),
                                'jump_protocol': row.get('jump_protocol', 'ssh').strip(),
                                'jump_host_name': row.get('jump_host_name', '').strip(),
                                'jump_port': int(row.get('jump_port', 22)) if row.get('jump_port') else 22
                            }
                            
                            # Log jump host details if present
                            if use_jump_server:
                                logging.info(f"Jump host details for {row['name']}:")
                                logging.info(f"  - jump_server: {device_data['jump_server']}")
                                logging.info(f"  - jump_username: {device_data['jump_username']}")
                                logging.info(f"  - jump_protocol: {device_data['jump_protocol']}")
                                logging.info(f"  - jump_port: {device_data['jump_port']}")
                                logging.info(f"  - connection_type: {device_data['connection_type']}")
                            
                            # Create device using from_dict to ensure proper handling
                            device = Device.from_dict(device_data)
                            
                            # Add device
                            self.device_manager.devices[device.name] = device
                            
                            # Track groups for this device if specified
                            if 'groups' in row and row['groups'].strip():
                                device_groups[device.name] = [g.strip() for g in row['groups'].split(',') if g.strip()]
                                logging.info(f"Device {device.name} will be added to groups: {device_groups[device.name]}")
                            
                            success_count += 1
                            logging.info(f"Successfully imported device: {device.name}")
                            
                        except Exception as e:
                            error_count += 1
                            error_msg = f"Row {row_num}: {str(e)}"
                            errors.append(error_msg)
                            logging.error(error_msg)
                    
                    # Process group assignments
                    if device_groups:
                        groups_created = 0
                        for device_name, group_names in device_groups.items():
                            for group_name in group_names:
                                # Create group if it doesn't exist
                                if group_name not in self.device_manager.groups:
                                    self.device_manager.groups[group_name] = DeviceGroup(group_name, [])
                                    groups_created += 1
                                
                                # Add device to group
                                if device_name not in self.device_manager.groups[group_name].members:
                                    self.device_manager.groups[group_name].members.append(device_name)
                                    logging.info(f"Added {device_name} to group {group_name}")
                        
                        # Log group creation summary
                        if groups_created > 0:
                            logging.info(f"Created {groups_created} new device groups")
                        
                        # Save groups
                        self.device_manager.save_groups()
                    
                    # Save devices
                    if success_count > 0:
                        self.device_manager.save_devices()
                        logging.info("Saved devices to disk")
                    
                    # Update tables
                    self.update_device_table()
                    self.update_backup_table()  # Also update the backup table
                    
                    # Show results
                    message = f"Successfully imported {success_count} devices."
                    if device_groups:
                        total_assignments = sum(len(groups) for groups in device_groups.values())
                        message += f"\nAssigned devices to {total_assignments} group memberships."
                    
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
        self.device_table.setRowCount(0)
        
        # Get filter values
        device_filter = self.device_filter_combo.currentText()
        connection_filter = self.connection_filter_combo.currentText()
        
        row = 0
        
        # Add standard devices first if they match the filter
        if device_filter in ["All Devices", "Standard Devices"]:
            for device_name, device in self.device_manager.devices.items():
                # Apply connection filter
                if connection_filter == "Jump Host" and not getattr(device, 'use_jump_server', False):
                    continue
                if connection_filter == "Direct" and getattr(device, 'use_jump_server', False):
                    continue
                
                self.device_table.insertRow(row)
                
                # Create checkbox for selection
                checkbox = QTableWidgetItem()
                checkbox.setFlags(Qt.ItemFlag.ItemIsUserCheckable | Qt.ItemFlag.ItemIsEnabled)
                checkbox.setCheckState(Qt.CheckState.Unchecked)
                self.device_table.setItem(row, 0, checkbox)
                
                # Set device information
                self.device_table.setItem(row, 1, QTableWidgetItem(device.name))
                self.device_table.setItem(row, 2, QTableWidgetItem(device.ip_address))
                device_type_str = device.device_type.name if hasattr(device.device_type, 'name') else str(device.device_type)
                self.device_table.setItem(row, 3, QTableWidgetItem(device_type_str))
                self.device_table.setItem(row, 4, QTableWidgetItem(getattr(device, 'username', '')))
                
                # Password - mask with asterisks for security
                password = getattr(device, 'password', '')
                masked_password = '*' * len(password) if password else ''
                self.device_table.setItem(row, 5, QTableWidgetItem(masked_password))
                
                # Protocol
                conn_type_obj = getattr(device, 'connection_type', 'SSH')
                if hasattr(conn_type_obj, 'value'):
                    protocol = str(conn_type_obj.value).split('_')[1].upper() if '_' in str(conn_type_obj.value) else 'SSH'
                else:
                    protocol = str(conn_type_obj).upper()
                self.device_table.setItem(row, 6, QTableWidgetItem(protocol))
                
                # Port
                self.device_table.setItem(row, 7, QTableWidgetItem(str(getattr(device, 'port', 22))))
                
                # Connection Type (Direct/Jump Host)
                use_jump_server = getattr(device, 'use_jump_server', False)
                connection_type = "Jump Host" if use_jump_server else "Direct"
                self.device_table.setItem(row, 8, QTableWidgetItem(connection_type))
                
                # Jump Server IP
                jump_server = getattr(device, 'jump_server', '')
                self.device_table.setItem(row, 9, QTableWidgetItem(jump_server if jump_server else ''))
                
                # Jump Server Name
                jump_host_name = getattr(device, 'jump_host_name', '')
                self.device_table.setItem(row, 10, QTableWidgetItem(jump_host_name if jump_host_name else ''))
                
                # Jump Username
                jump_username = getattr(device, 'jump_username', '')
                self.device_table.setItem(row, 11, QTableWidgetItem(jump_username))
                
                # Jump Password - mask with asterisks for security
                jump_password = getattr(device, 'jump_password', '')
                masked_jump_password = '*' * len(jump_password) if jump_password else ''
                self.device_table.setItem(row, 12, QTableWidgetItem(masked_jump_password))
                
                # Jump Protocol
                jump_connection_type = getattr(device, 'jump_connection_type', 'ssh')
                if hasattr(jump_connection_type, 'value'):
                    jump_protocol = str(jump_connection_type.value).upper()
                else:
                    jump_protocol = str(jump_connection_type).upper()
                self.device_table.setItem(row, 13, QTableWidgetItem(jump_protocol))
                
                # Jump Port
                jump_port = getattr(device, 'jump_port', 22)
                self.device_table.setItem(row, 14, QTableWidgetItem(str(jump_port) if jump_port else '22'))
                
                # Enable Password - mask with asterisks for security
                enable_password = getattr(device, 'enable_password', '')
                masked_enable_password = '*' * len(enable_password) if enable_password else ''
                self.device_table.setItem(row, 15, QTableWidgetItem(masked_enable_password))
                
                # Use Keys
                use_keys = getattr(device, 'use_keys', False)
                self.device_table.setItem(row, 16, QTableWidgetItem(str(use_keys)))
                
                # Key File
                key_file = getattr(device, 'key_file', '')
                self.device_table.setItem(row, 17, QTableWidgetItem(key_file if key_file else ''))
                
                # Connection Status
                connection_status = getattr(device, 'connection_status', 'Unknown')
                status_text = connection_status.value if hasattr(connection_status, 'value') else str(connection_status)
                status_item = QTableWidgetItem(status_text)
                
                # Color code the status
                if hasattr(connection_status, 'value'):
                    if connection_status.value.lower() == 'connected':
                        status_item.setForeground(QBrush(QColor('green')))
                    elif connection_status.value.lower() in ['error', 'timeout', 'failed']:
                        status_item.setForeground(QBrush(QColor('red')))
                    else:
                        status_item.setForeground(QBrush(QColor('orange')))
                
                self.device_table.setItem(row, 18, status_item)
                
                # Last Connected
                last_connected = getattr(device, 'last_connected', None)
                last_connected_str = last_connected.strftime('%Y-%m-%d %H:%M:%S') if last_connected else 'Never'
                self.device_table.setItem(row, 19, QTableWidgetItem(last_connected_str))
                
                row += 1
        
        # Adjust column widths
        self.device_table.resizeColumnsToContents()
        
        # Don't auto-refresh statuses on application load
        # self.refresh_device_status()

    def update_backup_table(self):
        """Update the backup table based on current filter selection."""
        # Check if backup UI components are initialized
        if not hasattr(self, 'backup_table') or not hasattr(self, 'backup_group_combo'):
            return
            
        # Reset and repopulate the groups combo box
        current_group = self.backup_group_combo.currentText()
        self.backup_group_combo.clear()
        self.backup_group_combo.addItem("Select Group")
        for group_name in sorted(self.device_manager.groups.keys()):
            self.backup_group_combo.addItem(group_name)
            
        # Try to restore the previous selection
        index = self.backup_group_combo.findText(current_group)
        if index >= 0:
            self.backup_group_combo.setCurrentIndex(index)
            
        # Apply the current filter after updating the UI components
        self.apply_backup_filter()
        
        # Update status
        self.backup_status_label.setText(f"Device list refreshed. {self.backup_table.rowCount()} devices shown.")
        self.backup_status_label.setStyleSheet("color: green;")

    def create_groups_tab(self, tab_widget):
        """Create the groups management tab."""
        groups_widget = QWidget()
        layout = QVBoxLayout(groups_widget)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(10)

        # Group controls
        controls = QHBoxLayout()
        controls.setSpacing(8)

        add_group_btn = QPushButton('Add Group')
        add_group_btn.setToolTip('Create a new device group')
        add_group_btn.clicked.connect(self.show_add_group_dialog)
        add_group_btn.setAccessibleName('Add Group Button')
        add_group_btn.setAccessibleDescription('Button to create a new device group')
        controls.addWidget(add_group_btn)
        
        edit_group_btn = QPushButton('Edit Group')
        edit_group_btn.setToolTip('Edit selected group')
        edit_group_btn.clicked.connect(self.edit_selected_group)
        edit_group_btn.setAccessibleName('Edit Group Button')
        edit_group_btn.setAccessibleDescription('Button to edit the selected group')
        controls.addWidget(edit_group_btn)
        
        remove_group_btn = QPushButton('Remove Group')
        remove_group_btn.setToolTip('Remove selected groups')
        remove_group_btn.clicked.connect(self.remove_selected_group)
        remove_group_btn.setAccessibleName('Remove Group Button')
        remove_group_btn.setAccessibleDescription('Button to remove selected groups')
        controls.addWidget(remove_group_btn)
        
        backup_group_btn = QPushButton('Backup Group')
        backup_group_btn.setToolTip('Backup all devices in selected group')
        backup_group_btn.clicked.connect(self.backup_selected_group)
        backup_group_btn.setAccessibleName('Backup Group Button')
        backup_group_btn.setAccessibleDescription('Button to backup all devices in selected group')
        controls.addWidget(backup_group_btn)
        
        controls.addStretch()
        layout.addLayout(controls)

        # Groups table
        self.groups_table = QTableWidget()
        self.groups_table.setColumnCount(4)
        self.groups_table.setHorizontalHeaderLabels([
            'Select', 'Name', 'Description', 'Device Count'
        ])
        self.groups_table.horizontalHeader().setStretchLastSection(True)
        self.groups_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.groups_table.setSelectionMode(QTableWidget.SelectionMode.SingleSelection)
        # Connect checkbox state change to trigger group selection update
        self.groups_table.itemChanged.connect(self.on_group_selection_changed)
        # Add context menu support
        self.groups_table.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.groups_table.customContextMenuRequested.connect(self.show_group_context_menu)
        layout.addWidget(self.groups_table)

        # Group members section
        members_label = QLabel("Group Members:")
        layout.addWidget(members_label)
        
        self.group_members_table = QTableWidget()
        self.group_members_table.setColumnCount(3)
        self.group_members_table.setHorizontalHeaderLabels([
            'Device Name', 'IP Address', 'Status'
        ])
        self.group_members_table.horizontalHeader().setStretchLastSection(True)
        layout.addWidget(self.group_members_table)
        


        # Update the groups table
        self.update_groups_table()
        
        # Connect selection changed event
        self.groups_table.itemSelectionChanged.connect(self.on_group_selection_changed)

        tab_widget.addTab(groups_widget, 'Groups')

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
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.Fixed)  # Checkbox
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)  # Name
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)  # IP
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.Stretch)  # Type
        header.setSectionResizeMode(4, QHeaderView.ResizeMode.Stretch)  # Status
        header.setSectionResizeMode(5, QHeaderView.ResizeMode.Fixed)  # Last Backup

        self.backup_table.setColumnWidth(0, 50)  # Checkbox
        self.backup_table.setColumnWidth(5, 150)  # Last Backup

        # Create the filter panel with an enterprise-grade UI
        filter_panel = QGroupBox("Backup Filter Options")
        filter_panel_layout = QVBoxLayout()  # Use QVBoxLayout instead of QGridLayout

        # Filter type
        filter_type_layout = QHBoxLayout()
        filter_type_label = QLabel("Filter Type:")
        filter_type_label.setToolTip("Select how to filter devices for backup")
        filter_type_layout.addWidget(filter_type_label)

        self.backup_filter_combo = QComboBox()
        self.backup_filter_combo.addItems(["All Devices", "By Group"])
        self.backup_filter_combo.setToolTip("Choose which devices to include in the backup operation")
        self.backup_filter_combo.setMinimumWidth(200)
        filter_type_layout.addWidget(self.backup_filter_combo)
        filter_panel_layout.addLayout(filter_type_layout)

        # Group selection combo (enabled only when 'By Group' is selected)
        group_layout = QHBoxLayout()
        group_label = QLabel("Group:")
        group_label.setToolTip("Select a specific device group")
        group_layout.addWidget(group_label)

        self.backup_group_combo = QComboBox()
        self.backup_group_combo.addItem("Select Group")
        self.backup_group_combo.setToolTip("Select a device group to backup")
        self.backup_group_combo.setMinimumWidth(200)
        
        # Add existing groups
        for group_name in sorted(self.device_manager.groups.keys()):
            self.backup_group_combo.addItem(group_name)
            
        group_layout.addWidget(self.backup_group_combo)
        filter_panel_layout.addLayout(group_layout)

        # Status display
        status_layout = QHBoxLayout()
        self.backup_status_label = QLabel("Current Status:")
        self.backup_status_label.setToolTip("Shows information about the current selection")
        status_layout.addWidget(self.backup_status_label)
        filter_panel_layout.addLayout(status_layout)

        # Button panel
        button_panel = QHBoxLayout()
        button_panel.setSpacing(10)

        # Skip Apply Filter and Refresh buttons as they're no longer needed
        
        # Spacer
        button_panel.addStretch()

        # Backup button
        backup_btn = QPushButton('Backup')
        backup_btn.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_DialogSaveButton))
        backup_btn.setToolTip('Backup selected devices')
        backup_btn.clicked.connect(self.start_backup_filtered)
        button_panel.addWidget(backup_btn)

        # Restore button
        restore_btn = QPushButton('Restore')
        restore_btn.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_DialogOpenButton))
        restore_btn.setToolTip('Restore configuration to selected devices')
        restore_btn.clicked.connect(self.restore_selected_devices)
        button_panel.addWidget(restore_btn)

        # Connect filter change handlers
        self.backup_filter_combo.currentTextChanged.connect(self.on_backup_filter_changed)
        self.backup_group_combo.currentTextChanged.connect(self.on_backup_group_changed)
        
        # Set up the layout
        filter_panel.setLayout(filter_panel_layout)
        layout.addWidget(filter_panel)
        layout.addLayout(button_panel)
        layout.addWidget(self.backup_table)

        # Update with current devices
        self.update_backup_table()

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
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.Fixed)  # Name
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.Fixed)  # IP
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.Fixed)  # Type
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.Fixed)  # Status
        header.setSectionResizeMode(4, QHeaderView.ResizeMode.Stretch)  # Last Error
        header.setSectionResizeMode(5, QHeaderView.ResizeMode.Fixed)  # Uptime
        header.setSectionResizeMode(6, QHeaderView.ResizeMode.Fixed)  # Last Seen
        
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

    def browse_local_path(self):
        """Browse for local backup directory."""
        directory = QFileDialog.getExistingDirectory(
            self, "Select Backup Directory", "", QFileDialog.Option.ShowDirsOnly
        )
        if directory:
            self.local_path.setText(directory)

    def toggle_auto_refresh(self, state):
        """Toggle automatic refresh of monitoring table."""
        if state == Qt.CheckState.Checked.value:
            self.refresh_timer.start(60000)  # Refresh every 60 seconds
            logging.info("Enabled auto-refresh for monitoring table")
        else:
            self.refresh_timer.stop()
            logging.info("Disabled auto-refresh for monitoring table")

    def clear_monitoring_errors(self):
        """Clear error messages from the monitoring table."""
        try:
            for row in range(self.monitoring_table.rowCount()):
                # Clear the error message cell
                self.monitoring_table.setItem(row, 4, QTableWidgetItem('None'))
                
            self.statusBar().showMessage("Monitoring errors cleared", 2000)
        except Exception as e:
            error_msg = f"Failed to clear monitoring errors: {str(e)}"
            logging.error(error_msg)
            self.show_message_with_copy(
                'Error',
                error_msg,
                QMessageBox.Icon.Critical
            )

    def update_monitoring_table(self):
        """Update the monitoring table with current device status.
        
        This method ensures thread-safety by routing the actual update to the main thread
        if it's called from a non-UI thread.
        """
        # Check if we're on the main thread
        if QThread.currentThread() == QApplication.instance().thread():
            # We're on the main thread, safe to update UI directly
            self._do_update_monitoring_table()
        else:
            # We're not on the main thread, use invokeMethod to safely update UI
            try:
                QMetaObject.invokeMethod(
                    self._do_update_monitoring_table,
                    Qt.ConnectionType.QueuedConnection
                )
            except Exception as e:
                logging.error(f"Error routing monitoring table update to main thread: {str(e)}")

    @pyqtSlot()
    def _do_update_monitoring_table(self):
        """Actual implementation of updating the monitoring table, must be called from the main thread."""
        try:
            self.monitoring_table.setRowCount(len(self.device_manager.devices))
            
            for row, (name, device) in enumerate(self.device_manager.devices.items()):
                # Device info
                self.monitoring_table.setItem(row, 0, QTableWidgetItem(device.name))
                self.monitoring_table.setItem(row, 1, QTableWidgetItem(device.ip_address))
                self.monitoring_table.setItem(row, 2, QTableWidgetItem(device.device_type.value))
                
                # Status with color coding
                status_item = QTableWidgetItem(device.connection_status.value.upper() if hasattr(device.connection_status, 'value') else str(device.connection_status).upper())
                if device.connection_status == ConnectionStatus.CONNECTED:
                    status_item.setForeground(QBrush(QColor('green')))
                elif device.connection_status in [ConnectionStatus.FAILED, ConnectionStatus.DISCONNECTED]:
                    status_item.setForeground(QBrush(QColor('red')))
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

    def update_backup_table_safe(self):
        """Thread-safe wrapper for update_backup_table."""
        self.update_backup_table()
        
    async def _backup_devices(self, devices):
        """Backup multiple devices asynchronously.
        
        Args:
            devices: List of devices to backup
        """
        success_count = 0
        failed_count = 0
        
        for device in devices:
            try:
                # Update UI to show backup in progress for this device
                # Log the operation
                logging.info(f"Starting backup of device {device.name}")
                
                # Start backup operation
                result = await self.backup_manager.backup_device(device)
                
                if result:
                    # Update UI safely through the UI thread, but without using invokeMethod
                    # since we're already handling async operations
                    self.update_backup_table_signal.emit()
                    success_count += 1
                else:
                    self.update_backup_table_signal.emit()
                    failed_count += 1
                    
            except Exception as e:
                logging.error(f"Error backing up device {device.name}: {str(e)}")
                failed_count += 1
        
        # Final UI update
        self.update_backup_table_signal.emit()
        
        # Show summary message
        if failed_count == 0 and success_count > 0:
            # Use signals instead of invokeMethod
            self.backup_success_signal.emit(success_count)
        elif failed_count > 0:
            self.backup_partial_signal.emit(success_count, failed_count)
        
        return success_count, failed_count
    
    # Helper methods for showing backup results
    @pyqtSlot(int)
    def show_backup_success(self, count):
        """Show a success message for backup operations."""
        self.show_message_with_copy(
            'Backup Complete',
            f"Successfully backed up {count} device{'s' if count != 1 else ''}.",
            QMessageBox.Icon.Information
        )
    
    @pyqtSlot(int, int)
    def show_backup_partial(self, success_count, failed_count):
        """Show a partial success message for backup operations."""
        self.show_message_with_copy(
            'Backup Complete',
            f"Completed with {success_count} successful and {failed_count} failed backup{'s' if failed_count != 1 else ''}.\n\nPlease check the log for details.",
            QMessageBox.Icon.Warning
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
                    
                    self.statusBar().showMessage(status_msg, 5000)  # show message for 5 seconds
            else:
                self.statusBar().showMessage("Backup Location: ~/.pulsarnet/backups (Default)", 5000)  # show message for 5 seconds
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
        
    def show_add_device_dialog(self):
        """Show dialog for adding a new device."""
        dialog = DeviceDialog(self, self.device_manager)
        result = dialog.exec()
        
        if result == QDialog.DialogCode.Accepted:
            # Refresh device table
            self.update_device_table()
            self.update_backup_table()
            
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

    def edit_selected_device(self):
        """Edit the selected device."""
        selected_devices = self.get_selected_devices_from_device_table()
        if not selected_devices:
            QMessageBox.warning(self, 'No Device Selected', 'Please select a device to edit by checking the box in the first column.')
            return
            
        # Only edit the first selected device if multiple are selected
        if len(selected_devices) > 1:
            QMessageBox.information(self, 'Multiple Devices Selected', 'Multiple devices selected. Only the first device will be edited.')
            
        device = selected_devices[0]
        self.show_edit_device_dialog(device)

    def show_device_context_menu(self, pos):
        """Show context menu for device table."""
        menu = QMenu(self)
        
        # Check if there are any devices with checkboxes checked
        selected_devices = self.get_selected_devices_from_device_table()
        has_selection = len(selected_devices) > 0
        
        # Only enable edit if exactly one device is selected
        edit_action = menu.addAction("Edit Device")
        edit_action.triggered.connect(self.edit_selected_device)
        edit_action.setEnabled(has_selection)
        
        # Enable remove if at least one device is selected
        remove_action = menu.addAction("Remove Device")
        remove_action.triggered.connect(self.remove_selected_device)
        remove_action.setEnabled(has_selection)
        
        # Add separator and other actions
        menu.addSeparator()
        
        test_action = menu.addAction("Test Connection")
        test_action.triggered.connect(self.test_selected_device_connection)
        test_action.setEnabled(has_selection)
        
        # Show context menu at cursor position
        menu.exec(self.device_table.mapToGlobal(pos))

    # Thread-safe method for updating connection status
    @pyqtSlot(int, str, bool, str)
    def update_connection_status(self, row, device_name, success, message):
        """Update the connection status in the device table from any thread."""
        try:
            if not self.device_table or row >= self.device_table.rowCount():
                return
                
            status_item = self.device_table.item(row, 8)
            if status_item:
                if success:
                    status_item.setText("Connected")
                    status_item.setForeground(QBrush(QColor('green')))
                else:
                    status_item.setText("Failed")
                    status_item.setForeground(QBrush(QColor('red')))
                    
                # Set tooltip with detailed message
                status_item.setToolTip(message)
                
                # Show message with result
                icon = QMessageBox.Icon.Information if success else QMessageBox.Icon.Warning
                self.show_message_with_copy(
                    'Connection Test',
                    f"Connection test for {device_name}: {message}",
                    icon
                )
        except Exception as e:
            logging.error(f"Error updating connection status: {str(e)}")

    def test_selected_device_connection(self):
        """Test connection to the selected device."""
        # Get selected devices
        selected_devices = self.get_selected_devices_from_device_table()
        
        if not selected_devices:
            QMessageBox.warning(self, 'No Device Selected', 'Please select a device to test by checking the box.')
            return
            
        # Test connection for each selected device
        for device in selected_devices:
            QMessageBox.information(self, 'Connection Test', 
                                  f'Connection test for {device.name} would be performed here.')
            
    def get_selected_devices_from_device_table(self):
        """Get list of selected devices from device table."""
        selected_devices = []
        for row in range(self.device_table.rowCount()):
            checkbox = self.device_table.item(row, 0)
            if checkbox and checkbox.checkState() == Qt.CheckState.Checked:
                device_name = self.device_table.item(row, 1).text()
                if device_name in self.device_manager.devices:
                    selected_devices.append(self.device_manager.devices[device_name])
        return selected_devices

    def show_edit_device_dialog(self, device):
        """Show dialog for editing an existing device.
        
        Args:
            device: The Device object to edit
        """
        dialog = DeviceDialog(self, self.device_manager, device)
        result = dialog.exec()
        
        if result == QDialog.DialogCode.Accepted:
            # Refresh device table
            self.update_device_table()
            self.update_backup_table()

    def edit_selected_group(self):
        """Edit the selected group."""
        if not hasattr(self, 'groups_table'):
            return
            
        try:
            # Get selected groups (checkboxes)
            selected_groups = []
            for row in range(self.groups_table.rowCount()):
                checkbox = self.groups_table.item(row, 0)
                if checkbox and checkbox.checkState() == Qt.CheckState.Checked:
                    group_name = self.groups_table.item(row, 1).text()
                    selected_groups.append(group_name)
            
            # If no checkboxes are checked, try to use the current selection
            if not selected_groups:
                selected_rows = self.groups_table.selectionModel().selectedRows()
                if not selected_rows:
                    # If no row is selected by row index, check if a cell is selected
                    selected_items = self.groups_table.selectedItems()
                    if selected_items:
                        # Get the row of the first selected item
                        selected_rows = [selected_items[0].row()]
                
                if selected_rows:
                    row = selected_rows[0].row() if hasattr(selected_rows[0], 'row') else selected_rows[0]
                    group_name_item = self.groups_table.item(row, 1)
                    if group_name_item:
                        group_name = group_name_item.text()
                        selected_groups.append(group_name)
            
            if not selected_groups:
                QMessageBox.warning(self, 'No Group Selected', 'Please select a group to edit by checking the box or selecting a row.')
                return
                
            # Only edit the first selected group if multiple are selected
            if len(selected_groups) > 1:
                QMessageBox.information(self, 'Multiple Groups Selected', 'Multiple groups selected. Only the first group will be edited.')
                
            group = self.device_manager.groups[selected_groups[0]]
            self.show_edit_group_dialog(group)
            
            # Update the UI after editing
            self.update_groups_table()
            self.on_group_selection_changed()
            
        except Exception as e:
            error_msg = f"Error editing group: {str(e)}"
            logging.error(error_msg)
            self.show_message_with_copy(
                'Group Edit Error',
                error_msg,
                QMessageBox.Icon.Critical
            )

    def edit_selected_group_from_dialog(self):
        """Edit a group selected in the schedule dialog."""
        sender = self.sender()
        parent_dialog = sender.window()
        
        # Find the checked group from the dialog
        checked_groups = []
        for widget in parent_dialog.findChildren(QCheckBox):
            if widget.isChecked() and widget.text() in self.device_manager.groups:
                checked_groups.append(widget.text())
        
        if len(checked_groups) != 1:
            QMessageBox.warning(parent_dialog, "Selection Error", 
                               "Please select exactly one group to edit.")
            return
            
        group_name = checked_groups[0]
        group = self.device_manager.groups.get(group_name)
        
        if group:
            self.show_edit_group_dialog(group)
            
            # Update the group list in the dialog after edit
            parent_dialog.accept()
            self.show_add_schedule_dialog()
        else:
            QMessageBox.warning(parent_dialog, "Group Error", 
                               f"Group '{group_name}' not found.")

    def delete_selected_group_from_dialog(self):
        """Delete a group selected in the schedule dialog."""
        sender = self.sender()
        parent_dialog = sender.window()
        
        # Find the checked group from the dialog
        checked_groups = []
        for widget in parent_dialog.findChildren(QCheckBox):
            if widget.isChecked() and widget.text() in self.device_manager.groups:
                checked_groups.append(widget.text())
        
        if not checked_groups:
            QMessageBox.warning(parent_dialog, "Selection Error", 
                               "Please select at least one group to delete.")
            return
            
        # Confirm deletion
        if QMessageBox.question(
            parent_dialog,
            "Confirm Deletion",
            f"Are you sure you want to delete {len(checked_groups)} group(s)?\n\n"
            "This action cannot be undone.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        ) != QMessageBox.StandardButton.Yes:
            return
            
        # Delete each selected group
        for group_name in checked_groups:
            if group_name in self.device_manager.groups:
                del self.device_manager.groups[group_name]
                
        # Save changes to disk
        self.device_manager.save_groups()
        
        # Update the UI
        self.update_device_table()
        
        # Close the current dialog and reopen it to refresh
        parent_dialog.accept()
        self.show_add_schedule_dialog()

    def remove_selected_group(self):
        """Remove the selected group."""
        if not hasattr(self, 'groups_table'):
            return
            
        # Use our modular GroupManager class
        if self.group_manager.remove_groups(self.groups_table):
            # Update the UI if removal was successful
            self.update_groups_table()
            self.group_members_table.setRowCount(0)  # Clear members table

    def get_devices_from_groups(self, group_names):
        """Get device names from specified groups.
        
        Args:
            group_names: List of group names to get devices from.
            
        Returns:
            List of device names that belong to the specified groups.
        """
        all_devices = set()
        for group_name in group_names:
            if group_name in self.device_manager.groups:
                group = self.device_manager.groups[group_name]
                all_devices.update(group.members)
            else:
                logging.warning(f"Group not found: {group_name}")
        
        return list(all_devices)

    def show_add_group_dialog(self):
        """Show dialog for creating a new device group."""
        try:
            dialog = GroupDialog(self, self.device_manager)
            result = dialog.exec()
            
            if result == QDialog.DialogCode.Accepted:
                new_group = dialog.get_group()
                if new_group:
                    # Add group to device manager
                    self.device_manager.groups[new_group.name] = new_group
                    # Save groups to disk
                    self.device_manager.save_groups()
                    
                    # Refresh UI
                    self.update_device_table()
                    self.update_groups_table()
                    self.update_backup_table()
                    
                    QMessageBox.information(
                        self,
                        'Group Created',
                        f'Group "{new_group.name}" created successfully with {len(new_group.members)} device(s).',
                        QMessageBox.StandardButton.Ok
                    )
        except Exception as e:
            error_msg = f"Error creating group: {str(e)}"
            logging.error(error_msg)
            self.show_message_with_copy(
                'Group Creation Error',
                error_msg,
                QMessageBox.Icon.Critical
            )

    def show_edit_group_dialog(self, group):
        """Show dialog for editing an existing device group.
        
        Args:
            group: The DeviceGroup object to edit
        """
        try:
            dialog = GroupDialog(self, self.device_manager, group)
            result = dialog.exec()
            
            if result == QDialog.DialogCode.Accepted:
                updated_group = dialog.get_group()
                if updated_group:
                    # Update group in device manager
                    self.device_manager.groups[updated_group.name] = updated_group
                    # Save groups to disk
                    self.device_manager.save_groups()
                    
                    # Refresh UI
                    self.update_device_table()
                    self.update_groups_table()
                    self.update_backup_table()
                    
                    QMessageBox.information(
                        self,
                        'Group Updated',
                        f'Group "{updated_group.name}" updated successfully with {len(updated_group.members)} device(s).',
                        QMessageBox.StandardButton.Ok
                    )
        except Exception as e:
            error_msg = f"Error updating group: {str(e)}"
            logging.error(error_msg)
            self.show_message_with_copy(
                'Group Update Error',
                error_msg,
                QMessageBox.Icon.Critical
            )

    def update_groups_table(self):
        """Update the groups table with current groups."""
        if not hasattr(self, 'groups_table'):
            logging.warning("Cannot update groups table: groups_table not found")
            return
            
        # Remember checked groups before clearing
        checked_groups = []
        for row in range(self.groups_table.rowCount()):
            item = self.groups_table.item(row, 0)
            if item and item.checkState() == Qt.CheckState.Checked:
                group_name_item = self.groups_table.item(row, 1)
                if group_name_item:
                    checked_groups.append(group_name_item.text())
        
        # Save current selection
        selected_rows = self.groups_table.selectionModel().selectedRows()
        current_selection = None
        if selected_rows:
            row = selected_rows[0].row()
            group_name_item = self.groups_table.item(row, 1)
            if group_name_item:
                current_selection = group_name_item.text()
                
        logging.debug(f"Updating groups table: {len(self.device_manager.groups)} groups found")
        logging.debug(f"Current checked groups: {checked_groups}")
        logging.debug(f"Current selection: {current_selection}")
            
        try:
            # Block signals temporarily to prevent triggering selection events during update
            self.groups_table.blockSignals(True)
            
            # Clear the table
            self.groups_table.setRowCount(0)
            
            # Add current groups
            for row, (group_name, group) in enumerate(self.device_manager.groups.items()):
                self.groups_table.insertRow(row)
                
                # Create a checkbox for selection
                checkbox = QTableWidgetItem()
                checkbox.setFlags(Qt.ItemFlag.ItemIsUserCheckable | Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsSelectable)
                # Restore checked state if it was checked before
                if group_name in checked_groups:
                    checkbox.setCheckState(Qt.CheckState.Checked)
                else:
                    checkbox.setCheckState(Qt.CheckState.Unchecked)
                
                self.groups_table.setItem(row, 0, checkbox)
                
                # Set group information
                self.groups_table.setItem(row, 1, QTableWidgetItem(group_name))
                self.groups_table.setItem(row, 2, QTableWidgetItem(group.description))
                
                # Get device count
                device_count = len(group.members)
                count_item = QTableWidgetItem(str(device_count))
                count_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                self.groups_table.setItem(row, 3, count_item)
                
                # Restore selection if this was the previously selected row
                if group_name == current_selection:
                    self.groups_table.selectRow(row)
            
            # Adjust column widths
            self.groups_table.resizeColumnsToContents()
            
            # Ensure that the selection column is a reasonable width
            selection_width = max(50, self.groups_table.columnWidth(0))
            self.groups_table.setColumnWidth(0, selection_width)
            
        except Exception as e:
            error_msg = f"Error updating groups table: {str(e)}"
            logging.error(error_msg)
            # Don't show error to user for this minor issue
        finally:
            # Unblock signals
            self.groups_table.blockSignals(False)
            
        # Now check if we need to trigger selection update for checked items
        has_checked = False
        for row in range(self.groups_table.rowCount()):
            item = self.groups_table.item(row, 0)
            if item and item.checkState() == Qt.CheckState.Checked:
                has_checked = True
                break
                
        # Force an update of the group members table
        if has_checked or current_selection:
            logging.debug("Triggering group selection update after table refresh")
            self.on_group_selection_changed()

    def on_group_selection_changed(self):
        """Update the group members table when a group is selected."""
        if not hasattr(self, 'groups_table') or not hasattr(self, 'group_members_table'):
            return
            
        try:
            logging.debug("\n--- Group Selection Changed ---")
            # Clear the members table
            self.group_members_table.setRowCount(0)
            
            # Get the group name three ways:
            # 1. Check selected rows
            # 2. Check checkboxes
            # 3. Check any selected items
            group_name = None
            
            # Method 1: Check selection model
            selected_indexes = self.groups_table.selectionModel().selectedRows()
            logging.debug(f"Selected rows: {len(selected_indexes)}")
            if selected_indexes:
                row = selected_indexes[0].row()
                group_name_item = self.groups_table.item(row, 1)
                if group_name_item:
                    group_name = group_name_item.text()
                    logging.debug(f"Group selected by row: {group_name}")
            
            # Method 2: Check checkboxes if no selection found
            if not group_name:
                logging.debug("No group selected by row, checking checkboxes")
                for row in range(self.groups_table.rowCount()):
                    # Check QTableWidgetItem checkbox
                    checkbox = self.groups_table.item(row, 0)
                    if checkbox:
                        logging.debug(f"Row {row} checkbox state: {checkbox.checkState()}")
                    if checkbox and checkbox.checkState() == Qt.CheckState.Checked:
                        group_name_item = self.groups_table.item(row, 1)
                        if group_name_item:
                            group_name = group_name_item.text()
                            logging.debug(f"Found checked group: {group_name}")
                            break
                    
                    # Also check for QCheckBox widgets
                    cell_widget = self.groups_table.cellWidget(row, 0)
                    if isinstance(cell_widget, QCheckBox):
                        logging.debug(f"Row {row} QCheckBox checked: {cell_widget.isChecked()}")
                    if isinstance(cell_widget, QCheckBox) and cell_widget.isChecked():
                        group_name_item = self.groups_table.item(row, 1)
                        if group_name_item:
                            group_name = group_name_item.text()
                            logging.debug(f"Found checked group via widget: {group_name}")
                            break
            
            # Method 3: Check for any selected items if still no group found
            if not group_name:
                logging.debug("Checking selected items")
                selected_items = self.groups_table.selectedItems()
                logging.debug(f"Selected items: {len(selected_items)}")
                if selected_items:
                    row = selected_items[0].row()
                    group_name_item = self.groups_table.item(row, 1)
                    if group_name_item:
                        group_name = group_name_item.text()
                        logging.debug(f"Group selected by item: {group_name}")
            
            # If no group name found or group doesn't exist, return
            logging.debug(f"Final group name: {group_name}")
            if not group_name or group_name not in self.device_manager.groups:
                logging.debug(f"Group not found in device manager groups: {list(self.device_manager.groups.keys())}")
                return
                
            group = self.device_manager.groups[group_name]
            logging.debug(f"Updating members table for group: {group_name} with {len(group.members)} members")
            logging.debug(f"Group members: {group.members}")
            
            # Add devices from the group to the members table
            # Check if members is a list of Device objects or a list of device names
            for row, member in enumerate(group.members):
                # Handle case where member is a Device object directly
                if hasattr(member, 'name') and hasattr(member, 'ip_address'):
                    device = member
                # Handle case where member is a string (device name)
                elif isinstance(member, str) and member in self.device_manager.devices:
                    device = self.device_manager.devices[member]
                else:
                    logging.debug(f"Skipping invalid member: {member}")
                    continue
                
                try:
                    self.group_members_table.insertRow(row)
                    
                    # Set device information
                    self.group_members_table.setItem(row, 0, QTableWidgetItem(device.name))
                    self.group_members_table.setItem(row, 1, QTableWidgetItem(device.ip_address))
                    
                    # Status with color coding
                    if hasattr(device, 'connection_status'):
                        if hasattr(device.connection_status, 'value'):
                            status_text = device.connection_status.value
                        else:
                            status_text = str(device.connection_status)
                    else:
                        status_text = "Unknown"
                        
                    status_item = QTableWidgetItem(status_text)
                    
                    if status_text == 'Connected':
                        status_item.setForeground(QBrush(QColor('green')))
                    elif status_text in ['Error', 'Failed', 'Timeout', 'Disconnected']:
                        status_item.setForeground(QBrush(QColor('red')))
                    else:
                        status_item.setForeground(QBrush(QColor('orange')))
                    
                    self.group_members_table.setItem(row, 2, status_item)
                except Exception as inner_e:
                    logging.debug(f"Error adding device to table: {str(inner_e)}")
                    continue
            
            # Adjust column widths
            self.group_members_table.resizeColumnsToContents()
            
        except Exception as e:
            error_msg = f"Error updating group members: {str(e)}"
            logging.error(error_msg)
            # Don't show error message to user for this minor issue

    def show_group_context_menu(self, pos):
        """Show context menu for group table."""
        menu = QMenu(self)
        
        # Get the selected group row
        selected_rows = self.groups_table.selectionModel().selectedRows()
        if not selected_rows:
            # If no row is selected by row index, check if a cell is selected
            selected_items = self.groups_table.selectedItems()
            if selected_items:
                # Get the row of the first selected item
                selected_rows = [selected_items[0].row()]
        
        has_selection = len(selected_rows) > 0
        
        # Actions for selected group
        edit_action = menu.addAction("Edit Group")
        edit_action.triggered.connect(self.edit_selected_group)
        edit_action.setEnabled(has_selection)
        
        remove_action = menu.addAction("Remove Group")
        remove_action.triggered.connect(self.remove_selected_group)
        remove_action.setEnabled(has_selection)
        
        menu.addSeparator()
        
        backup_action = menu.addAction("Backup All Devices in Group")
        backup_action.triggered.connect(self.backup_selected_group)
        backup_action.setEnabled(has_selection)
        
        add_to_schedule_action = menu.addAction("Add to Backup Schedule")
        add_to_schedule_action.triggered.connect(self.schedule_selected_group)
        add_to_schedule_action.setEnabled(has_selection)
        
        # Show context menu at cursor position
        menu.exec(self.groups_table.mapToGlobal(pos))

    def add_device_to_selected_group(self):
        """Add devices to the selected group."""
        if not hasattr(self, 'groups_table'):
            return
            
        # Get the selected group
        selected_indexes = self.groups_table.selectionModel().selectedRows()
        if not selected_indexes:
            QMessageBox.warning(self, 'No Group Selected', 'Please select a group to add devices to.')
            return
        
        # Get the group name from the selected row
        row = selected_indexes[0].row()
        group_name_item = self.groups_table.item(row, 1)
        if not group_name_item:
            return
            
        group_name = group_name_item.text()
        if group_name not in self.device_manager.groups:
            return
            
        # Create dialog to select devices
        dialog = QDialog(self)
        dialog.setWindowTitle(f'Add Devices to Group: {group_name}')
        dialog.setMinimumWidth(400)
        
        layout = QVBoxLayout()
        
        # Create list of devices with checkboxes
        device_list = QListWidget()
        
        # Get current members of the group
        current_members = self.device_manager.groups[group_name].members
        
        # Add all devices from device manager
        for device_name, device in sorted(self.device_manager.devices.items()):
            item = QListWidgetItem(device_name)
            item.setFlags(item.flags() | Qt.ItemFlag.ItemIsUserCheckable)
            # Pre-check if device is already in the group
            if device_name in current_members:
                item.setCheckState(Qt.CheckState.Checked)
            else:
                item.setCheckState(Qt.CheckState.Unchecked)
            device_list.addItem(item)
        
        layout.addWidget(device_list)
        
        # Add buttons
        button_layout = QHBoxLayout()
        select_all_btn = QPushButton('Select All')
        select_all_btn.clicked.connect(lambda: self.select_all_list_items(device_list))
        
        clear_all_btn = QPushButton('Clear All')
        clear_all_btn.clicked.connect(lambda: self.clear_all_list_items(device_list))
        
        button_layout.addWidget(select_all_btn)
        button_layout.addWidget(clear_all_btn)
        layout.addLayout(button_layout)
        
        # Dialog buttons
        dialog_buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        dialog_buttons.accepted.connect(dialog.accept)
        dialog_buttons.rejected.connect(dialog.reject)
        layout.addWidget(dialog_buttons)
        
        dialog.setLayout(layout)
        
        # Show dialog
        if dialog.exec() == QDialog.DialogCode.Accepted:
            # Update group members
            selected_devices = []
            for i in range(device_list.count()):
                item = device_list.item(i)
                if item.checkState() == Qt.CheckState.Checked:
                    selected_devices.append(item.text())
            
            # Update the group
            self.device_manager.groups[group_name].members = selected_devices
            self.device_manager.save_groups()
            
            # Update UI
            self.update_groups_table()
            self.on_group_selection_changed()
            
            QMessageBox.information(
                self,
                'Group Updated',
                f'Group {group_name} updated with {len(selected_devices)} device(s).',
                QMessageBox.StandardButton.Ok
            )

    def select_all_list_items(self, list_widget):
        """Select all items in a list widget."""
        for i in range(list_widget.count()):
            item = list_widget.item(i)
            item.setCheckState(Qt.CheckState.Checked)
    
    def clear_all_list_items(self, list_widget):
        """Clear all selections in a list widget."""
        for i in range(list_widget.count()):
            item = list_widget.item(i)
            item.setCheckState(Qt.CheckState.Unchecked)

    def remove_device_from_selected_group(self):
        """Remove devices from the selected group."""
        if not hasattr(self, 'groups_table') or not hasattr(self, 'group_members_table'):
            return
            
        # Get the selected group (three ways to check):
        # 1. Check selection model
        # 2. Check checkboxes
        # 3. Check any selected items
        group_name = None
        
        # Method 1: Check selection model
        selected_indexes = self.groups_table.selectionModel().selectedRows()
        if selected_indexes:
            row = selected_indexes[0].row()
            group_name_item = self.groups_table.item(row, 1)
            if group_name_item:
                group_name = group_name_item.text()
        
        # Method 2: Check checkboxes if no selection found
        if not group_name:
            for row in range(self.groups_table.rowCount()):
                checkbox = self.groups_table.item(row, 0)
                if checkbox and checkbox.checkState() == Qt.CheckState.Checked:
                    group_name_item = self.groups_table.item(row, 1)
                    if group_name_item:
                        group_name = group_name_item.text()
                        break
                
                # Also check for QCheckBox widgets
                cell_widget = self.groups_table.cellWidget(row, 0)
                if isinstance(cell_widget, QCheckBox) and cell_widget.isChecked():
                    group_name_item = self.groups_table.item(row, 1)
                    if group_name_item:
                        group_name = group_name_item.text()
                        break
        
        # Method 3: Check for any selected items
        if not group_name:
            selected_items = self.groups_table.selectedItems()
            if selected_items:
                row = selected_items[0].row()
                group_name_item = self.groups_table.item(row, 1)
                if group_name_item:
                    group_name = group_name_item.text()
        
        # If still no group selected, show warning
        if not group_name or group_name not in self.device_manager.groups:
            QMessageBox.warning(self, 'No Group Selected', 'Please select a group to remove devices from.')
            return
        
        # Get selected devices from group members table
        selected_devices = []
        for row in range(self.group_members_table.rowCount()):
            if self.group_members_table.isItemSelected(self.group_members_table.item(row, 0)):
                device_name = self.group_members_table.item(row, 0).text()
                selected_devices.append(device_name)
        
        if not selected_devices:
            QMessageBox.warning(self, 'No Devices Selected', 'Please select at least one device to remove from the group.')
            return
        
        # Confirm with user
        confirm = QMessageBox.question(
            self,
            'Confirm Removal',
            f'Are you sure you want to remove {len(selected_devices)} device(s) from group "{group_name}"?',
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if confirm == QMessageBox.StandardButton.Yes:
            # Remove selected devices from the group
            group = self.device_manager.groups[group_name]
            for device_name in selected_devices:
                if device_name in group.members:
                    group.members.remove(device_name)
                    
            self.device_manager.save_groups()
            self.on_group_selection_changed()  # Refresh the group members view
            
            QMessageBox.information(
                self,
                'Removal Complete',
                f'Successfully removed {len(selected_devices)} device(s) from group "{group_name}".',
                QMessageBox.StandardButton.Ok
            )

    def backup_selected_group(self):
        """Backup all devices in the selected group using improved selection logic."""
        if not hasattr(self, 'groups_table'):
            return
            
        # Get the selected group (three ways to check):
        # 1. Check selection model
        # 2. Check checkboxes
        # 3. Check any selected items
        group_name = None
        
        # Method 1: Check selection model
        selected_indexes = self.groups_table.selectionModel().selectedRows()
        if selected_indexes:
            row = selected_indexes[0].row()
            group_name_item = self.groups_table.item(row, 1)
            if group_name_item:
                group_name = group_name_item.text()
        
        # Method 2: Check checkboxes if no selection found
        if not group_name:
            for row in range(self.groups_table.rowCount()):
                checkbox = self.groups_table.item(row, 0)
                if checkbox and checkbox.checkState() == Qt.CheckState.Checked:
                    group_name_item = self.groups_table.item(row, 1)
                    if group_name_item:
                        group_name = group_name_item.text()
                        break
                
                # Also check for QCheckBox widgets
                cell_widget = self.groups_table.cellWidget(row, 0)
                if isinstance(cell_widget, QCheckBox) and cell_widget.isChecked():
                    group_name_item = self.groups_table.item(row, 1)
                    if group_name_item:
                        group_name = group_name_item.text()
                        break
        
        # Method 3: Check for any selected items
        if not group_name:
            selected_items = self.groups_table.selectedItems()
            if selected_items:
                row = selected_items[0].row()
                group_name_item = self.groups_table.item(row, 1)
                if group_name_item:
                    group_name = group_name_item.text()
        
        # If still no group selected, show warning
        if not group_name or group_name not in self.device_manager.groups:
            QMessageBox.warning(self, "No Group Selected", "Please select a group to backup.")
            return
        
        # Get the devices from the group
        group = self.device_manager.groups[group_name]
        devices = group.get_devices()
        
        if not devices:
            QMessageBox.warning(self, "No Devices", f"Group '{group_name}' does not contain any devices.")
            return
        
        # Confirm with user
        confirm = QMessageBox.question(
            self,
            'Confirm Backup',
            f'Are you sure you want to backup all devices ({len(devices)}) in group "{group_name}"?',
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if confirm == QMessageBox.StandardButton.Yes:
            # Start backup process
            self.start_backup(devices)

    def start_backup(self, devices=None):
        """Start backup process for selected devices or provided device list.
        
        Args:
            devices: Optional list of devices or device names to backup. If None,
                    will use selected devices from the backup table.
        """
        try:
            # If no devices provided, get selected from backup table
            if devices is None:
                selected_devices = []
                for row in range(self.backup_table.rowCount()):
                    # Check for QCheckBox widget (used in backup_table)
                    cell_widget = self.backup_table.cellWidget(row, 0)
                    if isinstance(cell_widget, QCheckBox) and cell_widget.isChecked():
                        device_name = self.backup_table.item(row, 1).text()
                        if device_name in self.device_manager.devices:
                            selected_devices.append(self.device_manager.devices[device_name])
                    
                    # Also check for QTableWidgetItem checkboxes
                    checkbox_item = self.backup_table.item(row, 0)
                    if checkbox_item and checkbox_item.checkState() == Qt.CheckState.Checked:
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
                
                devices = selected_devices
            
            # Convert device names to Device objects if needed
            device_objects = []
            if devices:
                for device in devices:
                    if isinstance(device, str):
                        if device in self.device_manager.devices:
                            device_objects.append(self.device_manager.devices[device])
                        else:
                            logging.warning(f"Device not found: {device}")
                    else:
                        device_objects.append(device)
            
            if not device_objects:
                logging.warning("No valid devices found for backup")
                return
            
            # Start the event loop if it's not running
            if not self.loop.is_running():
                # Create a new thread to run the event loop
                def run_loop():
                    asyncio.set_event_loop(self.loop)
                    self.loop.run_forever()
                
                loop_thread = threading.Thread(target=run_loop, daemon=True)
                loop_thread.start()
            
            # Schedule the backup operation
            future = asyncio.run_coroutine_threadsafe(
                self._backup_devices(device_objects), 
                self.loop
            )
            
            # Optional: Add a callback to handle completion
            def backup_done(future):
                try:
                    future.result()  # This will raise any exceptions from the coroutine
                except Exception as e:
                    logging.error(f"Backup operation failed: {str(e)}")
                    # Show error to user via signal
                    self.show_message_signal.emit(
                        'Backup Failed',
                        f"Backup operation failed: {str(e)}",
                        QMessageBox.Icon.Critical
                    )
            
            future.add_done_callback(backup_done)
            
        except Exception as e:
            error_msg = f"Error starting backup: {str(e)}"
            logging.error(error_msg)
            self.show_message_with_copy(
                'Backup Error',
                error_msg,
                QMessageBox.Icon.Critical
            )

    def start_backup_filtered(self):
        """Start backup based on the selected filter."""
        filter_option = self.backup_filter_combo.currentText()
        devices = []
        if filter_option == "All Devices":
            devices = list(self.device_manager.devices.values())
        elif filter_option == "By Group":
            group_name = self.backup_group_combo.currentText()
            if group_name == "Select Group":
                QMessageBox.warning(self, "No Group Selected", "Please select a group to backup.")
                return
            if group_name in self.device_manager.groups:
                devices = self.device_manager.groups[group_name].members
            else:
                QMessageBox.warning(self, "Invalid Group", "Selected group does not exist.")
                return
        elif filter_option == "By Device":
            selected_indexes = self.backup_table.selectionModel().selectedRows()
            for index in selected_indexes:
                device_name = self.backup_table.item(index.row(), 1).text()
                if device_name in self.device_manager.devices:
                    devices.append(self.device_manager.devices[device_name])
            if not devices:
                QMessageBox.warning(self, "No Devices Selected", "Please select at least one device for backup.")
                return
        else:
            devices = []

        if not devices:
            logging.warning("No valid devices found for backup")
            return
        self.start_backup(devices)

    def check_schedules(self):
        """Check for schedules due to run and execute them."""
        try:
            # Get all due schedules
            due_schedules = self.schedule_manager.get_due_schedules()
            
            if due_schedules:
                for schedule in due_schedules:
                    # Update the last run time
                    self.schedule_manager.update_schedule_time(schedule.name)
                    
                    # Check the target type and handle accordingly
                    if schedule.target_type == TargetType.GROUP:
                        # Get all devices from the specified groups
                        devices_to_backup = []
                        for group_name in schedule.groups:
                            if group_name in self.device_manager.groups:
                                group = self.device_manager.groups[group_name]
                                # Add devices from this group
                                for member in group.members:
                                    if hasattr(member, 'name'):
                                        devices_to_backup.append(member)
                                    elif isinstance(member, str) and member in self.device_manager.devices:
                                        devices_to_backup.append(self.device_manager.devices[member])
                        
                        if devices_to_backup:
                            logging.info(f"Starting backup for {len(devices_to_backup)} device(s) from groups: {', '.join(schedule.groups)}")
                            # Start backup for devices
                            self.start_backup(devices_to_backup)
                        else:
                            logging.warning(f"No valid devices found in groups: {', '.join(schedule.groups)}")
                    else:
                        # Handle device schedules
                        device_names = schedule.devices
                        logging.info(f"Starting backup for scheduled devices: {', '.join(device_names)}")
                        # Get device objects from names
                        devices = [self.device_manager.devices[name] for name in device_names 
                                  if name in self.device_manager.devices]
                        
                        # Start backup for devices
                        if devices:
                            self.start_backup(devices)
                
                # Update the scheduler table if the view exists and is initialized
                if hasattr(self, 'scheduler_controller'):
                    self.scheduler_controller.update_scheduler_table()
        except Exception as e:
            logging.error(f"Error checking schedules: {str(e)}")
            self.show_message_with_copy(
                'Schedule Error',
                f"An error occurred while checking schedules: {str(e)}",
                QMessageBox.Icon.Critical
            )

    def remove_selected_device(self):
        """Remove the selected device(s) from the device manager."""
        # Get selected devices
        selected_devices = self.get_selected_devices_from_device_table()
        
        if not selected_devices:
            QMessageBox.warning(self, 'No Device Selected', 'Please select at least one device to remove by checking the box.')
            return
            
        # Confirm deletion
        if QMessageBox.question(
            self,
            "Confirm Device Deletion",
            f"Are you sure you want to delete {len(selected_devices)} device(s)?\n\n"
            "This action cannot be undone.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        ) != QMessageBox.StandardButton.Yes:
            return
            
        # Remove devices
        for device in selected_devices:
            if device.name in self.device_manager.devices:
                del self.device_manager.devices[device.name]
                
        # Save changes
        self.device_manager.save_devices()
        
        # Update UI
        self.update_device_table()
        self.update_backup_table()
        
        QMessageBox.information(
            self,
            'Devices Removed',
            f"{len(selected_devices)} device(s) have been removed.",
            QMessageBox.StandardButton.Ok
        )
        
    def upload_config(self):
        """Export selected devices to CSV file."""
        # Get selected devices
        selected_devices = self.get_selected_devices_from_device_table()
        
        if not selected_devices:
            QMessageBox.warning(self, 'No Device Selected', 'Please select at least one device to export.')
            return
            
        # Show file dialog to choose save location
        file_path, _ = QFileDialog.getSaveFileName(
            self, 'Export Devices', '', 'CSV Files (*.csv)'
        )
        
        if not file_path:
            return  # User cancelled
            
        # Add .csv extension if not present
        if not file_path.lower().endswith('.csv'):
            file_path += '.csv'
            
        try:
            # Create CSV with device data
            with open(file_path, 'w', newline='') as f:
                writer = csv.writer(f)
                
                # Write header
                writer.writerow([
                    'name', 'ip_address', 'device_type', 'username', 'connection_type',
                    'port', 'jump_server', 'jump_username', 'jump_port'
                ])
                
                # Write device data
                for device in selected_devices:
                    writer.writerow([
                        device.name,
                        device.ip_address,
                        device.device_type.value if hasattr(device.device_type, 'value') else str(device.device_type),
                        device.username,
                        device.connection_type if hasattr(device, 'connection_type') else 'direct',
                        device.port if hasattr(device, 'port') else 22,
                        device.jump_server if hasattr(device, 'jump_server') else '',
                        device.jump_username if hasattr(device, 'jump_username') else '',
                        device.jump_port if hasattr(device, 'jump_port') else ''
                    ])
                    
            QMessageBox.information(
                self,
                'Export Complete',
                f'Successfully exported {len(selected_devices)} device(s) to {file_path}',
                QMessageBox.StandardButton.Ok
            )
            
        except Exception as e:
            error_msg = f"Failed to export devices: {str(e)}"
            logging.error(error_msg)
            self.show_message_with_copy(
                'Export Error',
                error_msg,
                QMessageBox.Icon.Critical
            )

    def refresh_device_status(self):
        """Refresh the connection status of all devices with recursion guard."""
        if getattr(self, '_refreshing', False):
            return
        
        self._refreshing = True
        try:
            if hasattr(self, 'device_table'):
                # Update the UI to show we're refreshing
                self.statusBar().showMessage("Refreshing device status...", 2000)
                
                # In a real implementation, this would check each device's connection
                # For now, we'll just update the display
                self.update_device_table()
                
                QMessageBox.information(
                    self,
                    'Refresh Complete',
                    'Device status refresh complete.',
                    QMessageBox.StandardButton.Ok
                )
        except Exception as e:
            error_msg = f"Failed to refresh device status: {str(e)}"
            logging.error(error_msg)
            self.show_message_with_copy(
                'Refresh Error',
                error_msg,
                QMessageBox.Icon.Critical
            )
        finally:
            self._refreshing = False

    def on_backup_filter_changed(self, text):
        """Handle backup filter type selection change."""
        # Show/hide UI elements based on filter type
        is_group_filter = (text == "By Group")
        
        # Update the UI based on filter selection
        self.backup_group_combo.setEnabled(is_group_filter)
        
        # Reset UI elements that aren't applicable
        if not is_group_filter:
            self.backup_group_combo.setCurrentText("Select Group")
            
        # Show all devices if "All Devices" is selected
        if text == "All Devices":
            self.backup_status_label.setText(f"Showing all {len(self.device_manager.devices)} devices")
            # Apply the filter immediately
            self.apply_backup_filter()
            
        # Update the backup status for clarity
        if text == "By Group" and self.backup_group_combo.currentText() == "Select Group":
            self.backup_status_label.setText("Please select a group")
            # Clear the table until a group is selected
            self.backup_table.setRowCount(0)

    def on_backup_group_changed(self, group_name):
        """Handle backup group selection change."""
        if group_name != "Select Group":
            # Count how many devices are in this group
            if group_name in self.device_manager.groups:
                group = self.device_manager.groups[group_name]
                device_count = len(group.members)
                self.backup_status_label.setText(f"Showing {device_count} devices from group '{group_name}'")
                
                # Automatically apply the filter
                self.apply_backup_filter()
            else:
                self.backup_status_label.setText(f"Group '{group_name}' not found")
        else:
            self.backup_status_label.setText("No group selected")
    
    def on_backup_device_type_changed(self, device_type):
        """Handle backup device type selection change."""
        if device_type != "Select Device Type":
            # Count devices of this type
            count = 0
            for device in self.device_manager.devices.values():
                current_type = str(device.device_type)
                if current_type == device_type:
                    count += 1

            self.backup_status_label.setText(f"Showing {count} devices of type '{device_type}'")
            
            # Automatically apply the filter
            self.apply_backup_filter()
        else:
            self.backup_status_label.setText("No device type selected")
    
    def apply_backup_filter(self):
        """Apply the current filter settings to the backup table."""
        # Check if backup UI components are initialized
        if not hasattr(self, 'backup_table') or not hasattr(self, 'backup_filter_combo'):
            return

        filter_type = self.backup_filter_combo.currentText()

        try:
            # Clear existing table
            self.backup_table.setRowCount(0)

            # Get filtered devices based on selection
            devices_to_show = []

            if filter_type == "All Devices":
                devices_to_show = list(self.device_manager.devices.values())
                self.backup_status_label.setText(f"Showing all {len(devices_to_show)} devices")
            elif filter_type == "By Group":
                group_name = self.backup_group_combo.currentText()
                if group_name != "Select Group" and group_name in self.device_manager.groups:
                    group = self.device_manager.groups[group_name]
                    # Ensure we're getting the actual device objects
                    devices_to_show = []
                    for member in group.members:
                        if hasattr(member, 'name'):
                            devices_to_show.append(member)
                        elif isinstance(member, str) and member in self.device_manager.devices:
                            devices_to_show.append(self.device_manager.devices[member])
                    
                    self.backup_status_label.setText(f"Showing {len(devices_to_show)} devices from group '{group_name}'")
                else:
                    # No devices to show if no group is selected
                    self.backup_status_label.setText("Please select a group")
                    return

            # Add filtered devices to the table
            for row, device in enumerate(devices_to_show):
                self.backup_table.insertRow(row)
                
                # Add checkbox for selection
                checkbox = QTableWidgetItem()
                checkbox.setFlags(Qt.ItemFlag.ItemIsUserCheckable | Qt.ItemFlag.ItemIsEnabled)
                checkbox.setCheckState(Qt.CheckState.Unchecked)
                self.backup_table.setItem(row, 0, checkbox)
                
                # Add device information
                self.backup_table.setItem(row, 1, QTableWidgetItem(device.name))
                self.backup_table.setItem(row, 2, QTableWidgetItem(device.ip_address))
                
                # Device type
                device_type = str(device.device_type) if hasattr(device, 'device_type') else "Unknown"
                self.backup_table.setItem(row, 3, QTableWidgetItem(device_type))
                
                # Connection status
                status_text = "Unknown"
                status_color = "gray"
                
                if hasattr(device, '_connection_status'):
                    status_text = device._connection_status.name.lower() if hasattr(device._connection_status, 'name') else str(device._connection_status)
                    
                    if status_text == "connected":
                        status_color = "green"
                    elif status_text in ["disconnected", "error", "timeout", "auth_failed"]:
                        status_color = "red"
                    else:
                        status_color = "orange"
                elif hasattr(device, 'connection_status'):
                    status_text = device.connection_status.name.lower() if hasattr(device.connection_status, 'name') else str(device.connection_status)
                    
                    if status_text == "connected":
                        status_color = "green"
                    elif status_text in ["disconnected", "error", "timeout", "auth_failed"]:
                        status_color = "red"
                    else:
                        status_color = "orange"
                
                status_item = QTableWidgetItem(status_text)
                status_item.setForeground(QBrush(QColor(status_color)))
                self.backup_table.setItem(row, 4, status_item)
                
                # Last backup time
                last_backup = "Never"
                if hasattr(device, 'last_backup') and device.last_backup:
                    if callable(device.last_backup):
                        # Handle property method
                        backup_time = device.last_backup()
                        if backup_time:
                            last_backup = backup_time.strftime("%Y-%m-%d %H:%M")
                    else:
                        # Handle property attribute
                        last_backup = device.last_backup.strftime("%Y-%m-%d %H:%M")
                
                self.backup_table.setItem(row, 5, QTableWidgetItem(last_backup))

        except Exception as e:
            logging.error(f"Error applying backup filter: {str(e)}")
            self.backup_status_label.setText(f"Error: {str(e)}")
            self.backup_status_label.setStyleSheet("color: red;")
            QMessageBox.critical(self, "Backup Error", f"An error occurred while applying the backup filter:\n{str(e)}")

    def start_backup_filtered(self):
        """Start backup based on the current table and filter settings."""
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
                # Check for QCheckBox widget (used in backup_table)
                cell_widget = self.backup_table.cellWidget(row, 0)
                if isinstance(cell_widget, QCheckBox) and cell_widget.isChecked():
                    device_name = self.backup_table.item(row, 1).text()
                    if device_name in self.device_manager.devices:
                        devices.append(self.device_manager.devices[device_name])
                
                # Also check for QTableWidgetItem checkboxes
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
            QMessageBox.critical(self, "Backup Error", f"An error occurred while starting the backup:\n{str(e)}")
