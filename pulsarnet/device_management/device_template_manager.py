"""DeviceTemplateManager for handling device type-specific templates.

This module provides functionality for managing and applying templates for
different network device types, including backup commands, connection settings,
and custom configurations.
"""

import os
import json
import logging
from typing import Dict, List, Any, Optional
from enum import Enum
import asyncio

from ..database.db_manager import DatabaseManager
from .device import DeviceType


class TemplateCategory(Enum):
    """Categories of device templates."""
    BACKUP = "backup"
    CONFIGURATION = "configuration"
    CONNECTION = "connection"
    MONITORING = "monitoring"


class DeviceTemplateManager:
    """Manager for device type templates."""
    
    def __init__(self, db_manager: Optional[DatabaseManager] = None):
        """Initialize the device template manager.
        
        Args:
            db_manager: Optional database manager. If None, a new one will be created.
        """
        self.db = db_manager or DatabaseManager()
        self.logger = logging.getLogger(__name__)
        self._templates_cache = {}
        self._cache_valid = False
        
        # Default templates path
        self.templates_dir = os.path.join(
            os.path.dirname(os.path.abspath(__file__)), 
            "../templates"
        )
        
    async def initialize(self):
        """Initialize the template manager and database connection."""
        await self.db.initialize()
        await self._load_default_templates()
        self._cache_valid = False
    
    async def _load_default_templates(self):
        """Load default templates from the filesystem if database is empty."""
        try:
            templates = await self.db.get_device_templates()
            if templates:
                return  # Templates already exist in database
                
            # Create templates directory if it doesn't exist
            os.makedirs(self.templates_dir, exist_ok=True)
            
            # Look for template files
            template_files = {}
            for device_type in DeviceType:
                filename = f"{device_type.value}.json"
                file_path = os.path.join(self.templates_dir, filename)
                
                if os.path.exists(file_path):
                    try:
                        with open(file_path, 'r') as f:
                            template_data = json.load(f)
                            await self.db.add_device_template({
                                'device_type': device_type.value,
                                'backup_commands': template_data.get('backup_commands', {}),
                                'connection_settings': template_data.get('connection_settings', {})
                            })
                    except Exception as e:
                        self.logger.error(f"Error loading template for {device_type.value}: {str(e)}")
            
            # Create default templates for common device types
            await self._create_default_templates()
            
        except Exception as e:
            self.logger.error(f"Error loading default templates: {str(e)}")
    
    async def _create_default_templates(self):
        """Create default templates for common device types."""
        default_templates = {
            # Cisco IOS
            'cisco_ios': {
                'backup_commands': {
                    'pre_commands': [],
                    'config_commands': ['show running-config'],
                    'post_commands': [],
                    'verification_commands': ['show version']
                },
                'connection_settings': {
                    'ssh_args': {
                        'device_type': 'cisco_ios',
                        'port': 22,
                        'global_delay_factor': 1,
                        'timeout': 30,
                        'keepalive': 30,
                        'fast_cli': True
                    },
                    'telnet_args': {
                        'device_type': 'cisco_ios_telnet',
                        'port': 23,
                        'global_delay_factor': 1,
                        'timeout': 30
                    }
                }
            },
            # Cisco NXOS
            'cisco_nxos': {
                'backup_commands': {
                    'pre_commands': [],
                    'config_commands': ['show running-config'],
                    'post_commands': [],
                    'verification_commands': ['show version']
                },
                'connection_settings': {
                    'ssh_args': {
                        'device_type': 'cisco_nxos',
                        'port': 22,
                        'global_delay_factor': 1,
                        'timeout': 30,
                        'keepalive': 30,
                        'fast_cli': True
                    }
                }
            },
            # Juniper
            'juniper_junos': {
                'backup_commands': {
                    'pre_commands': [],
                    'config_commands': ['show configuration | display set'],
                    'post_commands': [],
                    'verification_commands': ['show version']
                },
                'connection_settings': {
                    'ssh_args': {
                        'device_type': 'juniper_junos',
                        'port': 22,
                        'global_delay_factor': 1,
                        'timeout': 30
                    }
                }
            },
            # Arista EOS
            'arista_eos': {
                'backup_commands': {
                    'pre_commands': [],
                    'config_commands': ['show running-config'],
                    'post_commands': [],
                    'verification_commands': ['show version']
                },
                'connection_settings': {
                    'ssh_args': {
                        'device_type': 'arista_eos',
                        'port': 22,
                        'global_delay_factor': 1,
                        'timeout': 30
                    }
                }
            }
        }
        
        for device_type, template in default_templates.items():
            try:
                await self.db.add_device_template({
                    'device_type': device_type,
                    'backup_commands': template['backup_commands'],
                    'connection_settings': template['connection_settings']
                })
            except Exception as e:
                self.logger.error(f"Error creating default template for {device_type}: {str(e)}")
    
    async def get_templates(self) -> List[Dict[str, Any]]:
        """Get all device templates.
        
        Returns:
            List[Dict[str, Any]]: List of template dictionaries
        """
        if not self._cache_valid:
            templates = await self.db.get_device_templates()
            self._templates_cache = {t['device_type']: t for t in templates}
            self._cache_valid = True
            
        return list(self._templates_cache.values())
    
    async def get_template(self, device_type: str) -> Optional[Dict[str, Any]]:
        """Get template for a specific device type.
        
        Args:
            device_type: Device type string
            
        Returns:
            Optional[Dict[str, Any]]: Template dictionary or None if not found
        """
        if not self._cache_valid:
            await self.get_templates()
            
        # Try to get from cache
        template = self._templates_cache.get(device_type)
        if template:
            return template
            
        # If not in cache, try to get from database
        templates = await self.db.execute_query(
            "SELECT id, device_type, backup_commands, connection_settings, created_at, updated_at "
            "FROM device_templates WHERE device_type = ?",
            (device_type,)
        )
        
        if not templates:
            # Try to find a similar device type
            for cached_type in self._templates_cache:
                if cached_type.startswith(device_type.split('_')[0]):
                    self.logger.info(f"Using template for {cached_type} as fallback for {device_type}")
                    return self._templates_cache[cached_type]
            return None
            
        template = templates[0]
        
        import json
        result = {
            'id': template[0],
            'device_type': template[1],
            'backup_commands': json.loads(template[2]),
            'connection_settings': json.loads(template[3]),
            'created_at': template[4],
            'updated_at': template[5]
        }
        
        # Add to cache
        self._templates_cache[device_type] = result
        return result
    
    async def add_template(self, template_data: Dict[str, Any]) -> int:
        """Add a new device template.
        
        Args:
            template_data: Dictionary containing template information
            
        Returns:
            int: ID of the newly created template
        """
        template_id = await self.db.add_device_template(template_data)
        self._cache_valid = False
        return template_id
    
    async def update_template(self, device_type: str, template_data: Dict[str, Any]) -> bool:
        """Update an existing device template.
        
        Args:
            device_type: Device type to update
            template_data: Dictionary containing updated template information
            
        Returns:
            bool: True if update successful, False otherwise
        """
        try:
            # Get the template ID
            template = await self.get_template(device_type)
            if not template:
                return False
                
            template_id = template['id']
            
            # Update template in database
            template_data['device_type'] = device_type  # Ensure device type is set
            await self.db.add_device_template(template_data)  # Using upsert
            
            self._cache_valid = False
            return True
        except Exception as e:
            self.logger.error(f"Error updating template for {device_type}: {str(e)}")
            return False
    
    async def delete_template(self, device_type: str) -> bool:
        """Delete a device template.
        
        Args:
            device_type: Device type to delete
            
        Returns:
            bool: True if deletion successful, False otherwise
        """
        try:
            # Get the template ID
            template = await self.get_template(device_type)
            if not template:
                return False
                
            template_id = template['id']
            
            # Delete template from database
            await self.db.execute_query(
                "DELETE FROM device_templates WHERE id = ?",
                (template_id,)
            )
            
            # Remove from cache
            if device_type in self._templates_cache:
                del self._templates_cache[device_type]
                
            return True
        except Exception as e:
            self.logger.error(f"Error deleting template for {device_type}: {str(e)}")
            return False
    
    async def get_backup_commands(self, device_type: str) -> Dict[str, List[str]]:
        """Get backup commands for a specific device type.
        
        Args:
            device_type: Device type string
            
        Returns:
            Dict[str, List[str]]: Dictionary of backup command lists
        """
        template = await self.get_template(device_type)
        if not template:
            return {
                'pre_commands': [],
                'config_commands': ['show running-config'],
                'post_commands': [],
                'verification_commands': []
            }
            
        return template.get('backup_commands', {})
    
    async def get_connection_settings(self, device_type: str, connection_method: str = 'ssh') -> Dict[str, Any]:
        """Get connection settings for a specific device type and method.
        
        Args:
            device_type: Device type string
            connection_method: Connection method ('ssh', 'telnet', etc.)
            
        Returns:
            Dict[str, Any]: Connection settings dictionary
        """
        template = await self.get_template(device_type)
        if not template or 'connection_settings' not in template:
            # Default settings
            return {
                'device_type': device_type,
                'port': 22 if connection_method == 'ssh' else 23,
                'timeout': 30
            }
            
        connection_settings = template['connection_settings']
        
        # Get method-specific settings
        method_key = f"{connection_method}_args"
        if method_key in connection_settings:
            return connection_settings[method_key]
            
        # Fall back to generic settings
        return connection_settings.get('default_args', {
            'device_type': device_type,
            'port': 22 if connection_method == 'ssh' else 23,
            'timeout': 30
        })
    
    async def export_templates(self, export_dir: Optional[str] = None) -> bool:
        """Export all templates to JSON files.
        
        Args:
            export_dir: Directory to export templates to. If None, uses default templates directory.
            
        Returns:
            bool: True if export successful, False otherwise
        """
        try:
            if export_dir is None:
                export_dir = self.templates_dir
                
            os.makedirs(export_dir, exist_ok=True)
            
            templates = await self.get_templates()
            for template in templates:
                filename = f"{template['device_type']}.json"
                file_path = os.path.join(export_dir, filename)
                
                with open(file_path, 'w') as f:
                    json.dump({
                        'backup_commands': template.get('backup_commands', {}),
                        'connection_settings': template.get('connection_settings', {})
                    }, f, indent=4)
            
            return True
        except Exception as e:
            self.logger.error(f"Error exporting templates: {str(e)}")
            return False
    
    async def import_templates(self, import_dir: Optional[str] = None) -> int:
        """Import templates from JSON files.
        
        Args:
            import_dir: Directory to import templates from. If None, uses default templates directory.
            
        Returns:
            int: Number of templates imported
        """
        try:
            if import_dir is None:
                import_dir = self.templates_dir
                
            if not os.path.exists(import_dir):
                self.logger.error(f"Import directory does not exist: {import_dir}")
                return 0
                
            count = 0
            for filename in os.listdir(import_dir):
                if not filename.endswith('.json'):
                    continue
                    
                device_type = os.path.splitext(filename)[0]
                file_path = os.path.join(import_dir, filename)
                
                try:
                    with open(file_path, 'r') as f:
                        template_data = json.load(f)
                        template_data['device_type'] = device_type
                        await self.add_template(template_data)
                        count += 1
                except Exception as e:
                    self.logger.error(f"Error importing template from {filename}: {str(e)}")
            
            return count
        except Exception as e:
            self.logger.error(f"Error importing templates: {str(e)}")
            return 0
    
    async def render_commands(self, device_type: str, command_set: str, variables: Dict[str, str] = None) -> List[str]:
        """Render commands for a specific device type with variable substitution.
        
        Args:
            device_type: Device type string
            command_set: Command set name ('pre_commands', 'config_commands', etc.)
            variables: Dictionary of variables to substitute
            
        Returns:
            List[str]: Rendered command list
        """
        if variables is None:
            variables = {}
            
        backup_commands = await self.get_backup_commands(device_type)
        commands = backup_commands.get(command_set, [])
        
        # Perform variable substitution
        rendered_commands = []
        for cmd in commands:
            for var_name, var_value in variables.items():
                cmd = cmd.replace(f"{{{var_name}}}", str(var_value))
            rendered_commands.append(cmd)
            
        return rendered_commands 