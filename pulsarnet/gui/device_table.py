"""DeviceTable class for displaying network devices in PulsarNet."""

from PyQt6.QtWidgets import QTableWidget, QTableWidgetItem, QCheckBox
from PyQt6.QtCore import Qt

class DeviceTable(QTableWidget):
    """Table widget for displaying network devices."""

    def __init__(self, parent=None):
        """Initialize the device table.
        
        Args:
            parent: Parent widget
        """
        super().__init__(parent)
        self.init_table()

    def init_table(self):
        """Initialize table properties."""
        # Set column headers
        self.setColumnCount(6)
        self.setHorizontalHeaderLabels([
            'Select', 'Name', 'IP Address', 'Type', 'Status', 'Last Seen'
        ])
        
        # Set table properties
        self.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.setSelectionMode(QTableWidget.SelectionMode.SingleSelection)
        self.horizontalHeader().setStretchLastSection(True)