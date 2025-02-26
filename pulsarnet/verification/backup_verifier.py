"""Backup verification module for PulsarNet.

This module provides functionality to verify the integrity of device backups
using checksums and content validation.
"""

import os
import re
import hashlib
import logging
import asyncio
from typing import Dict, List, Any, Optional, Tuple, Union
import difflib
from datetime import datetime

from ..database.db_manager import DatabaseManager
from ..utils.logging_config import get_logger


class BackupVerifier:
    """Verifier for backup integrity."""
    
    def __init__(self, db_manager: Optional[DatabaseManager] = None):
        """Initialize the backup verifier.
        
        Args:
            db_manager: Optional database manager. If None, a new one will be created.
        """
        self.db = db_manager
        self.logger = get_logger("verification")
        
    async def initialize(self, db_manager: Optional[DatabaseManager] = None):
        """Initialize the backup verifier.
        
        Args:
            db_manager: Database manager to use
        """
        if db_manager:
            self.db = db_manager
            
        if self.db:
            await self.db.initialize()
            
    async def verify_backup(self, backup_id: int) -> Tuple[bool, str]:
        """Verify a backup by ID.
        
        Args:
            backup_id: Backup ID to verify
            
        Returns:
            Tuple[bool, str]: (Success flag, Verification message)
        """
        try:
            if not self.db:
                return False, "Database not initialized"
                
            # Get backup info
            backup_rows = await self.db.execute_query(
                "SELECT id, device_id, backup_type, file_path, file_size, checksum "
                "FROM backups WHERE id = ?",
                (backup_id,)
            )
            
            if not backup_rows:
                return False, f"Backup with ID {backup_id} not found"
                
            backup = backup_rows[0]
            file_path = backup[3]
            stored_checksum = backup[5]
            
            # Check if the file exists
            if not os.path.exists(file_path):
                await self.db.update_backup_verification(backup_id, "FAILED - File missing")
                return False, f"Backup file not found: {file_path}"
                
            # Calculate new checksum
            checksum = await self._calculate_checksum(file_path)
            
            # Check if checksums match
            if stored_checksum and checksum != stored_checksum:
                await self.db.update_backup_verification(backup_id, "FAILED - Checksum mismatch")
                return False, f"Checksum mismatch for backup {backup_id}"
                
            # If no stored checksum, update it
            if not stored_checksum:
                await self.db.update_backup_verification(backup_id, "VERIFIED", checksum)
            else:
                await self.db.update_backup_verification(backup_id, "VERIFIED")
                
            return True, "Backup verified successfully"
        except Exception as e:
            self.logger.error(f"Error verifying backup {backup_id}: {e}")
            await self.db.update_backup_verification(backup_id, f"FAILED - {str(e)}")
            return False, f"Error verifying backup: {str(e)}"
            
    async def verify_all_backups(self, device_id: Optional[int] = None) -> Dict[int, Tuple[bool, str]]:
        """Verify all backups or backups for a specific device.
        
        Args:
            device_id: Optional device ID to filter by
            
        Returns:
            Dict[int, Tuple[bool, str]]: Dictionary mapping backup IDs to verification results
        """
        results = {}
        
        try:
            if not self.db:
                return {0: (False, "Database not initialized")}
                
            # Get backups to verify
            if device_id:
                backups = await self.db.execute_query(
                    "SELECT id FROM backups WHERE device_id = ?",
                    (device_id,)
                )
            else:
                backups = await self.db.execute_query(
                    "SELECT id FROM backups"
                )
                
            # Verify each backup
            for backup_row in backups:
                backup_id = backup_row[0]
                success, message = await self.verify_backup(backup_id)
                results[backup_id] = (success, message)
                
            return results
        except Exception as e:
            self.logger.error(f"Error verifying all backups: {e}")
            return {0: (False, f"Error verifying backups: {str(e)}")}
            
    async def compare_backups(self, backup_id1: int, backup_id2: int) -> Tuple[bool, str, Optional[List[str]]]:
        """Compare two backups.
        
        Args:
            backup_id1: First backup ID
            backup_id2: Second backup ID
            
        Returns:
            Tuple[bool, str, Optional[List[str]]]: (Success flag, Message, Diff lines if successful)
        """
        try:
            if not self.db:
                return False, "Database not initialized", None
                
            # Get backup info
            backup1_rows = await self.db.execute_query(
                "SELECT id, device_id, file_path FROM backups WHERE id = ?",
                (backup_id1,)
            )
            
            backup2_rows = await self.db.execute_query(
                "SELECT id, device_id, file_path FROM backups WHERE id = ?",
                (backup_id2,)
            )
            
            if not backup1_rows:
                return False, f"Backup with ID {backup_id1} not found", None
                
            if not backup2_rows:
                return False, f"Backup with ID {backup_id2} not found", None
                
            file_path1 = backup1_rows[0][2]
            file_path2 = backup2_rows[0][2]
            
            # Check if the files exist
            if not os.path.exists(file_path1):
                return False, f"Backup file not found: {file_path1}", None
                
            if not os.path.exists(file_path2):
                return False, f"Backup file not found: {file_path2}", None
                
            # Read file contents
            with open(file_path1, 'r', encoding='utf-8', errors='replace') as f1:
                lines1 = f1.readlines()
                
            with open(file_path2, 'r', encoding='utf-8', errors='replace') as f2:
                lines2 = f2.readlines()
                
            # Generate diff
            diff = list(difflib.unified_diff(
                lines1, lines2, 
                fromfile=f"Backup {backup_id1}", 
                tofile=f"Backup {backup_id2}", 
                n=3
            ))
            
            if not diff:
                return True, "Backups are identical", []
                
            return True, f"Found {len(diff)} differences", diff
        except Exception as e:
            self.logger.error(f"Error comparing backups {backup_id1} and {backup_id2}: {e}")
            return False, f"Error comparing backups: {str(e)}", None
            
    async def verify_content(self, backup_id: int, patterns: List[Dict[str, str]]) -> Tuple[bool, str, List[Dict[str, Any]]]:
        """Verify backup content against expected patterns.
        
        Args:
            backup_id: Backup ID to verify
            patterns: List of pattern dictionaries with 'pattern' and 'description' keys
            
        Returns:
            Tuple[bool, str, List[Dict[str, Any]]]: (Success flag, Message, Results list)
        """
        try:
            if not self.db:
                return False, "Database not initialized", []
                
            # Get backup info
            backup_rows = await self.db.execute_query(
                "SELECT id, device_id, file_path FROM backups WHERE id = ?",
                (backup_id,)
            )
            
            if not backup_rows:
                return False, f"Backup with ID {backup_id} not found", []
                
            file_path = backup_rows[0][2]
            
            # Check if the file exists
            if not os.path.exists(file_path):
                return False, f"Backup file not found: {file_path}", []
                
            # Read file contents
            with open(file_path, 'r', encoding='utf-8', errors='replace') as f:
                content = f.read()
                
            # Check each pattern
            results = []
            all_passed = True
            
            for pattern_dict in patterns:
                pattern = pattern_dict['pattern']
                description = pattern_dict['description']
                required = pattern_dict.get('required', True)
                
                try:
                    matches = re.findall(pattern, content, re.MULTILINE)
                    found = len(matches) > 0
                    
                    if required and not found:
                        all_passed = False
                        
                    results.append({
                        'pattern': pattern,
                        'description': description,
                        'required': required,
                        'found': found,
                        'matches': matches if found else None
                    })
                except re.error as e:
                    self.logger.error(f"Invalid regex pattern '{pattern}': {e}")
                    results.append({
                        'pattern': pattern,
                        'description': description,
                        'required': required,
                        'found': False,
                        'error': f"Invalid pattern: {str(e)}"
                    })
                    if required:
                        all_passed = False
                        
            # Update verification status
            if all_passed:
                await self.db.update_backup_verification(backup_id, "CONTENT VERIFIED")
                message = "All required patterns found"
            else:
                await self.db.update_backup_verification(backup_id, "CONTENT CHECK FAILED")
                message = "Some required patterns not found"
                
            return all_passed, message, results
        except Exception as e:
            self.logger.error(f"Error verifying backup content {backup_id}: {e}")
            return False, f"Error verifying backup content: {str(e)}", []
            
    async def _calculate_checksum(self, file_path: str) -> str:
        """Calculate MD5 checksum for a file.
        
        Args:
            file_path: Path to the file
            
        Returns:
            str: MD5 checksum as a hexadecimal string
        """
        hash_md5 = hashlib.md5()
        
        with open(file_path, 'rb') as f:
            for chunk in iter(lambda: f.read(4096), b''):
                hash_md5.update(chunk)
                
        return hash_md5.hexdigest()
        
    async def validate_device_configuration(self, backup_id: int, device_type: str) -> Tuple[bool, str, Dict[str, Any]]:
        """Validate device configuration against expected values for the device type.
        
        Args:
            backup_id: Backup ID to validate
            device_type: Device type
            
        Returns:
            Tuple[bool, str, Dict[str, Any]]: (Success flag, Message, Validation results)
        """
        try:
            if not self.db:
                return False, "Database not initialized", {}
                
            # Get backup info
            backup_rows = await self.db.execute_query(
                "SELECT id, device_id, file_path FROM backups WHERE id = ?",
                (backup_id,)
            )
            
            if not backup_rows:
                return False, f"Backup with ID {backup_id} not found", {}
                
            file_path = backup_rows[0][2]
            
            # Check if the file exists
            if not os.path.exists(file_path):
                return False, f"Backup file not found: {file_path}", {}
                
            # Get validation patterns for this device type
            # Here we'd normally get these from a template or database
            # For now we'll use hardcoded patterns for demonstration
            validation_patterns = self._get_validation_patterns(device_type)
            
            # Perform content validation
            success, message, results = await self.verify_content(backup_id, validation_patterns)
            
            # Format results for display
            validation_results = {
                'success': success,
                'message': message,
                'patterns_checked': len(validation_patterns),
                'patterns_matched': sum(1 for r in results if r['found']),
                'details': results
            }
            
            return success, message, validation_results
        except Exception as e:
            self.logger.error(f"Error validating device configuration {backup_id}: {e}")
            return False, f"Error validating configuration: {str(e)}", {}
            
    def _get_validation_patterns(self, device_type: str) -> List[Dict[str, str]]:
        """Get validation patterns for a device type.
        
        Args:
            device_type: Device type
            
        Returns:
            List[Dict[str, str]]: List of pattern dictionaries
        """
        # Default patterns for any device
        default_patterns = [
            {
                'pattern': r'hostname\s+(\S+)',
                'description': 'Hostname defined',
                'required': True
            },
            {
                'pattern': r'ip\s+address\s+(\S+)',
                'description': 'IP address defined',
                'required': False
            }
        ]
        
        # Device-specific patterns
        if device_type.startswith('cisco_ios'):
            return default_patterns + [
                {
                    'pattern': r'service\s+password-encryption',
                    'description': 'Password encryption enabled',
                    'required': True
                },
                {
                    'pattern': r'no\s+service\s+password-recovery',
                    'description': 'Password recovery disabled',
                    'required': False
                },
                {
                    'pattern': r'enable\s+secret\s+(\S+)',
                    'description': 'Enable secret configured',
                    'required': True
                },
                {
                    'pattern': r'aaa\s+new-model',
                    'description': 'AAA enabled',
                    'required': False
                },
                {
                    'pattern': r'logging\s+(\S+)',
                    'description': 'Logging configured',
                    'required': True
                }
            ]
        elif device_type.startswith('juniper'):
            return default_patterns + [
                {
                    'pattern': r'system\s+{\s+root-authentication\s+{\s+encrypted-password\s+["\S]+;',
                    'description': 'Root authentication configured',
                    'required': True
                },
                {
                    'pattern': r'security\s+{\s+',
                    'description': 'Security section present',
                    'required': True
                }
            ]
        elif device_type.startswith('arista'):
            return default_patterns + [
                {
                    'pattern': r'username\s+(\S+)\s+',
                    'description': 'User accounts defined',
                    'required': True
                },
                {
                    'pattern': r'management\s+',
                    'description': 'Management section present',
                    'required': False
                }
            ]
        else:
            # Return default patterns for unknown device types
            return default_patterns 