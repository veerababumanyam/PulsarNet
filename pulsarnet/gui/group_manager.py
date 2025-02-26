"""
Module handling group management UI operations
"""

from PyQt6.QtWidgets import (
    QMessageBox, QTableWidget, QCheckBox,
    QTableWidgetItem
)
from PyQt6.QtCore import Qt

from pulsarnet.device_management.device_manager import DeviceManager


class GroupManager:
    """Handler for group-related GUI operations"""
    
    def __init__(self, main_window):
        """Initialize with reference to main window for UI access"""
        self.main_window = main_window
        self.device_manager = main_window.device_manager
    
    def get_selected_groups(self, groups_table):
        """
        Get selected groups from the groups table
        
        Args:
            groups_table (QTableWidget): The table containing groups
            
        Returns:
            list: List of selected group names
        """
        selected_groups = []
        
        # Check the number of rows
        print(f"Checking {groups_table.rowCount()} rows for selected groups")
        
        for row in range(groups_table.rowCount()):
            # Try both types of checkboxes
            # 1. QTableWidgetItem checkbox
            checkbox = groups_table.item(row, 0)
            group_name = None
            
            if checkbox:
                print(f"Row {row}: QTableWidgetItem checkbox state: {checkbox.checkState()}")
            
            if checkbox and checkbox.checkState() == Qt.CheckState.Checked:
                group_name = groups_table.item(row, 1).text()
                print(f"Found selected group via checkbox: {group_name}")
                selected_groups.append(group_name)
                continue
            
            # 2. QCheckBox widget
            cell_widget = groups_table.cellWidget(row, 0)
            if isinstance(cell_widget, QCheckBox):
                print(f"Row {row}: QCheckBox widget checked: {cell_widget.isChecked()}")
                if cell_widget.isChecked():
                    group_name = groups_table.item(row, 1).text()
                    print(f"Found selected group via QCheckBox: {group_name}")
                    selected_groups.append(group_name)
        
        print(f"Selected groups: {selected_groups}")
        return selected_groups
    
    def remove_groups(self, groups_table):
        """
        Remove selected groups
        
        Args:
            groups_table (QTableWidget): The table containing groups
            
        Returns:
            bool: Whether groups were successfully removed
        """
        if not groups_table:
            return False
            
        try:
            # Get selected groups
            selected_groups = self.get_selected_groups(groups_table)
            
            if not selected_groups:
                QMessageBox.warning(
                    self.main_window, 
                    'No Group Selected', 
                    'Please select at least one group to remove by checking the box.'
                )
                return False
            
            # Confirm deletion
            if QMessageBox.question(
                self.main_window,
                "Confirm Group Deletion",
                f"Are you sure you want to delete {len(selected_groups)} group(s)?\n\n"
                "This will not delete the devices themselves, only the group.\n"
                "This action cannot be undone.",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            ) != QMessageBox.StandardButton.Yes:
                return False
                
            # Delete each selected group
            for group_name in selected_groups:
                if group_name in self.device_manager.groups:
                    del self.device_manager.groups[group_name]
                    
            # Save changes to disk
            self.device_manager.save_groups()
            
            # Show success message
            QMessageBox.information(
                self.main_window,
                "Groups Deleted",
                f"{len(selected_groups)} group(s) have been deleted successfully.",
                QMessageBox.StandardButton.Ok
            )
            
            return True
            
        except Exception as e:
            QMessageBox.critical(
                self.main_window,
                "Error Deleting Groups",
                f"An error occurred while deleting groups: {str(e)}",
                QMessageBox.StandardButton.Ok
            )
            return False
    
    def remove_devices_from_group(self, groups_table, group_members_table):
        """
        Remove selected devices from the selected group
        
        Args:
            groups_table (QTableWidget): The table containing groups
            group_members_table (QTableWidget): The table containing group members
            
        Returns:
            bool: Whether devices were successfully removed from the group
        """
        if not groups_table or not group_members_table:
            return False
            
        # Get the selected group (three ways to check):
        # 1. First check for selected rows in selection model
        # 2. Then check for checked boxes in the first column
        # 3. Finally check for any selected items
        group_name = None
        
        # Method 1: Check selection model
        selected_indexes = groups_table.selectionModel().selectedRows()
        if selected_indexes:
            row = selected_indexes[0].row()
            group_name_item = groups_table.item(row, 1)
            if group_name_item:
                group_name = group_name_item.text()
        
        # Method 2: Check checkboxes if no selection found
        if not group_name:
            selected_groups = self.get_selected_groups(groups_table)
            if selected_groups:
                group_name = selected_groups[0]
        
        # If still no group selected, show warning
        if not group_name or group_name not in self.device_manager.groups:
            QMessageBox.warning(
                self.main_window, 
                'No Group Selected', 
                'Please select a group to remove devices from.'
            )
            return False
        
        # Get selected devices from group members table
        selected_devices = []
         
        # First check for directly selected items
        for row in range(group_members_table.rowCount()):
            # Get device name from column 1 (it's in different columns depending on table structure)
            device_item = group_members_table.item(row, 1)  # Use column 1 which contains device name
            if device_item and group_members_table.isItemSelected(device_item):
                device_name = device_item.text()
                if device_name:
                    selected_devices.append(device_name)
        
        if not selected_devices:
            QMessageBox.warning(
                self.main_window, 
                'No Devices Selected', 
                'Please select at least one device to remove from the group.'
            )
            return False
        
        # Confirm with user
        confirm = QMessageBox.question(
            self.main_window,
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
            return True
        
        return False
