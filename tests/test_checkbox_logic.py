"""
Tests specifically for the checkbox detection logic
"""

import unittest
import sys
import os

# Add project root to the path to ensure imports work correctly
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from PyQt6.QtWidgets import QApplication, QTableWidgetItem, QTableWidget, QCheckBox
from PyQt6.QtCore import Qt

class TestCheckboxLogic(unittest.TestCase):
    """Tests for checkbox detection in tables"""
    
    @classmethod
    def setUpClass(cls):
        # Create QApplication instance for all tests
        cls.app = QApplication.instance() or QApplication(sys.argv)
    
    def setUp(self):
        # Create test tables
        self.setup_test_tables()
    
    def setup_test_tables(self):
        """Set up test tables with both types of checkboxes"""
        # Create table with QTableWidgetItem checkboxes
        self.table_with_item_checkboxes = QTableWidget()
        self.table_with_item_checkboxes.setColumnCount(3)
        self.table_with_item_checkboxes.setRowCount(3)
        
        # Add data with QTableWidgetItem checkboxes
        for row in range(3):
            # Create checkbox as QTableWidgetItem
            checkbox = QTableWidgetItem()
            checkbox.setFlags(Qt.ItemFlag.ItemIsUserCheckable | Qt.ItemFlag.ItemIsEnabled)
            checkbox.setCheckState(Qt.CheckState.Unchecked if row != 1 else Qt.CheckState.Checked)
            self.table_with_item_checkboxes.setItem(row, 0, checkbox)
            
            # Set name and value
            self.table_with_item_checkboxes.setItem(row, 1, QTableWidgetItem(f"Item {row+1}"))
            self.table_with_item_checkboxes.setItem(row, 2, QTableWidgetItem(f"Value {row+1}"))
        
        # Create table with QCheckBox widgets
        self.table_with_widget_checkboxes = QTableWidget()
        self.table_with_widget_checkboxes.setColumnCount(3)
        self.table_with_widget_checkboxes.setRowCount(3)
        
        # Add data with QCheckBox widgets
        for row in range(3):
            # Create checkbox as QCheckBox
            checkbox = QCheckBox()
            checkbox.setChecked(row == 1)  # Check the second row
            self.table_with_widget_checkboxes.setCellWidget(row, 0, checkbox)
            
            # Set name and value
            self.table_with_widget_checkboxes.setItem(row, 1, QTableWidgetItem(f"Item {row+1}"))
            self.table_with_widget_checkboxes.setItem(row, 2, QTableWidgetItem(f"Value {row+1}"))
    
    def test_detect_qtablewidgetitem_checkbox(self):
        """Test detecting checked QTableWidgetItem checkboxes"""
        # Find checked items
        checked_items = []
        for row in range(self.table_with_item_checkboxes.rowCount()):
            checkbox = self.table_with_item_checkboxes.item(row, 0)
            if checkbox and checkbox.checkState() == Qt.CheckState.Checked:
                item_name = self.table_with_item_checkboxes.item(row, 1).text()
                checked_items.append(item_name)
        
        # Should find one checked item (row 1)
        self.assertEqual(len(checked_items), 1)
        self.assertEqual(checked_items[0], "Item 2")
    
    def test_detect_qcheckbox_widget(self):
        """Test detecting checked QCheckBox widgets"""
        # Find checked items
        checked_items = []
        for row in range(self.table_with_widget_checkboxes.rowCount()):
            cell_widget = self.table_with_widget_checkboxes.cellWidget(row, 0)
            if isinstance(cell_widget, QCheckBox) and cell_widget.isChecked():
                item_name = self.table_with_widget_checkboxes.item(row, 1).text()
                checked_items.append(item_name)
        
        # Should find one checked item (row 1)
        self.assertEqual(len(checked_items), 1)
        self.assertEqual(checked_items[0], "Item 2")
    
    def test_combined_checkbox_detection(self):
        """Test a function that can detect both types of checkboxes"""
        
        def find_checked_items(table):
            """Generic function to find checked items in a table
            regardless of checkbox type"""
            checked_items = []
            for row in range(table.rowCount()):
                # Check for QTableWidgetItem checkbox
                checkbox_item = table.item(row, 0)
                if checkbox_item and checkbox_item.checkState() == Qt.CheckState.Checked:
                    item_name = table.item(row, 1).text()
                    checked_items.append(item_name)
                    continue
                
                # Check for QCheckBox widget
                cell_widget = table.cellWidget(row, 0)
                if isinstance(cell_widget, QCheckBox) and cell_widget.isChecked():
                    item_name = table.item(row, 1).text()
                    checked_items.append(item_name)
            
            return checked_items
        
        # Test on QTableWidgetItem checkboxes
        checked_items1 = find_checked_items(self.table_with_item_checkboxes)
        self.assertEqual(len(checked_items1), 1)
        self.assertEqual(checked_items1[0], "Item 2")
        
        # Test on QCheckBox widgets
        checked_items2 = find_checked_items(self.table_with_widget_checkboxes)
        self.assertEqual(len(checked_items2), 1)
        self.assertEqual(checked_items2[0], "Item 2")

if __name__ == '__main__':
    unittest.main()
