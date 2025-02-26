"""Consolidation Plan Module for PulsarNet.

This module provides classes for representing device consolidation plans,
including grouping similar devices and documenting consolidation strategies.
"""

import json
from datetime import datetime
from enum import Enum
from typing import Dict, List, Optional, Set, Any
import uuid
import logging


class ConsolidationStrategy(Enum):
    """Strategy types for device consolidation."""
    REPLACE_WITH_NEW = "replace_with_new"
    MERGE_INTO_EXISTING = "merge_into_existing"
    STANDARDIZE_CONFIG = "standardize_config"
    VIRTUALIZE = "virtualize"
    DECOMMISSION = "decommission"
    REDISTRIBUTE_LOAD = "redistribute_load"
    CUSTOM = "custom"


class ConsolidationStatus(Enum):
    """Status of a consolidation plan or group."""
    DRAFT = "draft"
    PROPOSED = "proposed"
    APPROVED = "approved"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


class ConsolidationMetric(Enum):
    """Metrics for evaluating consolidation benefits."""
    COST_SAVINGS = "cost_savings"
    POWER_REDUCTION = "power_reduction"
    SPACE_SAVINGS = "space_savings"
    MANAGEMENT_SIMPLIFICATION = "management_simplification"
    PERFORMANCE_IMPROVEMENT = "performance_improvement"
    RELIABILITY_IMPROVEMENT = "reliability_improvement"


class ConsolidationGroup:
    """Represents a group of similar devices that could be consolidated."""

    def __init__(self, name: str, description: Optional[str] = None):
        """Initialize a consolidation group.

        Args:
            name: Name of the consolidation group
            description: Optional description of the group
        """
        self.id = str(uuid.uuid4())
        self.name = name
        self.description = description
        self.device_ids: List[int] = []
        self.primary_device_id: Optional[int] = None
        self.similarity_score: float = 0.0
        self.similarity_factors: Dict[str, float] = {}
        self.proposed_strategy: Optional[ConsolidationStrategy] = None
        self.estimated_benefits: Dict[ConsolidationMetric, float] = {}
        self.config_differences: List[Dict[str, Any]] = []
        self.notes: str = ""
        self.created_at = datetime.now().isoformat()
        self.updated_at = datetime.now().isoformat()

    def add_device(self, device_id: int) -> None:
        """Add a device to the group.

        Args:
            device_id: ID of the device to add
        """
        if device_id not in self.device_ids:
            self.device_ids.append(device_id)
            self.updated_at = datetime.now().isoformat()

    def remove_device(self, device_id: int) -> None:
        """Remove a device from the group.

        Args:
            device_id: ID of the device to remove
        """
        if device_id in self.device_ids:
            self.device_ids.remove(device_id)
            if self.primary_device_id == device_id:
                self.primary_device_id = self.device_ids[0] if self.device_ids else None
            self.updated_at = datetime.now().isoformat()

    def set_primary_device(self, device_id: int) -> bool:
        """Set a device as the primary device for the group.

        Args:
            device_id: ID of the device to set as primary

        Returns:
            bool: True if successful, False if the device is not in the group
        """
        if device_id in self.device_ids:
            self.primary_device_id = device_id
            self.updated_at = datetime.now().isoformat()
            return True
        return False

    def add_similarity_factor(self, factor: str, score: float) -> None:
        """Add a similarity factor and score.

        Args:
            factor: Name of the similarity factor
            score: Similarity score (0.0-1.0)
        """
        self.similarity_factors[factor] = score
        # Recalculate overall similarity score
        if self.similarity_factors:
            self.similarity_score = sum(self.similarity_factors.values()) / len(self.similarity_factors)
        self.updated_at = datetime.now().isoformat()

    def add_config_difference(self, difference: Dict[str, Any]) -> None:
        """Add a configuration difference to the group.

        Args:
            difference: Dictionary describing the configuration difference
        """
        self.config_differences.append(difference)
        self.updated_at = datetime.now().isoformat()

    def to_dict(self) -> Dict[str, Any]:
        """Convert the group to a dictionary.

        Returns:
            Dict[str, Any]: Dictionary representation of the group
        """
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "device_ids": self.device_ids,
            "primary_device_id": self.primary_device_id,
            "similarity_score": self.similarity_score,
            "similarity_factors": self.similarity_factors,
            "proposed_strategy": self.proposed_strategy.value if self.proposed_strategy else None,
            "estimated_benefits": {k.value: v for k, v in self.estimated_benefits.items()},
            "config_differences": self.config_differences,
            "notes": self.notes,
            "created_at": self.created_at,
            "updated_at": self.updated_at
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ConsolidationGroup':
        """Create a group from a dictionary.

        Args:
            data: Dictionary representation of the group

        Returns:
            ConsolidationGroup: Created group instance
        """
        group = cls(data["name"], data.get("description"))
        group.id = data["id"]
        group.device_ids = data["device_ids"]
        group.primary_device_id = data.get("primary_device_id")
        group.similarity_score = data.get("similarity_score", 0.0)
        group.similarity_factors = data.get("similarity_factors", {})
        
        strategy = data.get("proposed_strategy")
        if strategy:
            group.proposed_strategy = ConsolidationStrategy(strategy)
            
        benefits = data.get("estimated_benefits", {})
        group.estimated_benefits = {ConsolidationMetric(k): v for k, v in benefits.items()}
        
        group.config_differences = data.get("config_differences", [])
        group.notes = data.get("notes", "")
        group.created_at = data.get("created_at", group.created_at)
        group.updated_at = data.get("updated_at", group.updated_at)
        return group


