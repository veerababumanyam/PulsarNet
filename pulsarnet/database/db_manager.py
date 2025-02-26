"""Database manager module for PulsarNet.

This module provides a central interface for database operations using
SQLite with asynchronous access.
"""

import os
import json
import sqlite3
import asyncio
import logging
from typing import List, Dict, Any, Optional, Tuple, Union
from pathlib import Path
import aiosqlite
import datetime


class DatabaseManager:
    """Manager for SQLite database operations."""
    
    def __init__(self, db_path: str = None):
        """Initialize the database manager.
        
        Args:
            db_path: Path to the database file
        """
        self.db_path = db_path or os.path.join(
            os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), 
            'data', 
            'pulsarnet.db'
        )
        self.logger = logging.getLogger("pulsarnet.database")
        self.connection = None
        
        # Create directory if it doesn't exist
        db_dir = os.path.dirname(self.db_path)
        if not os.path.exists(db_dir):
            os.makedirs(db_dir)
    
    async def initialize(self):
        """Initialize the database connection and schema."""
        try:
            # Create database directory if it doesn't exist
            db_dir = os.path.dirname(self.db_path)
            os.makedirs(db_dir, exist_ok=True)
            
            # Connect to database
            self.connection = await aiosqlite.connect(self.db_path)
            
            # Enable foreign keys
            await self.connection.execute("PRAGMA foreign_keys = ON")
            
            # Load schema
            schema_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "schema.sql")
            with open(schema_path, "r") as f:
                schema = f.read()
                
            # Execute schema
            await self.connection.executescript(schema)
            await self.connection.commit()
            
            self.logger.info(f"Database initialized at {self.db_path}")
            return True
        except Exception as e:
            self.logger.error(f"Failed to initialize database: {e}")
            if self.connection:
                await self.connection.close()
                self.connection = None
            return False
    
    async def close(self):
        """Close the database connection."""
        if self.connection:
            await self.connection.close()
            self.connection = None
            self.logger.info("Database connection closed")
    
    async def execute_query(self, query: str, params: tuple = ()):
        """Execute a SQL query.
        
        Args:
            query: SQL query string
            params: Query parameters
            
        Returns:
            List of results or None on failure
        """
        try:
            if not self.connection:
                await self.initialize()
                
            cursor = await self.connection.execute(query, params)
            
            if query.strip().upper().startswith(("SELECT", "PRAGMA")):
                rows = await cursor.fetchall()
                await cursor.close()
                return rows
            else:
                await self.connection.commit()
                last_id = cursor.lastrowid
                await cursor.close()
                return last_id
        except Exception as e:
            self.logger.error(f"Database query error: {e}\nQuery: {query}\nParams: {params}")
            return None
    
    async def execute_script(self, script: str):
        """Execute a SQL script.
        
        Args:
            script: SQL script string
            
        Returns:
            bool: True on success, False on failure
        """
        try:
            if not self.connection:
                await self.initialize()
                
            await self.connection.executescript(script)
            await self.connection.commit()
            return True
        except Exception as e:
            self.logger.error(f"Database script error: {e}")
            return False
    
    async def get_settings(self, category: Optional[str] = None) -> Dict[str, Dict[str, str]]:
        """Get settings from the database.
        
        Args:
            category: Optional category filter
            
        Returns:
            Dict of settings
        """
        try:
            if category:
                rows = await self.execute_query(
                    "SELECT category, key, value FROM settings WHERE category = ?",
                    (category,)
                )
            else:
                rows = await self.execute_query(
                    "SELECT category, key, value FROM settings"
                )
                
            settings = {}
            for row in rows:
                cat, key, value = row
                if cat not in settings:
                    settings[cat] = {}
                    
                settings[cat][key] = value
                
            return settings
        except Exception as e:
            self.logger.error(f"Error getting settings: {e}")
            return {}
    
    async def get_setting(self, category: str, key: str, default: str = None) -> Optional[str]:
        """Get a specific setting.
        
        Args:
            category: Setting category
            key: Setting key
            default: Default value if setting doesn't exist
            
        Returns:
            Setting value or default
        """
        try:
            row = await self.execute_query(
                "SELECT value FROM settings WHERE category = ? AND key = ?",
                (category, key)
            )
            
            if row and row[0]:
                return row[0][0]
                
            return default
        except Exception as e:
            self.logger.error(f"Error getting setting {category}.{key}: {e}")
            return default
    
    async def set_setting(self, category: str, key: str, value: str, description: Optional[str] = None) -> bool:
        """Set a specific setting.
        
        Args:
            category: Setting category
            key: Setting key
            value: Setting value
            description: Optional setting description
            
        Returns:
            bool: True on success, False on failure
        """
        try:
            # Check if setting exists
            exists = await self.execute_query(
                "SELECT 1 FROM settings WHERE category = ? AND key = ?",
                (category, key)
            )
            
            if exists:
                # Update existing setting
                await self.execute_query(
                    "UPDATE settings SET value = ?, updated_at = CURRENT_TIMESTAMP WHERE category = ? AND key = ?",
                    (value, category, key)
                )
            else:
                # Insert new setting
                await self.execute_query(
                    "INSERT INTO settings (category, key, value, description) VALUES (?, ?, ?, ?)",
                    (category, key, value, description)
                )
                
            return True
        except Exception as e:
            self.logger.error(f"Error setting {category}.{key}: {e}")
            return False
    
    # Device methods
    async def get_devices(self) -> List[Dict[str, Any]]:
        """Get all devices.
        
        Returns:
            List of device dictionaries
        """
        try:
            rows = await self.execute_query(
                "SELECT id, name, ip_address, device_type, username, password, enable_password, "
                "connection_type, port, use_jump_server, jump_server, jump_username, jump_password, "
                "backup_enabled, verify_backup, created_at, updated_at, last_backup_time, "
                "last_backup_status, last_backup_path, notes "
                "FROM devices"
            )
            
            devices = []
            for row in rows:
                devices.append({
                    'id': row[0],
                    'name': row[1],
                    'ip_address': row[2],
                    'device_type': row[3],
                    'username': row[4],
                    'password': row[5],
                    'enable_password': row[6],
                    'connection_type': row[7],
                    'port': row[8],
                    'use_jump_server': bool(row[9]),
                    'jump_server': row[10],
                    'jump_username': row[11],
                    'jump_password': row[12],
                    'backup_enabled': bool(row[13]),
                    'verify_backup': bool(row[14]),
                    'created_at': row[15],
                    'updated_at': row[16],
                    'last_backup_time': row[17],
                    'last_backup_status': row[18],
                    'last_backup_path': row[19],
                    'notes': row[20]
                })
                
            return devices
        except Exception as e:
            self.logger.error(f"Error getting devices: {e}")
            return []
    
    async def get_device(self, device_id: int) -> Optional[Dict[str, Any]]:
        """Get a specific device.
        
        Args:
            device_id: Device ID
            
        Returns:
            Device dictionary or None if not found
        """
        try:
            row = await self.execute_query(
                "SELECT id, name, ip_address, device_type, username, password, enable_password, "
                "connection_type, port, use_jump_server, jump_server, jump_username, jump_password, "
                "backup_enabled, verify_backup, created_at, updated_at, last_backup_time, "
                "last_backup_status, last_backup_path, notes "
                "FROM devices WHERE id = ?",
                (device_id,)
            )
            
            if not row:
                return None
                
            row = row[0]
            
            return {
                'id': row[0],
                'name': row[1],
                'ip_address': row[2],
                'device_type': row[3],
                'username': row[4],
                'password': row[5],
                'enable_password': row[6],
                'connection_type': row[7],
                'port': row[8],
                'use_jump_server': bool(row[9]),
                'jump_server': row[10],
                'jump_username': row[11],
                'jump_password': row[12],
                'backup_enabled': bool(row[13]),
                'verify_backup': bool(row[14]),
                'created_at': row[15],
                'updated_at': row[16],
                'last_backup_time': row[17],
                'last_backup_status': row[18],
                'last_backup_path': row[19],
                'notes': row[20]
            }
        except Exception as e:
            self.logger.error(f"Error getting device {device_id}: {e}")
            return None
    
    async def get_device_by_name(self, name: str) -> Optional[Dict[str, Any]]:
        """Get a device by name.
        
        Args:
            name: Device name
            
        Returns:
            Device dictionary or None if not found
        """
        try:
            row = await self.execute_query(
                "SELECT id, name, ip_address, device_type, username, password, enable_password, "
                "connection_type, port, use_jump_server, jump_server, jump_username, jump_password, "
                "backup_enabled, verify_backup, created_at, updated_at, last_backup_time, "
                "last_backup_status, last_backup_path, notes "
                "FROM devices WHERE name = ?",
                (name,)
            )
            
            if not row:
                return None
                
            row = row[0]
            
            return {
                'id': row[0],
                'name': row[1],
                'ip_address': row[2],
                'device_type': row[3],
                'username': row[4],
                'password': row[5],
                'enable_password': row[6],
                'connection_type': row[7],
                'port': row[8],
                'use_jump_server': bool(row[9]),
                'jump_server': row[10],
                'jump_username': row[11],
                'jump_password': row[12],
                'backup_enabled': bool(row[13]),
                'verify_backup': bool(row[14]),
                'created_at': row[15],
                'updated_at': row[16],
                'last_backup_time': row[17],
                'last_backup_status': row[18],
                'last_backup_path': row[19],
                'notes': row[20]
            }
        except Exception as e:
            self.logger.error(f"Error getting device by name {name}: {e}")
            return None
    
    async def add_device(self, device_data: Dict[str, Any]) -> Optional[int]:
        """Add a new device.
        
        Args:
            device_data: Device data dictionary
            
        Returns:
            New device ID or None on failure
        """
        try:
            # Extract device data
            name = device_data.get('name')
            ip_address = device_data.get('ip_address')
            device_type = device_data.get('device_type')
            username = device_data.get('username')
            password = device_data.get('password')
            enable_password = device_data.get('enable_password')
            connection_type = device_data.get('connection_type', 'ssh')
            port = device_data.get('port', 22)
            use_jump_server = 1 if device_data.get('use_jump_server') else 0
            jump_server = device_data.get('jump_server')
            jump_username = device_data.get('jump_username')
            jump_password = device_data.get('jump_password')
            backup_enabled = 1 if device_data.get('backup_enabled', True) else 0
            verify_backup = 1 if device_data.get('verify_backup', True) else 0
            notes = device_data.get('notes')
            
            # Insert device
            device_id = await self.execute_query(
                "INSERT INTO devices (name, ip_address, device_type, username, password, enable_password, "
                "connection_type, port, use_jump_server, jump_server, jump_username, jump_password, "
                "backup_enabled, verify_backup, notes) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (name, ip_address, device_type, username, password, enable_password, 
                 connection_type, port, use_jump_server, jump_server, jump_username, 
                 jump_password, backup_enabled, verify_backup, notes)
            )
            
            return device_id
        except Exception as e:
            self.logger.error(f"Error adding device: {e}")
            return None
    
    async def update_device(self, device_id: int, device_data: Dict[str, Any]) -> bool:
        """Update an existing device.
        
        Args:
            device_id: Device ID
            device_data: Device data dictionary
            
        Returns:
            bool: True on success, False on failure
        """
        try:
            # Extract device data
            updates = []
            params = []
            
            for key, value in device_data.items():
                if key in ('id', 'created_at', 'updated_at', 'last_backup_time', 'last_backup_status', 'last_backup_path'):
                    continue  # Skip these fields
                    
                if key in ('use_jump_server', 'backup_enabled', 'verify_backup'):
                    value = 1 if value else 0
                    
                updates.append(f"{key} = ?")
                params.append(value)
                
            # Add updated_at timestamp
            updates.append("updated_at = CURRENT_TIMESTAMP")
            
            # Add device ID
            params.append(device_id)
            
            # Update device
            await self.execute_query(
                f"UPDATE devices SET {', '.join(updates)} WHERE id = ?",
                tuple(params)
            )
            
            return True
        except Exception as e:
            self.logger.error(f"Error updating device {device_id}: {e}")
            return False
    
    async def delete_device(self, device_id: int) -> bool:
        """Delete a device.
        
        Args:
            device_id: Device ID
            
        Returns:
            bool: True on success, False on failure
        """
        try:
            await self.execute_query(
                "DELETE FROM devices WHERE id = ?",
                (device_id,)
            )
            
            return True
        except Exception as e:
            self.logger.error(f"Error deleting device {device_id}: {e}")
            return False
    
    async def update_device_backup_status(self, device_id: int, status: str, path: Optional[str] = None) -> bool:
        """Update device backup status.
        
        Args:
            device_id: Device ID
            status: Backup status
            path: Backup file path
            
        Returns:
            bool: True on success, False on failure
        """
        try:
            if path:
                await self.execute_query(
                    "UPDATE devices SET last_backup_time = CURRENT_TIMESTAMP, "
                    "last_backup_status = ?, last_backup_path = ? WHERE id = ?",
                    (status, path, device_id)
                )
            else:
                await self.execute_query(
                    "UPDATE devices SET last_backup_time = CURRENT_TIMESTAMP, "
                    "last_backup_status = ? WHERE id = ?",
                    (status, device_id)
                )
                
            return True
        except Exception as e:
            self.logger.error(f"Error updating device backup status for {device_id}: {e}")
            return False
    
    # Group methods
    async def get_groups(self) -> List[Dict[str, Any]]:
        """Get all device groups.
        
        Returns:
            List of group dictionaries
        """
        try:
            rows = await self.execute_query(
                "SELECT id, name, description, created_at, updated_at FROM device_groups"
            )
            
            groups = []
            for row in rows:
                # Get devices in group
                device_rows = await self.execute_query(
                    "SELECT d.id, d.name FROM devices d "
                    "JOIN device_group_mappings m ON d.id = m.device_id "
                    "WHERE m.group_id = ?",
                    (row[0],)
                )
                
                devices = [{'id': dr[0], 'name': dr[1]} for dr in device_rows]
                
                groups.append({
                    'id': row[0],
                    'name': row[1],
                    'description': row[2],
                    'created_at': row[3],
                    'updated_at': row[4],
                    'devices': devices
                })
                
            return groups
        except Exception as e:
            self.logger.error(f"Error getting groups: {e}")
            return []
    
    async def get_group(self, group_id: int) -> Optional[Dict[str, Any]]:
        """Get a specific device group.
        
        Args:
            group_id: Group ID
            
        Returns:
            Group dictionary or None if not found
        """
        try:
            row = await self.execute_query(
                "SELECT id, name, description, created_at, updated_at FROM device_groups WHERE id = ?",
                (group_id,)
            )
            
            if not row:
                return None
                
            row = row[0]
            
            # Get devices in group
            device_rows = await self.execute_query(
                "SELECT d.id, d.name FROM devices d "
                "JOIN device_group_mappings m ON d.id = m.device_id "
                "WHERE m.group_id = ?",
                (group_id,)
            )
            
            devices = [{'id': dr[0], 'name': dr[1]} for dr in device_rows]
            
            return {
                'id': row[0],
                'name': row[1],
                'description': row[2],
                'created_at': row[3],
                'updated_at': row[4],
                'devices': devices
            }
        except Exception as e:
            self.logger.error(f"Error getting group {group_id}: {e}")
            return None
    
    async def add_group(self, group_data: Dict[str, Any]) -> Optional[int]:
        """Add a new device group.
        
        Args:
            group_data: Group data dictionary
            
        Returns:
            New group ID or None on failure
        """
        try:
            # Extract group data
            name = group_data.get('name')
            description = group_data.get('description')
            
            # Insert group
            group_id = await self.execute_query(
                "INSERT INTO device_groups (name, description) VALUES (?, ?)",
                (name, description)
            )
            
            # Add devices if specified
            devices = group_data.get('devices', [])
            for device_id in devices:
                await self.execute_query(
                    "INSERT INTO device_group_mappings (device_id, group_id) VALUES (?, ?)",
                    (device_id, group_id)
                )
                
            return group_id
        except Exception as e:
            self.logger.error(f"Error adding group: {e}")
            return None
    
    async def update_group(self, group_id: int, group_data: Dict[str, Any]) -> bool:
        """Update an existing device group.
        
        Args:
            group_id: Group ID
            group_data: Group data dictionary
            
        Returns:
            bool: True on success, False on failure
        """
        try:
            # Extract group data
            updates = []
            params = []
            
            for key, value in group_data.items():
                if key in ('id', 'created_at', 'updated_at', 'devices'):
                    continue  # Skip these fields
                    
                updates.append(f"{key} = ?")
                params.append(value)
                
            # Add updated_at timestamp
            updates.append("updated_at = CURRENT_TIMESTAMP")
            
            # Add group ID
            params.append(group_id)
            
            # Update group
            if updates:
                await self.execute_query(
                    f"UPDATE device_groups SET {', '.join(updates)} WHERE id = ?",
                    tuple(params)
                )
            
            # Update devices if specified
            if 'devices' in group_data:
                # Remove existing mappings
                await self.execute_query(
                    "DELETE FROM device_group_mappings WHERE group_id = ?",
                    (group_id,)
                )
                
                # Add new mappings
                for device_id in group_data['devices']:
                    await self.execute_query(
                        "INSERT INTO device_group_mappings (device_id, group_id) VALUES (?, ?)",
                        (device_id, group_id)
                    )
                    
            return True
        except Exception as e:
            self.logger.error(f"Error updating group {group_id}: {e}")
            return False
    
    async def delete_group(self, group_id: int) -> bool:
        """Delete a device group.
        
        Args:
            group_id: Group ID
            
        Returns:
            bool: True on success, False on failure
        """
        try:
            # Delete group mappings (cascade should handle this, but do it explicitly anyway)
            await self.execute_query(
                "DELETE FROM device_group_mappings WHERE group_id = ?",
                (group_id,)
            )
            
            # Delete group
            await self.execute_query(
                "DELETE FROM device_groups WHERE id = ?",
                (group_id,)
            )
            
            return True
        except Exception as e:
            self.logger.error(f"Error deleting group {group_id}: {e}")
            return False
    
    # Backup methods
    async def get_backups(self, device_id: Optional[int] = None) -> List[Dict[str, Any]]:
        """Get backup records.
        
        Args:
            device_id: Optional device ID to filter by
            
        Returns:
            List of backup dictionaries
        """
        try:
            if device_id:
                rows = await self.execute_query(
                    "SELECT id, device_id, backup_type, file_path, file_size, "
                    "checksum, verification_status, created_at, notes "
                    "FROM backups WHERE device_id = ? ORDER BY created_at DESC",
                    (device_id,)
                )
            else:
                rows = await self.execute_query(
                    "SELECT id, device_id, backup_type, file_path, file_size, "
                    "checksum, verification_status, created_at, notes "
                    "FROM backups ORDER BY created_at DESC"
                )
                
            backups = []
            for row in rows:
                backups.append({
                    'id': row[0],
                    'device_id': row[1],
                    'backup_type': row[2],
                    'file_path': row[3],
                    'file_size': row[4],
                    'checksum': row[5],
                    'verification_status': row[6],
                    'created_at': row[7],
                    'notes': row[8]
                })
                
            return backups
        except Exception as e:
            self.logger.error(f"Error getting backups: {e}")
            return []
    
    async def add_backup(self, backup_data: Dict[str, Any]) -> Optional[int]:
        """Add a new backup record.
        
        Args:
            backup_data: Backup data dictionary
            
        Returns:
            New backup ID or None on failure
        """
        try:
            # Extract backup data
            device_id = backup_data.get('device_id')
            backup_type = backup_data.get('backup_type')
            file_path = backup_data.get('file_path')
            file_size = backup_data.get('file_size')
            checksum = backup_data.get('checksum')
            verification_status = backup_data.get('verification_status')
            notes = backup_data.get('notes')
            
            # Insert backup
            backup_id = await self.execute_query(
                "INSERT INTO backups (device_id, backup_type, file_path, file_size, "
                "checksum, verification_status, notes) "
                "VALUES (?, ?, ?, ?, ?, ?, ?)",
                (device_id, backup_type, file_path, file_size, checksum, verification_status, notes)
            )
            
            return backup_id
        except Exception as e:
            self.logger.error(f"Error adding backup: {e}")
            return None
    
    async def update_backup_verification(self, backup_id: int, status: str, checksum: Optional[str] = None) -> bool:
        """Update backup verification status.
        
        Args:
            backup_id: Backup ID
            status: Verification status
            checksum: Optional checksum value
            
        Returns:
            bool: True on success, False on failure
        """
        try:
            if checksum:
                await self.execute_query(
                    "UPDATE backups SET verification_status = ?, checksum = ? WHERE id = ?",
                    (status, checksum, backup_id)
                )
            else:
                await self.execute_query(
                    "UPDATE backups SET verification_status = ? WHERE id = ?",
                    (status, backup_id)
                )
                
            return True
        except Exception as e:
            self.logger.error(f"Error updating backup verification for {backup_id}: {e}")
            return False
    
    # Schedule methods
    async def get_schedules(self) -> List[Dict[str, Any]]:
        """Get all schedules.
        
        Returns:
            List of schedule dictionaries
        """
        try:
            rows = await self.execute_query(
                "SELECT id, name, description, schedule_type, priority, enabled, "
                "start_time, days_of_week, days_of_month, months, last_run, next_run, "
                "target_type, target_id, created_at, updated_at "
                "FROM schedules ORDER BY priority DESC"
            )
            
            schedules = []
            for row in rows:
                schedules.append({
                    'id': row[0],
                    'name': row[1],
                    'description': row[2],
                    'schedule_type': row[3],
                    'priority': row[4],
                    'enabled': bool(row[5]),
                    'start_time': row[6],
                    'days_of_week': row[7],
                    'days_of_month': row[8],
                    'months': row[9],
                    'last_run': row[10],
                    'next_run': row[11],
                    'target_type': row[12],
                    'target_id': row[13],
                    'created_at': row[14],
                    'updated_at': row[15]
                })
                
            return schedules
        except Exception as e:
            self.logger.error(f"Error getting schedules: {e}")
            return []
    
    async def get_schedule(self, schedule_id: int) -> Optional[Dict[str, Any]]:
        """Get a specific schedule.
        
        Args:
            schedule_id: Schedule ID
            
        Returns:
            Schedule dictionary or None if not found
        """
        try:
            row = await self.execute_query(
                "SELECT id, name, description, schedule_type, priority, enabled, "
                "start_time, days_of_week, days_of_month, months, last_run, next_run, "
                "target_type, target_id, created_at, updated_at "
                "FROM schedules WHERE id = ?",
                (schedule_id,)
            )
            
            if not row:
                return None
                
            row = row[0]
            
            return {
                'id': row[0],
                'name': row[1],
                'description': row[2],
                'schedule_type': row[3],
                'priority': row[4],
                'enabled': bool(row[5]),
                'start_time': row[6],
                'days_of_week': row[7],
                'days_of_month': row[8],
                'months': row[9],
                'last_run': row[10],
                'next_run': row[11],
                'target_type': row[12],
                'target_id': row[13],
                'created_at': row[14],
                'updated_at': row[15]
            }
        except Exception as e:
            self.logger.error(f"Error getting schedule {schedule_id}: {e}")
            return None
    
    async def get_due_schedules(self) -> List[Dict[str, Any]]:
        """Get schedules that are due to run.
        
        Returns:
            List of due schedule dictionaries
        """
        try:
            now = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            
            rows = await self.execute_query(
                "SELECT id, name, description, schedule_type, priority, enabled, "
                "start_time, days_of_week, days_of_month, months, last_run, next_run, "
                "target_type, target_id, created_at, updated_at "
                "FROM schedules WHERE enabled = 1 AND next_run <= ? "
                "ORDER BY priority DESC",
                (now,)
            )
            
            schedules = []
            for row in rows:
                schedules.append({
                    'id': row[0],
                    'name': row[1],
                    'description': row[2],
                    'schedule_type': row[3],
                    'priority': row[4],
                    'enabled': bool(row[5]),
                    'start_time': row[6],
                    'days_of_week': row[7],
                    'days_of_month': row[8],
                    'months': row[9],
                    'last_run': row[10],
                    'next_run': row[11],
                    'target_type': row[12],
                    'target_id': row[13],
                    'created_at': row[14],
                    'updated_at': row[15]
                })
                
            return schedules
        except Exception as e:
            self.logger.error(f"Error getting due schedules: {e}")
            return []
    
    async def add_schedule(self, schedule_data: Dict[str, Any]) -> Optional[int]:
        """Add a new schedule.
        
        Args:
            schedule_data: Schedule data dictionary
            
        Returns:
            New schedule ID or None on failure
        """
        try:
            # Extract schedule data
            name = schedule_data.get('name')
            description = schedule_data.get('description')
            schedule_type = schedule_data.get('schedule_type')
            priority = schedule_data.get('priority', 1)
            enabled = 1 if schedule_data.get('enabled', True) else 0
            start_time = schedule_data.get('start_time')
            days_of_week = schedule_data.get('days_of_week')
            days_of_month = schedule_data.get('days_of_month')
            months = schedule_data.get('months')
            next_run = schedule_data.get('next_run')
            target_type = schedule_data.get('target_type')
            target_id = schedule_data.get('target_id')
            
            # Insert schedule
            schedule_id = await self.execute_query(
                "INSERT INTO schedules (name, description, schedule_type, priority, "
                "enabled, start_time, days_of_week, days_of_month, months, next_run, "
                "target_type, target_id) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (name, description, schedule_type, priority, enabled, start_time, 
                 days_of_week, days_of_month, months, next_run, target_type, target_id)
            )
            
            return schedule_id
        except Exception as e:
            self.logger.error(f"Error adding schedule: {e}")
            return None
    
    async def update_schedule(self, schedule_id: int, schedule_data: Dict[str, Any]) -> bool:
        """Update an existing schedule.
        
        Args:
            schedule_id: Schedule ID
            schedule_data: Schedule data dictionary
            
        Returns:
            bool: True on success, False on failure
        """
        try:
            # Extract schedule data
            updates = []
            params = []
            
            for key, value in schedule_data.items():
                if key in ('id', 'created_at', 'updated_at'):
                    continue  # Skip these fields
                    
                if key == 'enabled':
                    value = 1 if value else 0
                    
                updates.append(f"{key} = ?")
                params.append(value)
                
            # Add updated_at timestamp
            updates.append("updated_at = CURRENT_TIMESTAMP")
            
            # Add schedule ID
            params.append(schedule_id)
            
            # Update schedule
            await self.execute_query(
                f"UPDATE schedules SET {', '.join(updates)} WHERE id = ?",
                tuple(params)
            )
            
            return True
        except Exception as e:
            self.logger.error(f"Error updating schedule {schedule_id}: {e}")
            return False
    
    async def delete_schedule(self, schedule_id: int) -> bool:
        """Delete a schedule.
        
        Args:
            schedule_id: Schedule ID
            
        Returns:
            bool: True on success, False on failure
        """
        try:
            await self.execute_query(
                "DELETE FROM schedules WHERE id = ?",
                (schedule_id,)
            )
            
            return True
        except Exception as e:
            self.logger.error(f"Error deleting schedule {schedule_id}: {e}")
            return False
    
    async def update_schedule_run(self, schedule_id: int, next_run: str) -> bool:
        """Update schedule run times.
        
        Args:
            schedule_id: Schedule ID
            next_run: Next run time
            
        Returns:
            bool: True on success, False on failure
        """
        try:
            now = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            
            await self.execute_query(
                "UPDATE schedules SET last_run = ?, next_run = ? WHERE id = ?",
                (now, next_run, schedule_id)
            )
            
            return True
        except Exception as e:
            self.logger.error(f"Error updating schedule run for {schedule_id}: {e}")
            return False
    
    # Log methods
    async def add_log(self, level: str, source: str, message: str, details: Optional[str] = None) -> Optional[int]:
        """Add a log entry.
        
        Args:
            level: Log level
            source: Log source
            message: Log message
            details: Optional details
            
        Returns:
            New log ID or None on failure
        """
        try:
            log_id = await self.execute_query(
                "INSERT INTO logs (level, source, message, details) VALUES (?, ?, ?, ?)",
                (level, source, message, details)
            )
            
            return log_id
        except Exception as e:
            # Don't log this to avoid recursive logging
            return None
    
    async def get_logs(self, limit: int = 100, level: Optional[str] = None) -> List[Dict[str, Any]]:
        """Get log entries.
        
        Args:
            limit: Maximum number of logs to return
            level: Optional level filter
            
        Returns:
            List of log dictionaries
        """
        try:
            if level:
                rows = await self.execute_query(
                    "SELECT id, timestamp, level, source, message, details "
                    "FROM logs WHERE level = ? ORDER BY timestamp DESC LIMIT ?",
                    (level, limit)
                )
            else:
                rows = await self.execute_query(
                    "SELECT id, timestamp, level, source, message, details "
                    "FROM logs ORDER BY timestamp DESC LIMIT ?",
                    (limit,)
                )
                
            logs = []
            for row in rows:
                logs.append({
                    'id': row[0],
                    'timestamp': row[1],
                    'level': row[2],
                    'source': row[3],
                    'message': row[4],
                    'details': row[5]
                })
                
            return logs
        except Exception as e:
            # Don't log this to avoid recursive logging
            return []
    
    # Template methods
    async def get_device_templates(self) -> List[Dict[str, Any]]:
        """Get all device templates.
        
        Returns:
            List of template dictionaries
        """
        try:
            rows = await self.execute_query(
                "SELECT id, device_type, backup_commands, connection_settings, created_at, updated_at "
                "FROM device_templates"
            )
            
            templates = []
            for row in rows:
                try:
                    backup_commands = json.loads(row[2]) if row[2] else {}
                    connection_settings = json.loads(row[3]) if row[3] else {}
                except json.JSONDecodeError:
                    self.logger.error(f"Error decoding JSON for template {row[0]}")
                    backup_commands = {}
                    connection_settings = {}
                
                templates.append({
                    'id': row[0],
                    'device_type': row[1],
                    'backup_commands': backup_commands,
                    'connection_settings': connection_settings,
                    'created_at': row[4],
                    'updated_at': row[5]
                })
                
            return templates
        except Exception as e:
            self.logger.error(f"Error getting device templates: {e}")
            return []
    
    async def add_device_template(self, template_data: Dict[str, Any]) -> Optional[int]:
        """Add a new device template.
        
        Args:
            template_data: Template data dictionary
            
        Returns:
            New template ID or None on failure
        """
        try:
            # Extract template data
            device_type = template_data.get('device_type')
            backup_commands = template_data.get('backup_commands', {})
            connection_settings = template_data.get('connection_settings', {})
            
            # Serialize JSON
            backup_commands_json = json.dumps(backup_commands)
            connection_settings_json = json.dumps(connection_settings)
            
            # Check if template already exists
            existing = await self.execute_query(
                "SELECT id FROM device_templates WHERE device_type = ?",
                (device_type,)
            )
            
            if existing:
                # Update existing template
                await self.execute_query(
                    "UPDATE device_templates SET backup_commands = ?, connection_settings = ?, "
                    "updated_at = CURRENT_TIMESTAMP WHERE device_type = ?",
                    (backup_commands_json, connection_settings_json, device_type)
                )
                
                return existing[0][0]
            else:
                # Insert new template
                template_id = await self.execute_query(
                    "INSERT INTO device_templates (device_type, backup_commands, connection_settings) "
                    "VALUES (?, ?, ?)",
                    (device_type, backup_commands_json, connection_settings_json)
                )
                
                return template_id
        except Exception as e:
            self.logger.error(f"Error adding device template: {e}")
            return None 