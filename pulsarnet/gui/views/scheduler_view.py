"""Scheduler Tab View for PulsarNet GUI.

This module provides the view components for the scheduler configuration tab.
"""

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QFormLayout, 
    QLineEdit, QPushButton, QComboBox, QSpinBox, 
    QGroupBox, QFileDialog, QTableWidget, QTableWidgetItem,
    QLabel, QHeaderView, QCheckBox, QTimeEdit
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QBrush, QColor
from .base_view import BaseTabView

class SchedulerTabView(BaseTabView):
    """View class for the scheduler configuration tab."""
    
    def setup_ui(self):
        """Set up the UI components for the scheduler tab."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(10)
        
        # Filter panel
        filter_panel = QGroupBox("Schedule Filter Options")
        filter_panel.setObjectName("Schedule Filter Options")
        filter_panel_layout = QVBoxLayout()
        
        # Filter type
        filter_type_layout = QHBoxLayout()
        filter_type_label = QLabel("Filter Type:")
        filter_type_label.setToolTip("Select how to filter schedules")
        filter_type_layout.addWidget(filter_type_label)
        
        self.schedule_filter_combo = QComboBox()
        self.schedule_filter_combo.addItems(["All Schedules", "By Group", "By Device"])
        self.schedule_filter_combo.setToolTip("Choose which schedules to display")
        self.schedule_filter_combo.setMinimumWidth(200)
        filter_type_layout.addWidget(self.schedule_filter_combo)
        filter_panel_layout.addLayout(filter_type_layout)
        
        # Group selection combo (enabled only when 'By Group' is selected)
        group_layout = QHBoxLayout()
        self.group_label = QLabel("Group:")
        self.group_label.setToolTip("Select a specific device group")
        group_layout.addWidget(self.group_label)
        
        self.schedule_group_combo = QComboBox()
        self.schedule_group_combo.addItem("Select Group")
        self.schedule_group_combo.setToolTip("Select a device group to filter schedules")
        self.schedule_group_combo.setMinimumWidth(200)
        self.schedule_group_combo.setEnabled(False)
        group_layout.addWidget(self.schedule_group_combo)
        filter_panel_layout.addLayout(group_layout)
        
        # Status display
        status_layout = QHBoxLayout()
        self.schedule_status_label = QLabel("Current Status: Showing all schedules")
        self.schedule_status_label.setToolTip("Shows information about the current selection")
        status_layout.addWidget(self.schedule_status_label)
        filter_panel_layout.addLayout(status_layout)
        
        filter_panel.setLayout(filter_panel_layout)
        layout.addWidget(filter_panel)
        
        # Controls
        controls = QHBoxLayout()
        controls.setSpacing(8)
        
        self.add_schedule_btn = QPushButton('Add Schedule')
        self.add_schedule_btn.setToolTip('Create a new backup schedule for devices or groups')
        controls.addWidget(self.add_schedule_btn)
        
        self.edit_schedule_btn = QPushButton('Edit Schedule')
        self.edit_schedule_btn.setToolTip('Edit the selected schedule (select a row or check the box)')
        controls.addWidget(self.edit_schedule_btn)
        
        self.remove_schedule_btn = QPushButton('Remove Schedule')
        self.remove_schedule_btn.setToolTip('Remove the selected schedule (select a row or check the box)')
        controls.addWidget(self.remove_schedule_btn)
        
        controls.addStretch()
        
        self.refresh_btn = QPushButton('Refresh')
        self.refresh_btn.setToolTip('Refresh schedule list')
        controls.addWidget(self.refresh_btn)
        
        layout.addLayout(controls)
        
        # Schedule table
        self.scheduler_table = QTableWidget()
        self.scheduler_table.setColumnCount(6)
        self.scheduler_table.setHorizontalHeaderLabels([
            'Select', 'Name', 'Type', 'Targets', 'Next Run', 'Last Run'
        ])
        
        # Set column widths
        header = self.scheduler_table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.Fixed)  # Checkbox
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)  # Name
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)  # Type
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.Stretch)  # Targets
        header.setSectionResizeMode(4, QHeaderView.ResizeMode.Stretch)  # Next Run
        header.setSectionResizeMode(5, QHeaderView.ResizeMode.Stretch)  # Last Run
        
        self.scheduler_table.setColumnWidth(0, 50)  # Checkbox
        
        self.scheduler_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.scheduler_table.setSelectionMode(QTableWidget.SelectionMode.SingleSelection)
        self.scheduler_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        layout.addWidget(self.scheduler_table)
        
        self.setLayout(layout)