class ConsolidationPlan:
    """Represents a plan for consolidating multiple devices."""

    def __init__(self, name: str, description: Optional[str] = None,
                 created_by: Optional[str] = None):
        """Initialize a consolidation plan.

        Args:
            name: Name of the consolidation plan
            description: Optional description of the plan
            created_by: User who created the plan
        """
        self.id = str(uuid.uuid4())
        self.name = name
        self.description = description
        self.created_by = created_by or "system"
        self.status = ConsolidationStatus.DRAFT
        self.groups: Dict[str, ConsolidationGroup] = {}
        self.affected_device_ids: Set[int] = set()
        self.target_completion_date: Optional[str] = None
        self.notes: str = ""
        self.created_at = datetime.now().isoformat()
        self.updated_at = datetime.now().isoformat()
        self.approved_by: Optional[str] = None
        self.approved_at: Optional[str] = None

    def add_group(self, group: ConsolidationGroup) -> None:
        """Add a consolidation group to the plan.

        Args:
            group: Consolidation group to add
        """
        self.groups[group.id] = group
        self.affected_device_ids.update(group.device_ids)
        self.updated_at = datetime.now().isoformat()

    def remove_group(self, group_id: str) -> bool:
        """Remove a consolidation group from the plan.

        Args:
            group_id: ID of the group to remove

        Returns:
            bool: True if successful, False if group not found
        """
        if group_id in self.groups:
            removed_devices = set(self.groups[group_id].device_ids)
            del self.groups[group_id]
            
            # Recalculate affected devices
            self.affected_device_ids = set()
            for group in self.groups.values():
                self.affected_device_ids.update(group.device_ids)
                
            self.updated_at = datetime.now().isoformat()
            return True
        return False

    def get_group(self, group_id: str) -> Optional[ConsolidationGroup]:
        """Get a consolidation group by ID.

        Args:
            group_id: ID of the group to get

        Returns:
            Optional[ConsolidationGroup]: Group if found, None otherwise
        """
        return self.groups.get(group_id)

    def get_groups_for_device(self, device_id: int) -> List[ConsolidationGroup]:
        """Get all groups containing a specific device.

        Args:
            device_id: ID of the device

        Returns:
            List[ConsolidationGroup]: List of groups containing the device
        """
        return [group for group in self.groups.values() if device_id in group.device_ids]

    def change_status(self, status: ConsolidationStatus, user: Optional[str] = None) -> None:
        """Change the status of the consolidation plan.

        Args:
            status: New status for the plan
            user: User making the change
        """
        self.status = status
        self.updated_at = datetime.now().isoformat()
        
        if status == ConsolidationStatus.APPROVED and user:
            self.approved_by = user
            self.approved_at = datetime.now().isoformat()

    def to_dict(self) -> Dict[str, Any]:
        """Convert the plan to a dictionary.

        Returns:
            Dict[str, Any]: Dictionary representation of the plan
        """
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "created_by": self.created_by,
            "status": self.status.value,
            "groups": {group_id: group.to_dict() for group_id, group in self.groups.items()},
            "affected_device_ids": list(self.affected_device_ids),
            "target_completion_date": self.target_completion_date,
            "notes": self.notes,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "approved_by": self.approved_by,
            "approved_at": self.approved_at
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ConsolidationPlan':
        """Create a plan from a dictionary.

        Args:
            data: Dictionary representation of the plan

        Returns:
            ConsolidationPlan: Created plan instance
        """
        plan = cls(data["name"], data.get("description"), data.get("created_by"))
        plan.id = data["id"]
        plan.status = ConsolidationStatus(data["status"])
        
        # Recreate groups
        for group_data in data.get("groups", {}).values():
            group = ConsolidationGroup.from_dict(group_data)
            plan.groups[group.id] = group
            
        plan.affected_device_ids = set(data.get("affected_device_ids", []))
        plan.target_completion_date = data.get("target_completion_date")
        plan.notes = data.get("notes", "")
        plan.created_at = data.get("created_at", plan.created_at)
        plan.updated_at = data.get("updated_at", plan.updated_at)
        plan.approved_by = data.get("approved_by")
        plan.approved_at = data.get("approved_at")
        return plan

    def export_to_json(self, file_path: str) -> bool:
        """Export the plan to a JSON file.

        Args:
            file_path: Path to the output file

        Returns:
            bool: True if successful, False otherwise
        """
        try:
            with open(file_path, 'w') as f:
                json.dump(self.to_dict(), f, indent=2)
            return True
        except Exception as e:
            logging.error(f"Error exporting consolidation plan: {str(e)}")
            return False

    @classmethod
    def import_from_json(cls, file_path: str) -> Optional['ConsolidationPlan']:
        """Import a plan from a JSON file.

        Args:
            file_path: Path to the input file

        Returns:
            Optional[ConsolidationPlan]: Imported plan if successful, None otherwise
        """
        try:
            with open(file_path, 'r') as f:
                data = json.load(f)
            return cls.from_dict(data)
        except Exception as e:
            logging.error(f"Error importing consolidation plan: {str(e)}")
            return None 