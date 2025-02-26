"""Scheduler Tab Controller for PulsarNet GUI.

This controller handles the logic for the scheduler configuration tab.
"""

from PyQt6.QtWidgets import QFileDialog, QMessageBox, QPushButton, QTableWidgetItem, QHBoxLayout, QLabel, QComboBox, QVBoxLayout, QFormLayout, QLineEdit, QCheckBox, QTimeEdit, QGroupBox, QDialog, QDialogButtonBox, QRadioButton, QScrollArea, QTableWidget, QWidget, QHeaderView
from PyQt6.QtCore import Qt, QDateTime, QTime
from .base_controller import BaseController
import os
import json
import logging
from datetime import datetime

class SchedulerTabController(BaseController):
    def connect_signals(self):
        """Connect UI signals to controller methods."""
        # Connect filter change handlers
        self.view.schedule_filter_combo.currentTextChanged.connect(self.on_schedule_filter_changed)
        self.view.schedule_group_combo.currentTextChanged.connect(self.on_schedule_group_changed)
        
        # Connect button handlers
        self.view.add_schedule_btn.clicked.connect(self.show_add_schedule_dialog)
        self.view.edit_schedule_btn.clicked.connect(self.edit_selected_schedule)
        self.view.remove_schedule_btn.clicked.connect(self.remove_selected_schedule)
        self.view.refresh_btn.clicked.connect(self.update_scheduler_table)
        
        # Connect table cell clicked signal to handle checkbox clicks
        self.view.scheduler_table.cellClicked.connect(self.on_scheduler_table_cell_clicked)
        self.view.scheduler_table.cellDoubleClicked.connect(lambda row, col: self.edit_selected_schedule())
        
        # Connect device filter if it exists
        if hasattr(self.view, 'schedule_device_combo'):
            self.view.schedule_device_combo.currentTextChanged.connect(self.on_schedule_device_changed)
    
    def initialize(self):
        """Initialize the controller with data."""
        try:
            # Populate groups dropdown
            self.view.schedule_group_combo.clear()
            self.view.schedule_group_combo.addItem("Select Group")
            
            # Clear any stale data in the scheduler table
            self.view.scheduler_table.blockSignals(True)
            self.view.scheduler_table.clearContents()
            self.view.scheduler_table.setRowCount(0)
            
            # This code ensures no duplicate widgets in the scheduler table
            for row in range(self.view.scheduler_table.rowCount()):
                for col in range(self.view.scheduler_table.columnCount()):
                    if self.view.scheduler_table.cellWidget(row, col):
                        self.view.scheduler_table.removeCellWidget(row, col)
            
            # Add existing groups
            for group_name in sorted(self.main_window.device_manager.groups.keys()):
                self.view.schedule_group_combo.addItem(group_name)
            
            # Initialize device dropdown if present
            if hasattr(self.view, 'schedule_device_combo'):
                self.view.schedule_device_combo.clear()
                self.view.schedule_device_combo.addItem("Select Device")
                # Add all device names
                for device in sorted(self.main_window.device_manager.devices.values(), key=lambda d: d.name):
                    self.view.schedule_device_combo.addItem(device.name)
                
                # Disable it initially (will be enabled when "By Device" is selected)
                self.view.schedule_device_combo.setEnabled(False)
            
            # Update the scheduler table with all schedules
            self.update_scheduler_table()
            
            # Re-enable signals
            self.view.scheduler_table.blockSignals(False)
            
            # Update filter status
            self.on_schedule_filter_changed(self.view.schedule_filter_combo.currentText())
            
        except Exception as e:
            logging.error(f"Error initializing scheduler tab: {str(e)}")
            self.view.schedule_status_label.setText(f"Error: {str(e)}")
            return False
        
        return True
    
    def on_schedule_filter_changed(self, text):
        """Handle schedule filter type selection change."""
        try:
            # Show/hide UI elements based on filter type
            is_group_filter = (text == "By Group")
            is_device_filter = (text == "By Device")
            
            # Update the UI based on filter selection
            self.view.schedule_group_combo.setEnabled(is_group_filter)
            self.view.group_label.setEnabled(is_group_filter)
            
            # Handle device filter - populate device dropdown if needed
            if is_device_filter and not hasattr(self.view, 'schedule_device_combo'):
                # Create device selection UI if it doesn't exist
                device_layout = QHBoxLayout()
                self.view.device_label = QLabel("Device:")
                self.view.device_label.setToolTip("Select a specific device")
                device_layout.addWidget(self.view.device_label)
                
                self.view.schedule_device_combo = QComboBox()
                self.view.schedule_device_combo.addItem("Select Device")
                self.view.schedule_device_combo.setToolTip("Select a device to filter schedules")
                self.view.schedule_device_combo.setMinimumWidth(200)
                self.view.schedule_device_combo.currentTextChanged.connect(self.on_schedule_device_changed)
                device_layout.addWidget(self.view.schedule_device_combo)
                
                # Insert this layout after the group layout in the filter panel
                filter_panel = self.view.findChild(QGroupBox, "Schedule Filter Options")
                if filter_panel and filter_panel.layout():
                    filter_panel_layout = filter_panel.layout()
                    filter_panel_layout.insertLayout(2, device_layout)
                else:
                    # Fallback - add directly to the view layout
                    logging.warning("Could not find filter panel or its layout, adding device filter to main layout")
                    self.view.layout().insertLayout(1, device_layout)
                
                # Populate the device dropdown
                self.populate_device_dropdown()
            
            # Enable/disable device filter UI if it exists
            if hasattr(self.view, 'schedule_device_combo'):
                self.view.schedule_device_combo.setEnabled(is_device_filter)
                self.view.device_label.setEnabled(is_device_filter)
                
                # Reset device dropdown if not using device filter
                if not is_device_filter:
                    self.view.schedule_device_combo.setCurrentText("Select Device")
            
            # Reset UI elements that aren't applicable
            if not is_group_filter:
                self.view.schedule_group_combo.setCurrentText("Select Group")
            
            # Show all schedules if "All Schedules" is selected
            if text == "All Schedules":
                self.view.schedule_status_label.setText(f"Showing all {len(self.main_window.schedule_manager.schedules)} schedules")
                # Apply the filter immediately
                self.apply_schedule_filter()
                
            # Update the schedule status for clarity
            if text == "By Group" and self.view.schedule_group_combo.currentText() == "Select Group":
                self.view.schedule_status_label.setText("Please select a group")
                # Clear the table until a group is selected
                self.view.scheduler_table.setRowCount(0)
                
            if text == "By Device" and hasattr(self.view, 'schedule_device_combo') and self.view.schedule_device_combo.currentText() == "Select Device":
                self.view.schedule_status_label.setText("Please select a device")
                # Clear the table until a device is selected
                self.view.scheduler_table.setRowCount(0)
        except Exception as e:
            logging.error(f"Error in schedule filter change: {str(e)}")
            self.view.schedule_status_label.setText(f"Error: {str(e)}")
            self.view.schedule_status_label.setStyleSheet("color: red;")
    
    def on_schedule_group_changed(self, group_name):
        """Handle schedule group selection change."""
        if group_name != "Select Group":
            # Count how many schedules are for this group
            schedule_count = 0
            for schedule in self.main_window.schedule_manager.schedules.values():
                if schedule.target_type.value == "Group" and group_name in schedule.groups:
                    schedule_count += 1
            
            self.view.schedule_status_label.setText(f"Showing {schedule_count} schedules for group '{group_name}'")
            
            # Automatically apply the filter
            self.apply_schedule_filter()
        else:
            self.view.schedule_status_label.setText("No group selected")
    
    def apply_schedule_filter(self):
        """Apply the current filter settings to the scheduler table."""
        # Check if scheduler UI components are initialized
        if not hasattr(self.view, 'scheduler_table') or not hasattr(self.view, 'schedule_filter_combo'):
            return
        
        filter_type = self.view.schedule_filter_combo.currentText()
        
        try:
            # Clear existing table
            self.view.scheduler_table.clearContents()
            self.view.scheduler_table.setRowCount(0)
            
            # Get filtered schedules based on selection
            schedules_to_show = []
            
            if filter_type == "All Schedules":
                schedules_to_show = list(self.main_window.schedule_manager.schedules.values())
                self.view.schedule_status_label.setText(f"Showing all {len(schedules_to_show)} schedules")
            elif filter_type == "By Group":
                group_name = self.view.schedule_group_combo.currentText()
                if group_name != "Select Group":
                    # Filter schedules for this group
                    for schedule in self.main_window.schedule_manager.schedules.values():
                        if schedule.target_type.value == "Group" and group_name in schedule.groups:
                            schedules_to_show.append(schedule)
                    
                    self.view.schedule_status_label.setText(f"Showing {len(schedules_to_show)} schedules for group '{group_name}'")
                else:
                    # No schedules to show if no group is selected
                    self.view.schedule_status_label.setText("Please select a group")
                    # Ensure we return an empty list, not a boolean
                    self.update_scheduler_table([])
                    return
            elif filter_type == "By Device":
                device_name = self.view.schedule_device_combo.currentText()
                if device_name != "Select Device":
                    # Filter schedules for this device
                    for schedule in self.main_window.schedule_manager.schedules.values():
                        if schedule.target_type.value == "Device" and device_name in schedule.devices:
                            schedules_to_show.append(schedule)
                    
                    self.view.schedule_status_label.setText(f"Showing {len(schedules_to_show)} schedules for device '{device_name}'")
                else:
                    # No schedules to show if no device is selected
                    self.view.schedule_status_label.setText("Please select a device")
                    # Ensure we return an empty list, not a boolean
                    self.update_scheduler_table([])
                    return
            
            # Add filtered schedules to the table
            self.update_scheduler_table(schedules_to_show)
            
        except Exception as e:
            logging.error(f"Error applying schedule filter: {str(e)}")
            self.view.schedule_status_label.setText(f"Error: {str(e)}")
            self.view.schedule_status_label.setStyleSheet("color: red;")
    
    def update_scheduler_table(self, schedules=None):
        """Update the scheduler table with current schedules."""
        try:
            # Remember selected schedule
            selected_schedule_name = None
            selected_row = -1
            
            # Check if any row is selected first
            selected_items = self.view.scheduler_table.selectedItems()
            if selected_items:
                selected_row = selected_items[0].row()
                selected_schedule_name = self.view.scheduler_table.item(selected_row, 1).text() if selected_row >= 0 else None
            else:
                # Check checkboxes
                for row in range(self.view.scheduler_table.rowCount()):
                    checkbox_item = self.view.scheduler_table.item(row, 0)
                    if checkbox_item and checkbox_item.checkState() == Qt.CheckState.Checked:
                        selected_row = row
                        selected_schedule_name = self.view.scheduler_table.item(row, 1).text()
                        break
            
            # Completely clear the table and block signals temporarily
            self.view.scheduler_table.blockSignals(True)
            self.view.scheduler_table.clearContents()
            
            # Remove any widgets that might still exist
            for row in range(self.view.scheduler_table.rowCount()):
                for col in range(self.view.scheduler_table.columnCount()):
                    if self.view.scheduler_table.cellWidget(row, col):
                        self.view.scheduler_table.removeCellWidget(row, col)
            
            self.view.scheduler_table.setRowCount(0)
            
            # Use provided schedules or get all schedules if none provided
            if schedules is None:
                schedules = self.main_window.schedule_manager.schedules.values()
            elif not isinstance(schedules, (list, tuple, set)) and not hasattr(schedules, '__iter__'):
                # Handle case where schedules is not iterable (e.g., bool)
                logging.warning("Non-iterable schedules provided, defaulting to all schedules")
                schedules = self.main_window.schedule_manager.schedules.values()
            
            # Add each schedule to the table
            schedule_to_row_map = {}  # To track where each schedule ends up in the new table
            
            for row, schedule in enumerate(schedules):
                self.view.scheduler_table.insertRow(row)
                
                # Add checkbox for selection
                checkbox = QTableWidgetItem()
                checkbox.setFlags(Qt.ItemFlag.ItemIsUserCheckable | Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsSelectable)
                checkbox.setCheckState(Qt.CheckState.Unchecked)
                self.view.scheduler_table.setItem(row, 0, checkbox)
                schedule_to_row_map[schedule.name] = row
                
                # Name column
                name_item = QTableWidgetItem(schedule.name)
                name_item.setFlags(Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsSelectable)
                self.view.scheduler_table.setItem(row, 1, name_item)
                
                # Schedule type
                type_item = QTableWidgetItem(schedule.schedule_type.value if hasattr(schedule.schedule_type, 'value') else str(schedule.schedule_type))
                type_item.setFlags(Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsSelectable)
                self.view.scheduler_table.setItem(row, 2, type_item)
                
                # Targets (devices or groups)
                if schedule.target_type.value == "Device":
                    targets = ", ".join(schedule.devices)
                else:  # Group
                    targets = ", ".join(schedule.groups)
                targets_item = QTableWidgetItem(targets)
                targets_item.setFlags(Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsSelectable)
                self.view.scheduler_table.setItem(row, 3, targets_item)
                
                # Next run time
                next_run = "Not scheduled"
                if schedule.next_run:
                    next_run = schedule.next_run.strftime("%Y-%m-%d %H:%M")
                next_run_item = QTableWidgetItem(next_run)
                next_run_item.setFlags(Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsSelectable)
                self.view.scheduler_table.setItem(row, 4, next_run_item)
                
                # Last run time
                last_run = "Never"
                if schedule.last_run:
                    last_run = schedule.last_run.strftime("%Y-%m-%d %H:%M")
                last_run_item = QTableWidgetItem(last_run)
                last_run_item.setFlags(Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsSelectable)
                self.view.scheduler_table.setItem(row, 5, last_run_item)
            
            # Restore selection if the schedule still exists
            if selected_schedule_name and selected_schedule_name in schedule_to_row_map:
                row_to_select = schedule_to_row_map[selected_schedule_name]
                self.view.scheduler_table.selectRow(row_to_select)
                checkbox_item = self.view.scheduler_table.item(row_to_select, 0)
                if checkbox_item:
                    checkbox_item.setCheckState(Qt.CheckState.Checked)
            
            # Re-enable signals after all updates are done
            self.view.scheduler_table.blockSignals(False)
            
            # Hide the empty message if there are schedules
            if hasattr(self.view, 'empty_schedules_label'):
                self.view.empty_schedules_label.setVisible(len(schedules) == 0)
            
            return True
        except Exception as e:
            logging.error(f"Error updating scheduler table: {str(e)}")
            self.view.schedule_status_label.setText(f"Error: {str(e)}")
            self.view.schedule_status_label.setStyleSheet("color: red;")
    
    def show_add_schedule_dialog(self):
        """Show dialog to add a new schedule."""
        try:
            # Create a dialog
            dialog = QDialog(self.main_window)
            dialog.setWindowTitle("Add Backup Schedule")
            dialog.setMinimumWidth(500)
            dialog.setMinimumHeight(600)
            
            # Set up the layout
            layout = QVBoxLayout(dialog)
            
            # Form for schedule details
            form_layout = QFormLayout()
            
            # Schedule name
            name_input = QLineEdit()
            name_input.setPlaceholderText("Enter schedule name")
            form_layout.addRow("Schedule Name:", name_input)
            
            # Schedule type
            type_combo = QComboBox()
            for schedule_type in ["Daily", "Weekly", "Custom"]:
                type_combo.addItem(schedule_type)
            form_layout.addRow("Schedule Type:", type_combo)
            
            # Target type selection - now as radio buttons for clarity
            target_type_group = QGroupBox("Target Type")
            target_type_layout = QVBoxLayout(target_type_group)
            
            device_radio = QRadioButton("Individual Devices")
            device_radio.setChecked(True)  # Default selection
            group_radio = QRadioButton("Device Group")
            
            target_type_layout.addWidget(device_radio)
            target_type_layout.addWidget(group_radio)
            
            # Devices selection container
            devices_container = QGroupBox("Select Devices")
            devices_container_layout = QVBoxLayout(devices_container)
            
            # Direct device selection
            direct_devices_group = QGroupBox("Available Devices")
            direct_devices_layout = QVBoxLayout(direct_devices_group)
            direct_devices_scroll = QScrollArea()
            direct_devices_scroll.setWidgetResizable(True)
            direct_devices_widget = QWidget()
            direct_devices_scroll_layout = QVBoxLayout(direct_devices_widget)
            
            # Get all devices
            device_list = sorted(self.main_window.device_manager.devices.keys())
            device_checkboxes = {}
            
            for device_name in device_list:
                checkbox = QCheckBox(device_name)
                direct_devices_scroll_layout.addWidget(checkbox)
                device_checkboxes[device_name] = checkbox
            
            direct_devices_scroll.setWidget(direct_devices_widget)
            direct_devices_layout.addWidget(direct_devices_scroll)
            devices_container_layout.addWidget(direct_devices_group)
            
            # Group selection
            groups_container = QGroupBox("Select a Group")
            groups_container_layout = QVBoxLayout(groups_container)
            
            # Group selection combo
            group_selection_layout = QHBoxLayout()
            group_label = QLabel("Group:")
            group_combo = QComboBox()
            group_combo.addItem("Select Group")
            
            # Get all groups
            group_list = sorted(self.main_window.device_manager.groups.keys())
            for group_name in group_list:
                group_combo.addItem(group_name)
            
            group_selection_layout.addWidget(group_label)
            group_selection_layout.addWidget(group_combo)
            groups_container_layout.addLayout(group_selection_layout)
            
            # Group devices display
            group_devices_label = QLabel("Devices in selected group:")
            groups_container_layout.addWidget(group_devices_label)
            
            group_devices_list = QTableWidget()
            group_devices_list.setColumnCount(2)
            group_devices_list.setHorizontalHeaderLabels(["Device Name", "IP Address"])
            group_devices_list.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
            group_devices_list.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
            groups_container_layout.addWidget(group_devices_list)
            
            # Function to update group devices view
            def update_group_devices(group_name):
                group_devices_list.setRowCount(0)
                if group_name != "Select Group" and group_name in self.main_window.device_manager.groups:
                    group = self.main_window.device_manager.groups[group_name]
                    row = 0
                    for member in group.members:
                        if hasattr(member, 'name') and hasattr(member, 'ip_address'):
                            # It's a device object
                            group_devices_list.insertRow(row)
                            group_devices_list.setItem(row, 0, QTableWidgetItem(member.name))
                            group_devices_list.setItem(row, 1, QTableWidgetItem(member.ip_address))
                            row += 1
                        elif isinstance(member, str) and member in self.main_window.device_manager.devices:
                            # It's a device name
                            device = self.main_window.device_manager.devices[member]
                            group_devices_list.insertRow(row)
                            group_devices_list.setItem(row, 0, QTableWidgetItem(device.name))
                            group_devices_list.setItem(row, 1, QTableWidgetItem(device.ip_address))
                            row += 1
            
            group_combo.currentTextChanged.connect(update_group_devices)
            
            # Time selection
            time_edit = QTimeEdit()
            time_edit.setDisplayFormat("HH:mm")
            time_edit.setTime(QTime.currentTime())
            form_layout.addRow("Time:", time_edit)
            
            # Day selection for weekly schedules
            days_group = QGroupBox("Days (for Weekly schedules)")
            days_layout = QVBoxLayout(days_group)
            
            day_names = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
            day_checkboxes = {}
            
            for i, day_name in enumerate(day_names):
                checkbox = QCheckBox(day_name)
                days_layout.addWidget(checkbox)
                day_checkboxes[i] = checkbox
            
            # Show/hide days selection based on schedule type
            def on_schedule_type_changed(text):
                days_group.setVisible(text == "Weekly")
            
            type_combo.currentTextChanged.connect(on_schedule_type_changed)
            on_schedule_type_changed(type_combo.currentText())  # Initial state
            
            # Show/hide containers based on target type selection
            def on_target_type_changed():
                devices_container.setVisible(device_radio.isChecked())
                groups_container.setVisible(group_radio.isChecked())
            
            device_radio.toggled.connect(on_target_type_changed)
            group_radio.toggled.connect(on_target_type_changed)
            on_target_type_changed()  # Initial state
            
            # Add form to the layout
            layout.addLayout(form_layout)
            layout.addWidget(target_type_group)
            layout.addWidget(devices_container)
            layout.addWidget(groups_container)
            
            # Add days selection to the layout
            layout.addWidget(days_group)
            
            # Add dialog buttons
            button_box = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
            button_box.accepted.connect(dialog.accept)
            button_box.rejected.connect(dialog.reject)
            layout.addWidget(button_box)
            
            # Show the dialog and process result
            if dialog.exec() == QDialog.DialogCode.Accepted:
                # Get values from the form
                schedule_name = name_input.text().strip()
                schedule_type_text = type_combo.currentText()
                target_type_text = "Device" if device_radio.isChecked() else "Group"
                selected_time = time_edit.time().toString("HH:mm")
                
                # Validate name
                if not schedule_name:
                    QMessageBox.warning(self.main_window, "Validation Error", "Schedule name cannot be empty.")
                    return
                
                # Check if name already exists
                if schedule_name in self.main_window.schedule_manager.schedules:
                    QMessageBox.warning(self.main_window, "Validation Error", f"Schedule name '{schedule_name}' already exists.")
                    return
                
                # Get selected devices or groups
                selected_devices = []
                selected_groups = []
                
                if target_type_text == "Device":
                    for device_name, checkbox in device_checkboxes.items():
                        if checkbox.isChecked():
                            selected_devices.append(device_name)
                    
                    if not selected_devices:
                        QMessageBox.warning(self.main_window, "Validation Error", "Please select at least one device.")
                        return
                else:  # Group
                    selected_group = group_combo.currentText()
                    if selected_group == "Select Group":
                        QMessageBox.warning(self.main_window, "Validation Error", "Please select a group.")
                        return
                    selected_groups.append(selected_group)
                
                # Get selected days for weekly schedules
                selected_days = []
                if schedule_type_text == "Weekly":
                    for day_index, checkbox in day_checkboxes.items():
                        if checkbox.isChecked():
                            selected_days.append(day_index)
                    
                    if not selected_days:
                        QMessageBox.warning(self.main_window, "Validation Error", "Please select at least one day for weekly schedule.")
                        return
                
                # Create the schedule
                from pulsarnet.scheduler.scheduler import BackupSchedule, ScheduleType, TargetType
                
                schedule_type = ScheduleType(schedule_type_text)
                target_type = TargetType(target_type_text)
                
                schedule = BackupSchedule(
                    name=schedule_name,
                    schedule_type=schedule_type,
                    target_type=target_type,
                    devices=selected_devices,
                    groups=selected_groups,
                    time=selected_time,
                    days=selected_days
                )
                
                # Add the schedule
                self.main_window.schedule_manager.add_schedule(schedule)
                
                # Update the UI
                self.update_scheduler_table()
                
                QMessageBox.information(self.main_window, "Success", f"Schedule '{schedule_name}' has been created.")
        except Exception as e:
            logging.error(f"Error showing add schedule dialog: {str(e)}")
            QMessageBox.critical(self.main_window, "Error", f"Failed to create schedule: {str(e)}")
    
    def edit_selected_schedule(self):
        """Edit the selected schedule."""
        try:
            # Check if any row is selected first
            selected_items = self.view.scheduler_table.selectedItems()
            selected_row = None
            
            if selected_items:
                # Row selection method
                selected_row = selected_items[0].row()
            else:
                # Checkbox selection method
                for row in range(self.view.scheduler_table.rowCount()):
                    checkbox_item = self.view.scheduler_table.item(row, 0)
                    if checkbox_item and checkbox_item.checkState() == Qt.CheckState.Checked:
                        selected_row = row
                        break
            
            if selected_row is None:
                QMessageBox.warning(self.main_window, "No Selection", "Please select a schedule to edit by selecting a row or checking the box")
                return
            
            # Get the schedule name from the selected row
            schedule_name = self.view.scheduler_table.item(selected_row, 1).text()
            
            # Get the existing schedule
            if schedule_name not in self.main_window.schedule_manager.schedules:
                QMessageBox.warning(self.main_window, "Error", f"Schedule '{schedule_name}' not found")
                return
            
            schedule = self.main_window.schedule_manager.schedules[schedule_name]
            
            # Create a dialog
            dialog = QDialog(self.main_window)
            dialog.setWindowTitle(f"Edit Schedule: {schedule_name}")
            dialog.setMinimumWidth(500)
            dialog.setMinimumHeight(600)
            
            # Set up the layout
            layout = QVBoxLayout(dialog)
            
            # Form for schedule details
            form_layout = QFormLayout()
            
            # Schedule name (read-only when editing)
            name_input = QLineEdit(schedule_name)
            name_input.setEnabled(False)  # Disable name editing
            form_layout.addRow("Schedule Name:", name_input)
            
            # Schedule type
            type_combo = QComboBox()
            for schedule_type in ["Daily", "Weekly", "Custom"]:
                type_combo.addItem(schedule_type)
            # Set current type
            type_combo.setCurrentText(schedule.schedule_type.value)
            form_layout.addRow("Schedule Type:", type_combo)
            
            # Target type selection - now as radio buttons for clarity
            target_type_group = QGroupBox("Target Type")
            target_type_layout = QVBoxLayout(target_type_group)
            
            device_radio = QRadioButton("Individual Devices")
            group_radio = QRadioButton("Device Group")
            
            # Set correct radio button based on existing schedule
            if schedule.target_type.value == "Device":
                device_radio.setChecked(True)
            else:
                group_radio.setChecked(True)
            
            target_type_layout.addWidget(device_radio)
            target_type_layout.addWidget(group_radio)
            
            # Devices selection container
            devices_container = QGroupBox("Select Devices")
            devices_container_layout = QVBoxLayout(devices_container)
            
            # Direct device selection
            direct_devices_group = QGroupBox("Available Devices")
            direct_devices_layout = QVBoxLayout(direct_devices_group)
            direct_devices_scroll = QScrollArea()
            direct_devices_scroll.setWidgetResizable(True)
            direct_devices_widget = QWidget()
            direct_devices_scroll_layout = QVBoxLayout(direct_devices_widget)
            
            # Get all devices
            device_list = sorted(self.main_window.device_manager.devices.keys())
            device_checkboxes = {}
            
            for device_name in device_list:
                checkbox = QCheckBox(device_name)
                # Check if this device is in the schedule
                if schedule.target_type.value == "Device" and device_name in schedule.devices:
                    checkbox.setChecked(True)
                direct_devices_scroll_layout.addWidget(checkbox)
                device_checkboxes[device_name] = checkbox
            
            direct_devices_scroll.setWidget(direct_devices_widget)
            direct_devices_layout.addWidget(direct_devices_scroll)
            devices_container_layout.addWidget(direct_devices_group)
            
            # Group selection
            groups_container = QGroupBox("Select a Group")
            groups_container_layout = QVBoxLayout(groups_container)
            
            # Group selection combo
            group_selection_layout = QHBoxLayout()
            group_label = QLabel("Group:")
            group_combo = QComboBox()
            group_combo.addItem("Select Group")
            
            # Get all groups
            group_list = sorted(self.main_window.device_manager.groups.keys())
            for group_name in group_list:
                group_combo.addItem(group_name)
                
            # Set current group if applicable
            if schedule.target_type.value == "Group" and schedule.groups:
                current_group = schedule.groups[0]
                if current_group in group_list:
                    group_combo.setCurrentText(current_group)
            
            group_selection_layout.addWidget(group_label)
            group_selection_layout.addWidget(group_combo)
            groups_container_layout.addLayout(group_selection_layout)
            
            # Group devices display
            group_devices_label = QLabel("Devices in selected group:")
            groups_container_layout.addWidget(group_devices_label)
            
            group_devices_list = QTableWidget()
            group_devices_list.setColumnCount(2)
            group_devices_list.setHorizontalHeaderLabels(["Device Name", "IP Address"])
            group_devices_list.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
            group_devices_list.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
            groups_container_layout.addWidget(group_devices_list)
            
            # Function to update group devices view
            def update_group_devices(group_name):
                group_devices_list.setRowCount(0)
                if group_name != "Select Group" and group_name in self.main_window.device_manager.groups:
                    group = self.main_window.device_manager.groups[group_name]
                    row = 0
                    for member in group.members:
                        if hasattr(member, 'name') and hasattr(member, 'ip_address'):
                            # It's a device object
                            group_devices_list.insertRow(row)
                            group_devices_list.setItem(row, 0, QTableWidgetItem(member.name))
                            group_devices_list.setItem(row, 1, QTableWidgetItem(member.ip_address))
                            row += 1
                        elif isinstance(member, str) and member in self.main_window.device_manager.devices:
                            # It's a device name
                            device = self.main_window.device_manager.devices[member]
                            group_devices_list.insertRow(row)
                            group_devices_list.setItem(row, 0, QTableWidgetItem(device.name))
                            group_devices_list.setItem(row, 1, QTableWidgetItem(device.ip_address))
                            row += 1
            
            group_combo.currentTextChanged.connect(update_group_devices)
            # Initialize the group devices view
            update_group_devices(group_combo.currentText())
            
            # Time selection
            time_edit = QTimeEdit()
            time_edit.setDisplayFormat("HH:mm")
            # Set current time
            hour, minute = map(int, schedule.time.split(':'))
            time_edit.setTime(QTime(hour, minute))
            form_layout.addRow("Time:", time_edit)
            
            # Day selection for weekly schedules
            days_group = QGroupBox("Days (for Weekly schedules)")
            days_layout = QVBoxLayout(days_group)
            
            day_names = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
            day_checkboxes = {}
            
            for i, day_name in enumerate(day_names):
                checkbox = QCheckBox(day_name)
                # Check if this day is in the schedule
                if i in schedule.days:
                    checkbox.setChecked(True)
                days_layout.addWidget(checkbox)
                day_checkboxes[i] = checkbox
            
            # Show/hide days selection based on schedule type
            def on_schedule_type_changed(text):
                days_group.setVisible(text == "Weekly")
            
            type_combo.currentTextChanged.connect(on_schedule_type_changed)
            on_schedule_type_changed(type_combo.currentText())  # Initial state
            
            # Show/hide containers based on target type selection
            def on_target_type_changed():
                devices_container.setVisible(device_radio.isChecked())
                groups_container.setVisible(group_radio.isChecked())
            
            device_radio.toggled.connect(on_target_type_changed)
            group_radio.toggled.connect(on_target_type_changed)
            on_target_type_changed()  # Initial state
            
            # Add form to the layout
            layout.addLayout(form_layout)
            layout.addWidget(target_type_group)
            layout.addWidget(devices_container)
            layout.addWidget(groups_container)
            
            # Add days selection to the layout
            layout.addWidget(days_group)
            
            # Add dialog buttons
            button_box = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
            button_box.accepted.connect(dialog.accept)
            button_box.rejected.connect(dialog.reject)
            layout.addWidget(button_box)
            
            # Show the dialog and process result
            if dialog.exec() == QDialog.DialogCode.Accepted:
                # Get values from the form
                schedule_type_text = type_combo.currentText()
                target_type_text = "Device" if device_radio.isChecked() else "Group"
                selected_time = time_edit.time().toString("HH:mm")
                
                # Get selected devices or groups
                selected_devices = []
                selected_groups = []
                
                if target_type_text == "Device":
                    for device_name, checkbox in device_checkboxes.items():
                        if checkbox.isChecked():
                            selected_devices.append(device_name)
                    
                    if not selected_devices:
                        QMessageBox.warning(self.main_window, "Validation Error", "Please select at least one device.")
                        return
                else:  # Group
                    selected_group = group_combo.currentText()
                    if selected_group == "Select Group":
                        QMessageBox.warning(self.main_window, "Validation Error", "Please select a group.")
                        return
                    selected_groups.append(selected_group)
                
                # Get selected days for weekly schedules
                selected_days = []
                if schedule_type_text == "Weekly":
                    for day_index, checkbox in day_checkboxes.items():
                        if checkbox.isChecked():
                            selected_days.append(day_index)
                    
                    if not selected_days:
                        QMessageBox.warning(self.main_window, "Validation Error", "Please select at least one day for weekly schedule.")
                        return
                
                # Update the schedule
                from pulsarnet.scheduler.scheduler import ScheduleType, TargetType
                
                # Create updated schedule
                updated_schedule = type(schedule)(
                    name=schedule_name,
                    schedule_type=ScheduleType(schedule_type_text),
                    target_type=TargetType(target_type_text),
                    devices=selected_devices,
                    groups=selected_groups,
                    time=selected_time,
                    days=selected_days,
                    enabled=schedule.enabled,
                    last_run=schedule.last_run
                )
                
                # Update the schedule
                self.main_window.schedule_manager.update_schedule(updated_schedule)
                
                # Update the UI
                self.update_scheduler_table()
                
                QMessageBox.information(self.main_window, "Success", f"Schedule '{schedule_name}' has been updated.")
        except Exception as e:
            logging.error(f"Error editing schedule: {str(e)}")
            QMessageBox.critical(self.main_window, "Error", f"Failed to update schedule: {str(e)}")
    
    def remove_selected_schedule(self):
        """Remove the selected schedule."""
        try:
            # Check if any row is selected first
            selected_items = self.view.scheduler_table.selectedItems()
            selected_row = None
            
            if selected_items:
                # Row selection method
                selected_row = selected_items[0].row()
            else:
                # Checkbox selection method
                for row in range(self.view.scheduler_table.rowCount()):
                    checkbox_item = self.view.scheduler_table.item(row, 0)
                    if checkbox_item and checkbox_item.checkState() == Qt.CheckState.Checked:
                        selected_row = row
                        break
            
            if selected_row is None:
                QMessageBox.warning(self.main_window, "No Selection", "Please select a schedule to remove by selecting a row or checking the box")
                return
            
            # Get the schedule name from the selected row
            schedule_name = self.view.scheduler_table.item(selected_row, 1).text()
            
            # Confirm deletion
            response = QMessageBox.question(
                self.main_window,
                "Confirm Deletion",
                f"Are you sure you want to delete the schedule '{schedule_name}'?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No
            )
            
            if response == QMessageBox.StandardButton.Yes:
                try:
                    # Remove the schedule
                    self.main_window.schedule_manager.remove_schedule(schedule_name)
                    
                    # Update the table
                    self.update_scheduler_table()
                    
                    QMessageBox.information(self.main_window, "Success", f"Schedule '{schedule_name}' has been removed")
                except Exception as e:
                    logging.error(f"Error removing schedule: {str(e)}")
                    QMessageBox.critical(self.main_window, "Error", f"Failed to remove schedule: {str(e)}")
        except Exception as e:
            logging.error(f"Error in schedule removal: {str(e)}")
            QMessageBox.critical(self.main_window, "Error", f"An unexpected error occurred: {str(e)}")

    def populate_device_dropdown(self):
        """Populate the device dropdown with available devices."""
        # Get the list of devices
        devices = list(self.main_window.device_manager.devices.keys())
        
        # Add devices to the dropdown
        for device_name in devices:
            self.view.schedule_device_combo.addItem(device_name)

    def on_schedule_device_changed(self, text):
        """Handle schedule device selection change."""
        if text != "Select Device":
            # Count how many schedules are for this device
            schedule_count = 0
            for schedule in self.main_window.schedule_manager.schedules.values():
                if schedule.target_type.value == "Device" and text in schedule.devices:
                    schedule_count += 1
            
            self.view.schedule_status_label.setText(f"Showing {schedule_count} schedules for device '{text}'")
            
            # Automatically apply the filter
            self.apply_schedule_filter()
        else:
            self.view.schedule_status_label.setText("No device selected")

    def on_scheduler_table_cell_clicked(self, row, column):
        """Handle table cell clicks."""
        try:
            # Double-check for duplicate widgets and remove them
            cell_widget = self.view.scheduler_table.cellWidget(row, 0)
            if cell_widget:
                # Remove the widget if it exists - this addresses the duplicate checkbox issue
                self.view.scheduler_table.removeCellWidget(row, 0)
                logging.debug(f"Removed duplicate cell widget in row {row}, column 0")
            
            # Use temporary signal blocking to avoid triggering recursive updates
            self.view.scheduler_table.blockSignals(True)
            
            # Clear all checkboxes (for single selection mode)
            for r in range(self.view.scheduler_table.rowCount()):
                checkbox_item = self.view.scheduler_table.item(r, 0)
                if checkbox_item and r != row:
                    checkbox_item.setCheckState(Qt.CheckState.Unchecked)
            
            # Toggle the clicked checkbox if column 0
            if column == 0:
                checkbox_item = self.view.scheduler_table.item(row, 0)
                if checkbox_item:
                    # Toggle state
                    new_state = Qt.CheckState.Checked if checkbox_item.checkState() == Qt.CheckState.Unchecked else Qt.CheckState.Unchecked
                    checkbox_item.setCheckState(new_state)
                    
                    # Select the row if checkbox is checked
                    if new_state == Qt.CheckState.Checked:
                        self.view.scheduler_table.selectRow(row)
                    else:
                        # Only clear selection if we're unchecking
                        self.view.scheduler_table.clearSelection()
            else:
                # For any other column click, select the row and check its checkbox
                self.view.scheduler_table.selectRow(row)
                checkbox_item = self.view.scheduler_table.item(row, 0)
                if checkbox_item:
                    checkbox_item.setCheckState(Qt.CheckState.Checked)
            
            # Re-enable signals
            self.view.scheduler_table.blockSignals(False)
        except Exception as e:
            logging.error(f"Error handling cell click: {str(e)}")
