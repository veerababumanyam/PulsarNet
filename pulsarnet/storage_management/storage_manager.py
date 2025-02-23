"""Storage Manager Module for PulsarNet.

This module provides the StorageManager class that orchestrates storage operations,
manages multiple storage locations, and enforces retention policies.
"""

from pathlib import Path
from typing import Dict, List, Optional
from datetime import datetime

from .storage_location import StorageLocation, StorageType
from .retention_policy import RetentionPolicy, RetentionRule, RetentionType

class StorageManager:
    """Class for managing backup storage operations and policies."""

    def __init__(self):
        """Initialize the storage manager."""
        self.storage_locations: Dict[str, StorageLocation] = {}
        self.retention_policies: Dict[str, RetentionPolicy] = {}
        self.default_policy: Optional[str] = None

    def add_storage_location(self, location: StorageLocation) -> None:
        """Add a new storage location.

        Args:
            location: StorageLocation instance to add

        Raises:
            ValueError: If location with same name already exists
        """
        if location.name in self.storage_locations:
            raise ValueError(f"Storage location '{location.name}' already exists")
        self.storage_locations[location.name] = location

    def remove_storage_location(self, name: str) -> None:
        """Remove a storage location.

        Args:
            name: Name of the storage location to remove

        Raises:
            KeyError: If location does not exist
        """
        if name not in self.storage_locations:
            raise KeyError(f"Storage location '{name}' not found")
        del self.storage_locations[name]

    def add_retention_policy(self, policy: RetentionPolicy, set_as_default: bool = False) -> None:
        """Add a new retention policy.

        Args:
            policy: RetentionPolicy instance to add
            set_as_default: Whether to set this as the default policy

        Raises:
            ValueError: If policy with same name already exists
        """
        if policy.name in self.retention_policies:
            raise ValueError(f"Retention policy '{policy.name}' already exists")
        self.retention_policies[policy.name] = policy

        if set_as_default or not self.default_policy:
            self.default_policy = policy.name

    async def check_storage_space(self, location_name: str) -> Dict[str, float]:
        """Check available and used space in a storage location.

        Args:
            location_name: Name of the storage location

        Returns:
            Dict containing space usage information

        Raises:
            KeyError: If location does not exist
        """
        location = self.storage_locations.get(location_name)
        if not location:
            raise KeyError(f"Storage location '{location_name}' not found")

        space_info = await location.check_space()
        if location.max_size_gb:
            space_info["usage_percent"] = (space_info["used_gb"] / location.max_size_gb) * 100
        return space_info

    async def apply_retention_policy(
        self,
        location_name: str,
        policy_name: Optional[str] = None
    ) -> List[Path]:
        """Apply retention policy to a storage location.

        Args:
            location_name: Name of the storage location
            policy_name: Name of the retention policy to apply (uses default if None)

        Returns:
            List of files that were deleted

        Raises:
            KeyError: If location or policy does not exist
        """
        location = self.storage_locations.get(location_name)
        if not location:
            raise KeyError(f"Storage location '{location_name}' not found")

        policy_name = policy_name or self.default_policy
        if not policy_name:
            raise ValueError("No retention policy specified and no default policy set")

        policy = self.retention_policies.get(policy_name)
        if not policy:
            raise KeyError(f"Retention policy '{policy_name}' not found")

        # Get list of backup files in the location
        backup_files = list(location.path.glob("*.cfg"))  # Assuming .cfg extension for backups
        files_to_delete = await policy.get_files_to_delete(backup_files)

        # Delete the files
        for file_path in files_to_delete:
            try:
                file_path.unlink()
            except Exception as e:
                # Log the error but continue with other files
                print(f"Error deleting {file_path}: {e}")

        return files_to_delete

    def get_storage_info(self) -> List[Dict]:
        """Get information about all storage locations.

        Returns:
            List of dictionaries containing storage location information
        """
        return [location.to_dict() for location in self.storage_locations.values()]

    def get_policy_info(self) -> List[Dict]:
        """Get information about all retention policies.

        Returns:
            List of dictionaries containing retention policy information
        """
        return [{
            **policy.to_dict(),
            "is_default": policy.name == self.default_policy
        } for policy in self.retention_policies.values()]