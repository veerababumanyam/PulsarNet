"""Device Consolidation Manager Module for PulsarNet.

This module provides the main manager for device consolidation operations,
helping to identify and plan consolidation opportunities.
"""

import os
import json
import logging
import asyncio
from datetime import datetime
from typing import Dict, List, Optional, Tuple, Any, Set, Union

from .consolidation_plan import ConsolidationPlan, ConsolidationGroup
from .consolidation_plan import ConsolidationStatus, ConsolidationStrategy, ConsolidationMetric
from .similarity_analyzer import SimilarityAnalyzer


class DeviceConsolidationManager:
    """Manager for device consolidation operations."""

    def __init__(self, db_manager=None):
        """Initialize the device consolidation manager.

        Args:
            db_manager: Database manager for accessing device data
        """
        self.db_manager = db_manager
        self.similarity_analyzer = SimilarityAnalyzer(db_manager)
        self.plans: Dict[str, ConsolidationPlan] = {}
        self.config_dir = os.path.expanduser("~/.pulsarnet/consolidation")
        self.logger = logging.getLogger("pulsarnet.consolidation.manager")
        self.loaded = False

    async def initialize(self, db_manager=None):
        """Initialize the consolidation manager.

        Args:
            db_manager: Database manager to use (if not provided at init)
        """
        if db_manager:
            self.db_manager = db_manager
            
        await self.similarity_analyzer.initialize(self.db_manager)
        
        # Create config directory if it doesn't exist
        os.makedirs(self.config_dir, exist_ok=True)
        
        # Load existing plans if available
        if not self.loaded:
            await self.load_plans()
            self.loaded = True
        
        self.logger.info("Device consolidation manager initialized")

    async def load_plans(self) -> None:
        """Load saved consolidation plans from disk."""
        plans_file = os.path.join(self.config_dir, "consolidation_plans.json")
        if not os.path.exists(plans_file):
            self.logger.info("No existing consolidation plans found")
            return
            
        try:
            with open(plans_file, 'r') as f:
                data = json.load(f)
                
            for plan_data in data.values():
                try:
                    plan = ConsolidationPlan.from_dict(plan_data)
                    self.plans[plan.id] = plan
                    self.logger.debug(f"Loaded consolidation plan: {plan.name}")
                except Exception as e:
                    self.logger.error(f"Error loading plan: {str(e)}")
                    
            self.logger.info(f"Loaded {len(self.plans)} consolidation plans")
        except Exception as e:
            self.logger.error(f"Failed to load consolidation plans: {str(e)}")

    async def save_plans(self) -> bool:
        """Save all consolidation plans to disk.

        Returns:
            bool: True if successful, False otherwise
        """
        plans_file = os.path.join(self.config_dir, "consolidation_plans.json")
        try:
            plans_dict = {plan_id: plan.to_dict() for plan_id, plan in self.plans.items()}
            with open(plans_file, 'w') as f:
                json.dump(plans_dict, f, indent=2)
            self.logger.info(f"Saved {len(self.plans)} consolidation plans")
            return True
        except Exception as e:
            self.logger.error(f"Failed to save consolidation plans: {str(e)}")
            return False

    async def identify_consolidation_opportunities(self, 
                                                  threshold: float = 0.7,
                                                  device_type_filter: Optional[str] = None,
                                                  location_filter: Optional[str] = None) -> List[List[int]]:
        """Identify groups of devices that could be consolidated.

        Args:
            threshold: Minimum similarity score threshold
            device_type_filter: Optional filter for device type
            location_filter: Optional filter for location

        Returns:
            List[List[int]]: List of device ID groups that could be consolidated
        """
        # Get all devices matching filters
        all_devices = await self._get_filtered_devices(device_type_filter, location_filter)
        
        if not all_devices:
            self.logger.warning("No devices found matching the specified filters")
            return []
        
        # Use the similarity analyzer to identify groups
        device_ids = [device["id"] for device in all_devices]
        consolidation_groups = await self.similarity_analyzer.identify_consolidation_groups(threshold)
        
        # If filters are applied, remove devices that don't match the filter
        if device_type_filter or location_filter:
            filtered_groups = []
            for group in consolidation_groups:
                filtered_group = [d for d in group if d in device_ids]
                if len(filtered_group) > 1:  # Only include groups with at least 2 devices
                    filtered_groups.append(filtered_group)
            return filtered_groups
            
        return consolidation_groups

    async def create_consolidation_plan(self, name: str, 
                                       device_groups: List[List[int]],
                                       description: Optional[str] = None,
                                       user: Optional[str] = None) -> ConsolidationPlan:
        """Create a consolidation plan from identified device groups.

        Args:
            name: Name of the consolidation plan
            device_groups: List of device ID groups
            description: Optional description of the plan
            user: User creating the plan

        Returns:
            ConsolidationPlan: Created consolidation plan
        """
        plan = ConsolidationPlan(name, description, user)
        
        for i, group_devices in enumerate(device_groups):
            if len(group_devices) < 2:
                continue  # Skip groups with fewer than 2 devices
                
            group_name = f"{name} Group {i+1}"
            group = ConsolidationGroup(group_name)
            
            # Add devices to the group
            for device_id in group_devices:
                group.add_device(device_id)
                
            # Try to determine similarity factors
            if len(group_devices) >= 2:
                # Analyze the first pair to get similarity details
                scores = await self.similarity_analyzer.analyze_device_pair(group_devices[0], group_devices[1])
                overall_score = await self.similarity_analyzer.calculate_overall_similarity(scores)
                
                # Add similarity factors to the group
                group.similarity_score = overall_score
                for factor, score in scores.items():
                    group.add_similarity_factor(factor.value, score.score)
                
                # Get recommendations for this group
                recommendations = await self.similarity_analyzer.generate_consolidation_recommendations(group_devices)
                
                # Set proposed strategy based on recommendations
                strategy = recommendations.get("strategy")
                if strategy:
                    group.proposed_strategy = ConsolidationStrategy(strategy)
                    
                # Add recommended primary device if available
                if "recommended_primary" in recommendations:
                    group.set_primary_device(recommendations["recommended_primary"])
                    
                # Add estimated benefits
                benefits = recommendations.get("estimated_benefits", {})
                for metric_name, value in benefits.items():
                    try:
                        metric = ConsolidationMetric(metric_name)
                        group.estimated_benefits[metric] = value
                    except (ValueError, KeyError):
                        pass
                
                # Analyze config differences between devices in the group
                if len(group_devices) >= 2:
                    for i in range(len(group_devices) - 1):
                        for j in range(i + 1, len(group_devices)):
                            diff_result = await self.similarity_analyzer.analyze_config_differences(
                                group_devices[i], group_devices[j]
                            )
                            if "error" not in diff_result:
                                group.add_config_difference({
                                    "device1_id": group_devices[i],
                                    "device2_id": group_devices[j],
                                    "sections": diff_result.get("sections", {}),
                                    "categories": diff_result.get("categorized_changes", {})
                                })
            
            # Add the group to the plan
            plan.add_group(group)
        
        # Add the plan to our collection and save
        self.plans[plan.id] = plan
        await self.save_plans()
        
        self.logger.info(f"Created consolidation plan '{name}' with {len(plan.groups)} device groups")
        return plan

    async def get_plan(self, plan_id: str) -> Optional[ConsolidationPlan]:
        """Get a consolidation plan by ID.

        Args:
            plan_id: ID of the plan to get

        Returns:
            Optional[ConsolidationPlan]: Plan if found, None otherwise
        """
        return self.plans.get(plan_id)

    async def get_all_plans(self) -> List[ConsolidationPlan]:
        """Get all consolidation plans.

        Returns:
            List[ConsolidationPlan]: List of all plans
        """
        return list(self.plans.values())

    async def update_plan(self, plan: ConsolidationPlan) -> bool:
        """Update a consolidation plan.

        Args:
            plan: Updated consolidation plan

        Returns:
            bool: True if successful, False otherwise
        """
        if plan.id not in self.plans:
            self.logger.warning(f"Cannot update plan {plan.id}: not found")
            return False
            
        self.plans[plan.id] = plan
        await self.save_plans()
        
        self.logger.info(f"Updated consolidation plan '{plan.name}'")
        return True

    async def delete_plan(self, plan_id: str) -> bool:
        """Delete a consolidation plan.

        Args:
            plan_id: ID of the plan to delete

        Returns:
            bool: True if successful, False otherwise
        """
        if plan_id not in self.plans:
            self.logger.warning(f"Cannot delete plan {plan_id}: not found")
            return False
            
        del self.plans[plan_id]
        await self.save_plans()
        
        self.logger.info(f"Deleted consolidation plan {plan_id}")
        return True

    async def change_plan_status(self, plan_id: str, status: ConsolidationStatus, user: Optional[str] = None) -> bool:
        """Change the status of a consolidation plan.

        Args:
            plan_id: ID of the plan to update
            status: New status for the plan
            user: User making the change

        Returns:
            bool: True if successful, False otherwise
        """
        plan = self.plans.get(plan_id)
        if not plan:
            self.logger.warning(f"Cannot update plan status {plan_id}: not found")
            return False
            
        plan.change_status(status, user)
        await self.save_plans()
        
        self.logger.info(f"Changed status of plan '{plan.name}' to {status.value}")
        return True

    async def find_similar_devices(self, device_id: int, threshold: float = None) -> List[Tuple[int, float, Dict]]:
        """Find devices similar to the specified device.

        Args:
            device_id: ID of the device to find similar devices for
            threshold: Minimum similarity score threshold

        Returns:
            List[Tuple[int, float, Dict]]: List of (device_id, score, details) for similar devices
        """
        return await self.similarity_analyzer.find_similar_devices(device_id, threshold)

    async def analyze_device_pair(self, device_id1: int, device_id2: int) -> Dict[str, Any]:
        """Analyze the similarity between two devices.

        Args:
            device_id1: ID of the first device
            device_id2: ID of the second device

        Returns:
            Dict[str, Any]: Similarity analysis results
        """
        scores = await self.similarity_analyzer.analyze_device_pair(device_id1, device_id2)
        overall_score = await self.similarity_analyzer.calculate_overall_similarity(scores)
        
        # Convert to a structured result
        result = {
            "overall_similarity": overall_score,
            "factors": {
                factor.value: {
                    "score": score.score,
                    "details": score.details
                } for factor, score in scores.items()
            }
        }
        
        # Add config differences
        config_diff = await self.similarity_analyzer.analyze_config_differences(device_id1, device_id2)
        result["config_differences"] = config_diff
        
        return result

    async def get_plan_devices(self, plan_id: str) -> Dict[int, Dict[str, Any]]:
        """Get detailed device information for all devices in a plan.

        Args:
            plan_id: ID of the plan

        Returns:
            Dict[int, Dict[str, Any]]: Dictionary of device details by device ID
        """
        plan = self.plans.get(plan_id)
        if not plan:
            return {}
            
        device_ids = list(plan.affected_device_ids)
        return await self._get_devices_by_ids(device_ids)

    async def get_group_devices(self, plan_id: str, group_id: str) -> Dict[int, Dict[str, Any]]:
        """Get detailed device information for all devices in a group.

        Args:
            plan_id: ID of the plan
            group_id: ID of the group

        Returns:
            Dict[int, Dict[str, Any]]: Dictionary of device details by device ID
        """
        plan = self.plans.get(plan_id)
        if not plan:
            return {}
            
        group = plan.get_group(group_id)
        if not group:
            return {}
            
        return await self._get_devices_by_ids(group.device_ids)

    async def export_plan(self, plan_id: str, file_path: Optional[str] = None) -> bool:
        """Export a consolidation plan to a JSON file.

        Args:
            plan_id: ID of the plan to export
            file_path: Optional path to save the file (defaults to config dir)

        Returns:
            bool: True if successful, False otherwise
        """
        plan = self.plans.get(plan_id)
        if not plan:
            self.logger.warning(f"Cannot export plan {plan_id}: not found")
            return False
            
        if not file_path:
            file_path = os.path.join(self.config_dir, f"plan_{plan_id}.json")
            
        return plan.export_to_json(file_path)

    async def import_plan(self, file_path: str) -> Optional[str]:
        """Import a consolidation plan from a JSON file.

        Args:
            file_path: Path to the JSON file

        Returns:
            Optional[str]: ID of the imported plan if successful, None otherwise
        """
        plan = ConsolidationPlan.import_from_json(file_path)
        if not plan:
            self.logger.error(f"Failed to import plan from {file_path}")
            return None
            
        # Add the plan to our collection and save
        self.plans[plan.id] = plan
        await self.save_plans()
        
        self.logger.info(f"Imported consolidation plan '{plan.name}'")
        return plan.id

    async def get_all_device_types(self) -> List[str]:
        """Get a list of all device types in the system.

        Returns:
            List[str]: List of device types
        """
        if not self.db_manager:
            return []
            
        try:
            devices = await self.db_manager.get_devices()
            types = set(device.get("device_type", "") for device in devices)
            return sorted([t for t in types if t])
        except Exception as e:
            self.logger.error(f"Error getting device types: {str(e)}")
            return []

    async def get_all_locations(self) -> List[str]:
        """Get a list of all device locations in the system.

        Returns:
            List[str]: List of locations
        """
        if not self.db_manager:
            return []
            
        try:
            devices = await self.db_manager.get_devices()
            locations = set(device.get("location", "") for device in devices)
            return sorted([loc for loc in locations if loc])
        except Exception as e:
            self.logger.error(f"Error getting device locations: {str(e)}")
            return []

    async def _get_filtered_devices(self, device_type: Optional[str] = None, 
                                   location: Optional[str] = None) -> List[Dict[str, Any]]:
        """Get devices matching the specified filters.

        Args:
            device_type: Optional filter for device type
            location: Optional filter for location

        Returns:
            List[Dict[str, Any]]: List of matching devices
        """
        if not self.db_manager:
            return []
            
        try:
            devices = await self.db_manager.get_devices()
            
            # Apply filters
            filtered_devices = devices
            
            if device_type:
                filtered_devices = [d for d in filtered_devices if d.get("device_type") == device_type]
                
            if location:
                filtered_devices = [d for d in filtered_devices if d.get("location") == location]
                
            return filtered_devices
        except Exception as e:
            self.logger.error(f"Error getting filtered devices: {str(e)}")
            return []

    async def _get_devices_by_ids(self, device_ids: List[int]) -> Dict[int, Dict[str, Any]]:
        """Get device details for the specified device IDs.

        Args:
            device_ids: List of device IDs to get details for

        Returns:
            Dict[int, Dict[str, Any]]: Dictionary of device details by device ID
        """
        if not self.db_manager:
            return {}
            
        result = {}
        for device_id in device_ids:
            try:
                device = await self.db_manager.get_device(device_id)
                if device:
                    result[device_id] = device
            except Exception as e:
                self.logger.error(f"Error getting device {device_id}: {str(e)}")
                
        return result 