"""Storage Location Module for PulsarNet.

This module defines the StorageLocation class that handles storage location
configurations and operations for backup files.
"""

from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Dict, Optional

class StorageType(Enum):
    """Enumeration of supported storage types."""
    LOCAL = "local"
    FTP = "ftp"
    SFTP = "sftp"
    TFTP = "tftp"

@dataclass
class StorageCredentials:
    """Storage credentials for remote locations."""
    username: Optional[str] = None
    password: Optional[str] = None
    key_file: Optional[Path] = None

class StorageLocation:
    """Class for managing storage locations and their configurations."""

    def __init__(
        self,
        name: str,
        storage_type: StorageType,
        path: Path,
        credentials: Optional[StorageCredentials] = None,
        max_size_gb: Optional[float] = None
    ):
        """Initialize a storage location.

        Args:
            name: Unique identifier for the storage location
            storage_type: Type of storage (LOCAL, FTP, etc.)
            path: Base path for the storage location
            credentials: Optional credentials for remote storage
            max_size_gb: Optional maximum storage size in GB
        """
        self.name = name
        self.storage_type = storage_type
        self.path = path
        self.credentials = credentials
        self.max_size_gb = max_size_gb
        self._validate_config()

    def _validate_config(self) -> None:
        """Validate the storage location configuration.

        Raises:
            ValueError: If the configuration is invalid
        """
        if self.storage_type != StorageType.LOCAL and not self.credentials:
            raise ValueError(f"Credentials required for {self.storage_type} storage")

        if self.max_size_gb is not None and self.max_size_gb <= 0:
            raise ValueError("Maximum storage size must be positive")

    async def check_space(self) -> Dict[str, float]:
        """Check available and used space in the storage location.

        Returns:
            Dict containing used_gb and available_gb
        """
        # Implementation will vary based on storage type
        if self.storage_type == StorageType.LOCAL:
            return await self._check_local_space()
        else:
            return await self._check_remote_space()

    async def _check_local_space(self) -> Dict[str, float]:
        """Check space for local storage.

        Returns:
            Dict containing used_gb and available_gb
        """
        if not self.path.exists():
            raise ValueError(f"Storage path does not exist: {self.path}")

        total, used, free = shutil.disk_usage(str(self.path))
        return {
            "used_gb": used / (1024 ** 3),
            "available_gb": free / (1024 ** 3)
        }

    async def _check_remote_space(self) -> Dict[str, float]:
        """Check space for remote storage.

        Returns:
            Dict containing used_gb and available_gb
        """
        # To be implemented based on specific protocol requirements
        raise NotImplementedError(f"Space check not implemented for {self.storage_type}")

    def to_dict(self) -> Dict:
        """Convert storage location to dictionary representation.

        Returns:
            Dictionary containing storage location configuration
        """
        return {
            "name": self.name,
            "storage_type": self.storage_type.value,
            "path": str(self.path),
            "max_size_gb": self.max_size_gb,
            "credentials": {
                "username": self.credentials.username,
                "has_password": bool(self.credentials.password),
                "key_file": str(self.credentials.key_file) if self.credentials and self.credentials.key_file else None
            } if self.credentials else None
        }