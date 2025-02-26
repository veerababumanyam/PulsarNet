"""Similarity Analyzer Module for PulsarNet.

This module provides functionality for analyzing network devices,
identifying similarities between them, and determining consolidation opportunities.
"""

import re
import difflib
import logging
from enum import Enum
from typing import Dict, List, Tuple, Set, Optional, Any, NamedTuple, Union
import ipaddress
import asyncio


class SimilarityFactor(Enum):
    """Factors used to determine device similarity."""
    DEVICE_TYPE = "device_type"
    SOFTWARE_VERSION = "software_version"
    HARDWARE_MODEL = "hardware_model"
    INTERFACE_COUNT = "interface_count"
    INTERFACE_TYPES = "interface_types"
    CONFIG_STRUCTURE = "config_structure"
    FEATURE_SET = "feature_set"
    VLAN_CONFIG = "vlan_config"
    ROUTING_CONFIG = "routing_config"
    ACL_CONFIG = "acl_config"
    QOS_CONFIG = "qos_config"
    UTILIZATION = "utilization"
    LOCATION = "location"
    ROLE = "role"


class SimilarityScore(NamedTuple):
    """Score and details for a similarity factor."""
    score: float
    details: str


class SimilarityAnalyzer:
    """Class for analyzing similarities between network devices."""

    def __init__(self, db_manager=None):
        """Initialize the similarity analyzer.

        Args:
            db_manager: Database manager for accessing device data
        """
        self.db_manager = db_manager
        self.logger = logging.getLogger("pulsarnet.consolidation.similarity_analyzer")
        self.factor_weights: Dict[SimilarityFactor, float] = {
            SimilarityFactor.DEVICE_TYPE: 0.15,
            SimilarityFactor.SOFTWARE_VERSION: 0.10,
            SimilarityFactor.HARDWARE_MODEL: 0.15,
            SimilarityFactor.INTERFACE_COUNT: 0.05,
            SimilarityFactor.INTERFACE_TYPES: 0.10,
            SimilarityFactor.CONFIG_STRUCTURE: 0.15,
            SimilarityFactor.FEATURE_SET: 0.10,
            SimilarityFactor.VLAN_CONFIG: 0.05,
            SimilarityFactor.ROUTING_CONFIG: 0.05,
            SimilarityFactor.ACL_CONFIG: 0.05,
            SimilarityFactor.QOS_CONFIG: 0.02,
            SimilarityFactor.UTILIZATION: 0.05,
            SimilarityFactor.LOCATION: 0.03,
            SimilarityFactor.ROLE: 0.05,
        }
        self.min_similarity_threshold = 0.7  # Default threshold for similarity

    async def initialize(self, db_manager):
        """Initialize the analyzer with a database manager.

        Args:
            db_manager: Database manager to use
        """
        self.db_manager = db_manager
        self.logger.debug("Similarity analyzer initialized")

    async def analyze_device_pair(self, device_id1: int, device_id2: int) -> Dict[SimilarityFactor, SimilarityScore]:
        """Analyze the similarity between two devices.

        Args:
            device_id1: ID of the first device
            device_id2: ID of the second device

        Returns:
            Dict[SimilarityFactor, SimilarityScore]: Similarity scores by factor
        """
        self.logger.debug(f"Analyzing similarity between devices {device_id1} and {device_id2}")
        
        # Get device data
        device1 = await self._get_device_data(device_id1)
        device2 = await self._get_device_data(device_id2)
        
        if not device1 or not device2:
            self.logger.warning(f"Could not analyze devices: {device_id1} or {device_id2} not found")
            return {}
        
        # Calculate similarity for each factor
        similarity_scores = {}
        
        # Calculate basic device type similarity
        similarity_scores[SimilarityFactor.DEVICE_TYPE] = await self._compare_device_type(device1, device2)
        
        # Compare software versions
        similarity_scores[SimilarityFactor.SOFTWARE_VERSION] = await self._compare_software_version(device1, device2)
        
        # Compare hardware models
        similarity_scores[SimilarityFactor.HARDWARE_MODEL] = await self._compare_hardware_model(device1, device2)
        
        # Compare interfaces
        similarity_scores[SimilarityFactor.INTERFACE_COUNT] = await self._compare_interface_count(device1, device2)
        similarity_scores[SimilarityFactor.INTERFACE_TYPES] = await self._compare_interface_types(device1, device2)
        
        # Compare configurations
        backup1 = await self._get_latest_backup(device_id1)
        backup2 = await self._get_latest_backup(device_id2)
        
        if backup1 and backup2:
            similarity_scores[SimilarityFactor.CONFIG_STRUCTURE] = await self._compare_config_structure(backup1, backup2)
            similarity_scores[SimilarityFactor.FEATURE_SET] = await self._compare_features(backup1, backup2)
            similarity_scores[SimilarityFactor.VLAN_CONFIG] = await self._compare_vlan_config(backup1, backup2)
            similarity_scores[SimilarityFactor.ROUTING_CONFIG] = await self._compare_routing_config(backup1, backup2)
            similarity_scores[SimilarityFactor.ACL_CONFIG] = await self._compare_acl_config(backup1, backup2)
            similarity_scores[SimilarityFactor.QOS_CONFIG] = await self._compare_qos_config(backup1, backup2)
        
        # Compare utilization metrics
        similarity_scores[SimilarityFactor.UTILIZATION] = await self._compare_utilization(device_id1, device_id2)
        
        # Compare location data
        similarity_scores[SimilarityFactor.LOCATION] = await self._compare_location(device1, device2)
        
        # Compare device roles
        similarity_scores[SimilarityFactor.ROLE] = await self._compare_role(device1, device2)
        
        self.logger.debug(f"Similarity analysis completed for devices {device_id1} and {device_id2}")
        return similarity_scores

    async def calculate_overall_similarity(self, scores: Dict[SimilarityFactor, SimilarityScore]) -> float:
        """Calculate an overall similarity score from individual factor scores.

        Args:
            scores: Dictionary of similarity scores by factor

        Returns:
            float: Overall weighted similarity score (0.0-1.0)
        """
        if not scores:
            return 0.0
            
        total_weight = 0.0
        weighted_score = 0.0
        
        for factor, score_details in scores.items():
            weight = self.factor_weights.get(factor, 0.0)
            total_weight += weight
            weighted_score += weight * score_details.score
        
        # Normalize the score if we have weights
        if total_weight > 0:
            return weighted_score / total_weight
        return 0.0

    async def find_similar_devices(self, device_id: int, threshold: float = None) -> List[Tuple[int, float, Dict]]:
        """Find devices similar to the specified device.

        Args:
            device_id: ID of the device to find similar devices for
            threshold: Minimum similarity score threshold (defaults to class threshold)

        Returns:
            List[Tuple[int, float, Dict]]: List of (device_id, score, details) for similar devices
        """
        if threshold is None:
            threshold = self.min_similarity_threshold
            
        all_devices = await self._get_all_device_ids()
        similar_devices = []
        
        for other_id in all_devices:
            if other_id == device_id:
                continue
                
            # Analyze similarity
            scores = await self.analyze_device_pair(device_id, other_id)
            overall_score = await self.calculate_overall_similarity(scores)
            
            if overall_score >= threshold:
                details = {
                    "by_factor": {
                        factor.value: {
                            "score": score.score,
                            "details": score.details
                        } for factor, score in scores.items()
                    },
                    "overall_score": overall_score
                }
                similar_devices.append((other_id, overall_score, details))
        
        # Sort by similarity score (descending)
        similar_devices.sort(key=lambda x: x[1], reverse=True)
        return similar_devices

    async def identify_consolidation_groups(self, threshold: float = None) -> List[List[int]]:
        """Identify groups of similar devices that could be consolidated.

        Args:
            threshold: Minimum similarity score threshold

        Returns:
            List[List[int]]: List of device ID groups that could be consolidated
        """
        if threshold is None:
            threshold = self.min_similarity_threshold
            
        all_devices = await self._get_all_device_ids()
        # Use a simple graph representation where devices are nodes
        # and edges represent similarity above threshold
        similarity_graph: Dict[int, Set[int]] = {device_id: set() for device_id in all_devices}
        
        # Build the similarity graph
        for i, device1 in enumerate(all_devices):
            for device2 in all_devices[i+1:]:
                scores = await self.analyze_device_pair(device1, device2)
                overall_score = await self.calculate_overall_similarity(scores)
                
                if overall_score >= threshold:
                    similarity_graph[device1].add(device2)
                    similarity_graph[device2].add(device1)
        
        # Find connected components in the graph (groups of similar devices)
        visited = set()
        groups = []
        
        for device_id in all_devices:
            if device_id in visited:
                continue
                
            # BFS to find all similar devices
            group = []
            queue = [device_id]
            visited.add(device_id)
            
            while queue:
                current_id = queue.pop(0)
                group.append(current_id)
                
                for neighbor in similarity_graph[current_id]:
                    if neighbor not in visited:
                        visited.add(neighbor)
                        queue.append(neighbor)
            
            if len(group) > 1:  # Only include groups with more than one device
                groups.append(group)
        
        return groups

    async def analyze_config_differences(self, device_id1: int, device_id2: int) -> Dict[str, Any]:
        """Analyze the differences between device configurations.

        Args:
            device_id1: ID of the first device
            device_id2: ID of the second device

        Returns:
            Dict[str, Any]: Details of configuration differences
        """
        backup1 = await self._get_latest_backup(device_id1)
        backup2 = await self._get_latest_backup(device_id2)
        
        if not backup1 or not backup2:
            return {"error": "Could not find backups for both devices"}
            
        # Compare configurations
        diff = list(difflib.unified_diff(
            backup1.splitlines(),
            backup2.splitlines(),
            lineterm='',
            n=3
        ))
        
        # Calculate statistics about the differences
        added_lines = [line for line in diff if line.startswith('+') and not line.startswith('+++')]
        removed_lines = [line for line in diff if line.startswith('-') and not line.startswith('---')]
        changed_sections = self._identify_changed_sections(diff)
        
        # Analyze what the changes represent (interfaces, routing, etc.)
        categorized_changes = self._categorize_changes(added_lines, removed_lines)
        
        return {
            "diff_count": len(diff),
            "added_count": len(added_lines),
            "removed_count": len(removed_lines),
            "sections": changed_sections,
            "categorized_changes": categorized_changes,
            "full_diff": diff[:100] if len(diff) > 100 else diff  # Limit the size of the full diff
        }

    async def generate_consolidation_recommendations(self, device_ids: List[int]) -> Dict[str, Any]:
        """Generate recommendations for consolidating a group of devices.

        Args:
            device_ids: List of device IDs to analyze for consolidation

        Returns:
            Dict[str, Any]: Consolidation recommendations
        """
        if len(device_ids) < 2:
            return {"error": "At least two devices are required for consolidation analysis"}
            
        devices = []
        for device_id in device_ids:
            device_data = await self._get_device_data(device_id)
            if device_data:
                devices.append((device_id, device_data))
                
        if len(devices) < 2:
            return {"error": "Could not find data for enough devices"}
            
        # Analyze device roles, models, and utilization to determine the best consolidation strategy
        device_types = {}
        model_counts = {}
        total_interfaces = 0
        used_interfaces = 0
        location_groups = {}
        
        for device_id, device_data in devices:
            device_type = device_data.get("device_type", "unknown")
            device_types[device_type] = device_types.get(device_type, 0) + 1
            
            model = device_data.get("hardware_model", "unknown")
            model_counts[model] = model_counts.get(model, 0) + 1
            
            # Count interfaces if available
            interfaces = device_data.get("interfaces", [])
            total_interfaces += len(interfaces)
            used_interfaces += sum(1 for i in interfaces if i.get("status") == "up")
            
            # Group by location
            location = device_data.get("location", "unknown")
            if location not in location_groups:
                location_groups[location] = []
            location_groups[location].append(device_id)
        
        # Determine predominant device type and model
        predominant_type = max(device_types.items(), key=lambda x: x[1])[0] if device_types else "unknown"
        predominant_model = max(model_counts.items(), key=lambda x: x[1])[0] if model_counts else "unknown"
        
        # Calculate utilization
        utilization_ratio = used_interfaces / total_interfaces if total_interfaces > 0 else 0
        
        # Generate recommendations based on analysis
        recommendations = {
            "predominant_type": predominant_type,
            "predominant_model": predominant_model,
            "device_count": len(devices),
            "total_interfaces": total_interfaces,
            "used_interfaces": used_interfaces,
            "utilization_ratio": utilization_ratio,
            "locations": list(location_groups.keys()),
        }
        
        # Determine consolidation strategy
        if utilization_ratio < 0.5:
            recommendations["strategy"] = "MERGE_INTO_EXISTING"
            recommendations["explanation"] = "Low utilization suggests these devices could be consolidated by merging their functions into fewer devices."
        elif len(location_groups) > 1:
            recommendations["strategy"] = "STANDARDIZE_CONFIG"
            recommendations["explanation"] = "Devices are in different locations. Standardize configurations while keeping separate physical devices."
        elif len(model_counts) > 2:
            recommendations["strategy"] = "REPLACE_WITH_NEW"
            recommendations["explanation"] = "Multiple device models suggest replacing with standardized newer models."
        else:
            recommendations["strategy"] = "MERGE_INTO_EXISTING"
            recommendations["explanation"] = "Devices appear similar and could be consolidated to reduce count."
            
        # Recommended primary device
        if devices:
            # Choose the device with the newest software if available
            devices_with_versions = [(id, data.get("software_version", "")) for id, data in devices]
            devices_with_versions.sort(key=lambda x: x[1], reverse=True)
            recommendations["recommended_primary"] = devices_with_versions[0][0]
            
        # Estimated benefits
        potential_reduction = max(0, len(devices) - max(1, int(len(devices) * utilization_ratio)))
        recommendations["estimated_benefits"] = {
            "cost_savings": potential_reduction * 5000,  # Rough estimate of savings per device
            "power_reduction": potential_reduction * 500,  # Watts
            "space_savings": potential_reduction,  # Rack units
            "management_simplification": len(devices) / (len(devices) - potential_reduction) if potential_reduction < len(devices) else float('inf')
        }
        
        return recommendations

    async def _get_device_data(self, device_id: int) -> Optional[Dict[str, Any]]:
        """Get device data from the database.

        Args:
            device_id: ID of the device

        Returns:
            Optional[Dict[str, Any]]: Device data if found
        """
        if not self.db_manager:
            self.logger.error("No database manager available")
            return None
            
        try:
            return await self.db_manager.get_device(device_id)
        except Exception as e:
            self.logger.error(f"Error retrieving device data: {str(e)}")
            return None

    async def _get_all_device_ids(self) -> List[int]:
        """Get all device IDs from the database.

        Returns:
            List[int]: List of all device IDs
        """
        if not self.db_manager:
            self.logger.error("No database manager available")
            return []
            
        try:
            devices = await self.db_manager.get_devices()
            return [device["id"] for device in devices]
        except Exception as e:
            self.logger.error(f"Error retrieving device IDs: {str(e)}")
            return []

    async def _get_latest_backup(self, device_id: int) -> Optional[str]:
        """Get the latest backup for a device.

        Args:
            device_id: ID of the device

        Returns:
            Optional[str]: Backup configuration text if found
        """
        if not self.db_manager:
            self.logger.error("No database manager available")
            return None
            
        try:
            # Get the latest backup from the database
            backups = await self.db_manager.get_backups(device_id)
            if not backups:
                return None
                
            # Find the most recent backup
            latest_backup = max(backups, key=lambda b: b.get("created_at", ""))
            
            # Read the backup file
            with open(latest_backup["file_path"], "r") as f:
                return f.read()
        except Exception as e:
            self.logger.error(f"Error retrieving backup: {str(e)}")
            return None

    async def _compare_device_type(self, device1: Dict[str, Any], device2: Dict[str, Any]) -> SimilarityScore:
        """Compare device types for similarity.

        Args:
            device1: First device data
            device2: Second device data

        Returns:
            SimilarityScore: Similarity score and details
        """
        type1 = device1.get("device_type", "")
        type2 = device2.get("device_type", "")
        
        if not type1 or not type2:
            return SimilarityScore(0.0, "Missing device type information")
            
        if type1 == type2:
            return SimilarityScore(1.0, f"Identical device types: {type1}")
            
        # Check for related device types (e.g., cisco_ios and cisco_nxos)
        type1_parts = type1.split("_")
        type2_parts = type2.split("_")
        
        if type1_parts and type2_parts and type1_parts[0] == type2_parts[0]:
            return SimilarityScore(0.7, f"Related device types from same vendor: {type1_parts[0]}")
            
        return SimilarityScore(0.0, f"Different device types: {type1} vs {type2}")

    async def _compare_software_version(self, device1: Dict[str, Any], device2: Dict[str, Any]) -> SimilarityScore:
        """Compare software versions for similarity.

        Args:
            device1: First device data
            device2: Second device data

        Returns:
            SimilarityScore: Similarity score and details
        """
        version1 = device1.get("software_version", "")
        version2 = device2.get("software_version", "")
        
        if not version1 or not version2:
            return SimilarityScore(0.5, "Missing version information")
            
        if version1 == version2:
            return SimilarityScore(1.0, f"Identical software versions: {version1}")
            
        # Compare major versions
        v1_parts = re.findall(r'(\d+)\.(\d+)\.?(\d*)', version1)
        v2_parts = re.findall(r'(\d+)\.(\d+)\.?(\d*)', version2)
        
        if v1_parts and v2_parts:
            v1 = [int(x) if x else 0 for x in v1_parts[0]]
            v2 = [int(x) if x else 0 for x in v2_parts[0]]
            
            if v1[0] == v2[0]:  # Same major version
                if v1[1] == v2[1]:  # Same minor version
                    return SimilarityScore(0.9, f"Minor version match: {v1[0]}.{v1[1]}")
                return SimilarityScore(0.7, f"Major version match: {v1[0]}")
        
        return SimilarityScore(0.3, "Different software versions")

    async def _compare_hardware_model(self, device1: Dict[str, Any], device2: Dict[str, Any]) -> SimilarityScore:
        """Compare hardware models for similarity.

        Args:
            device1: First device data
            device2: Second device data

        Returns:
            SimilarityScore: Similarity score and details
        """
        model1 = device1.get("hardware_model", "")
        model2 = device2.get("hardware_model", "")
        
        if not model1 or not model2:
            return SimilarityScore(0.5, "Missing hardware model information")
            
        if model1 == model2:
            return SimilarityScore(1.0, f"Identical hardware models: {model1}")
            
        # Check for related models (e.g., Cisco C3750X-48P and C3750X-24P)
        # Extract model families and compare
        model1_parts = re.findall(r'([A-Za-z]+)[-]?(\d+)[A-Za-z]*[-]?(\d*)', model1)
        model2_parts = re.findall(r'([A-Za-z]+)[-]?(\d+)[A-Za-z]*[-]?(\d*)', model2)
        
        if model1_parts and model2_parts:
            if model1_parts[0][0] == model2_parts[0][0]:
                if model1_parts[0][1] == model2_parts[0][1]:
                    return SimilarityScore(0.8, f"Same model family: {model1_parts[0][0]}{model1_parts[0][1]}")
                return SimilarityScore(0.6, f"Same vendor series: {model1_parts[0][0]}")
        
        return SimilarityScore(0.2, "Different hardware models")

    async def _compare_interface_count(self, device1: Dict[str, Any], device2: Dict[str, Any]) -> SimilarityScore:
        """Compare interface counts for similarity.

        Args:
            device1: First device data
            device2: Second device data

        Returns:
            SimilarityScore: Similarity score and details
        """
        interfaces1 = device1.get("interfaces", [])
        interfaces2 = device2.get("interfaces", [])
        
        count1 = len(interfaces1)
        count2 = len(interfaces2)
        
        if count1 == 0 or count2 == 0:
            return SimilarityScore(0.5, "Missing interface information")
            
        if count1 == count2:
            return SimilarityScore(1.0, f"Identical interface counts: {count1}")
            
        # Calculate similarity based on ratio of interface counts
        ratio = min(count1, count2) / max(count1, count2)
        
        if ratio > 0.8:
            return SimilarityScore(0.9, f"Similar interface counts: {count1} vs {count2}")
        elif ratio > 0.5:
            return SimilarityScore(0.7, f"Moderately similar interface counts: {count1} vs {count2}")
        elif ratio > 0.3:
            return SimilarityScore(0.5, f"Different interface counts: {count1} vs {count2}")
        else:
            return SimilarityScore(0.2, f"Very different interface counts: {count1} vs {count2}")

    async def _compare_interface_types(self, device1: Dict[str, Any], device2: Dict[str, Any]) -> SimilarityScore:
        """Compare interface types for similarity.

        Args:
            device1: First device data
            device2: Second device data

        Returns:
            SimilarityScore: Similarity score and details
        """
        interfaces1 = device1.get("interfaces", [])
        interfaces2 = device2.get("interfaces", [])
        
        if not interfaces1 or not interfaces2:
            return SimilarityScore(0.5, "Missing interface information")
            
        # Count interface types
        types1 = {}
        for iface in interfaces1:
            iface_type = iface.get("type", "unknown")
            types1[iface_type] = types1.get(iface_type, 0) + 1
            
        types2 = {}
        for iface in interfaces2:
            iface_type = iface.get("type", "unknown")
            types2[iface_type] = types2.get(iface_type, 0) + 1
            
        # Check if both devices have the same interface types
        all_types = set(types1.keys()) | set(types2.keys())
        common_types = set(types1.keys()) & set(types2.keys())
        
        type_similarity = len(common_types) / len(all_types) if all_types else 0
        
        # Calculate weighted similarity based on quantities
        weighted_similarity = 0
        total_weight = 0
        
        for itype in common_types:
            count1 = types1.get(itype, 0)
            count2 = types2.get(itype, 0)
            
            # Weight by the average count of this interface type
            weight = (count1 + count2) / 2
            weighted_similarity += weight * (min(count1, count2) / max(count1, count2))
            total_weight += weight
            
        if total_weight:
            weighted_ratio = weighted_similarity / total_weight
            final_score = 0.7 * type_similarity + 0.3 * weighted_ratio
            formatted_ratio = f"{weighted_ratio:.2f}"
        else:
            final_score = type_similarity
            formatted_ratio = "N/A"
            
        details = f"Interface type similarity: {type_similarity:.2f}, Type distribution similarity: {formatted_ratio}"
        return SimilarityScore(final_score, details)

    async def _compare_config_structure(self, config1: str, config2: str) -> SimilarityScore:
        """Compare configuration structures for similarity.

        Args:
            config1: First device configuration
            config2: Second device configuration

        Returns:
            SimilarityScore: Similarity score and details
        """
        if not config1 or not config2:
            return SimilarityScore(0.0, "Missing configuration data")
            
        # Extract main section headers from configs to compare structure
        sections1 = set(re.findall(r'^([\w\-]+)', config1, re.MULTILINE))
        sections2 = set(re.findall(r'^([\w\-]+)', config2, re.MULTILINE))
        
        common_sections = sections1 & sections2
        all_sections = sections1 | sections2
        
        structure_similarity = len(common_sections) / len(all_sections) if all_sections else 0
        
        # Calculate text similarity as a fallback/additional measure
        similarity_ratio = difflib.SequenceMatcher(None, config1, config2).ratio()
        
        # Weighted combination
        final_score = 0.7 * structure_similarity + 0.3 * similarity_ratio
        
        details = f"Configuration structure similarity: {structure_similarity:.2f}, Text similarity: {similarity_ratio:.2f}"
        return SimilarityScore(final_score, details)

    async def _compare_features(self, config1: str, config2: str) -> SimilarityScore:
        """Compare enabled features for similarity.

        Args:
            config1: First device configuration
            config2: Second device configuration

        Returns:
            SimilarityScore: Similarity score and details
        """
        # Features to look for
        features = [
            "spanning-tree", "vtp", "snmp", "tacacs", "radius", 
            "ntp", "logging", "dhcp", "ospf", "eigrp", "bgp", 
            "hsrp", "vrrp", "lacp", "qos", "access-list", "ipsec",
            "ssh", "vlan"
        ]
        
        # Check for each feature in both configurations
        features1 = {}
        features2 = {}
        
        for feature in features:
            features1[feature] = len(re.findall(f"{feature}", config1, re.IGNORECASE)) > 0
            features2[feature] = len(re.findall(f"{feature}", config2, re.IGNORECASE)) > 0
            
        # Count matching features
        matches = sum(1 for f in features if features1[f] == features2[f])
        feature_similarity = matches / len(features)
        
        # Analyze which features are different
        different_features = [f for f in features if features1[f] != features2[f]]
        details = f"Feature similarity: {feature_similarity:.2f}, Different features: {', '.join(different_features)}"
        
        return SimilarityScore(feature_similarity, details)

    async def _compare_vlan_config(self, config1: str, config2: str) -> SimilarityScore:
        """Compare VLAN configurations for similarity.

        Args:
            config1: First device configuration
            config2: Second device configuration

        Returns:
            SimilarityScore: Similarity score and details
        """
        # Extract VLANs from configurations
        vlan_pattern = r'vlan (\d+)'
        vlans1 = set(re.findall(vlan_pattern, config1, re.IGNORECASE))
        vlans2 = set(re.findall(vlan_pattern, config2, re.IGNORECASE))
        
        if not vlans1 and not vlans2:
            return SimilarityScore(1.0, "No VLANs configured on either device")
        
        if not vlans1 or not vlans2:
            return SimilarityScore(0.0, "VLANs on only one device")
            
        common_vlans = vlans1 & vlans2
        all_vlans = vlans1 | vlans2
        
        vlan_similarity = len(common_vlans) / len(all_vlans)
        
        details = f"VLAN similarity: {vlan_similarity:.2f}, Common VLANs: {len(common_vlans)}, Total unique VLANs: {len(all_vlans)}"
        return SimilarityScore(vlan_similarity, details)

    async def _compare_routing_config(self, config1: str, config2: str) -> SimilarityScore:
        """Compare routing configurations for similarity.

        Args:
            config1: First device configuration
            config2: Second device configuration

        Returns:
            SimilarityScore: Similarity score and details
        """
        # Check for routing protocols
        protocols = ["ospf", "eigrp", "bgp", "rip", "isis", "static"]
        
        protocol_presence1 = {}
        protocol_presence2 = {}
        
        for protocol in protocols:
            protocol_presence1[protocol] = len(re.findall(f"router {protocol}", config1, re.IGNORECASE)) > 0
            protocol_presence2[protocol] = len(re.findall(f"router {protocol}", config2, re.IGNORECASE)) > 0
            
        # Count matching protocols
        matching_protocols = sum(1 for p in protocols if protocol_presence1[p] == protocol_presence2[p])
        protocol_similarity = matching_protocols / len(protocols)
        
        # For static routes, try to count and compare them
        static_routes1 = len(re.findall(r'ip route', config1, re.IGNORECASE))
        static_routes2 = len(re.findall(r'ip route', config2, re.IGNORECASE))
        
        static_route_similarity = 0
        if static_routes1 > 0 or static_routes2 > 0:
            static_route_similarity = min(static_routes1, static_routes2) / max(static_routes1, static_routes2)
        
        # Weighted combination
        score = 0.7 * protocol_similarity + 0.3 * static_route_similarity
        
        details = f"Routing protocol similarity: {protocol_similarity:.2f}, Static route similarity: {static_route_similarity:.2f}"
        return SimilarityScore(score, details)

    async def _compare_acl_config(self, config1: str, config2: str) -> SimilarityScore:
        """Compare ACL configurations for similarity.

        Args:
            config1: First device configuration
            config2: Second device configuration

        Returns:
            SimilarityScore: Similarity score and details
        """
        # Extract ACLs
        acl_pattern = r'access-list (\d+|standard|extended|named)'
        acls1 = set(re.findall(acl_pattern, config1, re.IGNORECASE))
        acls2 = set(re.findall(acl_pattern, config2, re.IGNORECASE))
        
        if not acls1 and not acls2:
            return SimilarityScore(1.0, "No ACLs configured on either device")
        
        if not acls1 or not acls2:
            return SimilarityScore(0.0, "ACLs on only one device")
            
        # Compare ACL presence
        common_acls = acls1 & acls2
        all_acls = acls1 | acls2
        
        acl_presence_similarity = len(common_acls) / len(all_acls)
        
        # Count ACL rules
        acl_rule_count1 = len(re.findall(r'permit|deny', config1, re.IGNORECASE))
        acl_rule_count2 = len(re.findall(r'permit|deny', config2, re.IGNORECASE))
        
        if acl_rule_count1 == 0 and acl_rule_count2 == 0:
            rule_count_similarity = 1.0
        elif acl_rule_count1 == 0 or acl_rule_count2 == 0:
            rule_count_similarity = 0.0
        else:
            rule_count_similarity = min(acl_rule_count1, acl_rule_count2) / max(acl_rule_count1, acl_rule_count2)
        
        # Weighted combination
        score = 0.7 * acl_presence_similarity + 0.3 * rule_count_similarity
        
        details = f"ACL presence similarity: {acl_presence_similarity:.2f}, Rule count similarity: {rule_count_similarity:.2f}"
        return SimilarityScore(score, details)

    async def _compare_qos_config(self, config1: str, config2: str) -> SimilarityScore:
        """Compare QoS configurations for similarity.

        Args:
            config1: First device configuration
            config2: Second device configuration

        Returns:
            SimilarityScore: Similarity score and details
        """
        # Check for QoS keywords
        qos_keywords = [
            "service-policy", "policy-map", "class-map", "priority-queue",
            "bandwidth", "shape", "police", "dscp", "precedence", "cos"
        ]
        
        # Count QoS keywords in each config
        keyword_counts1 = {kw: len(re.findall(kw, config1, re.IGNORECASE)) for kw in qos_keywords}
        keyword_counts2 = {kw: len(re.findall(kw, config2, re.IGNORECASE)) for kw in qos_keywords}
        
        # Check if either device has QoS configured
        has_qos1 = any(count > 0 for count in keyword_counts1.values())
        has_qos2 = any(count > 0 for count in keyword_counts2.values())
        
        if not has_qos1 and not has_qos2:
            return SimilarityScore(1.0, "No QoS configured on either device")
        
        if not has_qos1 or not has_qos2:
            return SimilarityScore(0.0, "QoS on only one device")
        
        # Calculate similarity between keyword counts
        similarity_sum = 0
        keyword_count = 0
        
        for kw in qos_keywords:
            count1 = keyword_counts1.get(kw, 0)
            count2 = keyword_counts2.get(kw, 0)
            
            if count1 > 0 or count2 > 0:
                keyword_count += 1
                similarity_sum += min(count1, count2) / max(count1, count2)
        
        if keyword_count == 0:
            return SimilarityScore(0.0, "No matching QoS features")
            
        score = similarity_sum / keyword_count
        details = f"QoS configuration similarity: {score:.2f}, Matching QoS features: {keyword_count}/{len(qos_keywords)}"
        return SimilarityScore(score, details)

    async def _compare_utilization(self, device_id1: int, device_id2: int) -> SimilarityScore:
        """Compare device utilization metrics for similarity.

        Args:
            device_id1: ID of the first device
            device_id2: ID of the second device

        Returns:
            SimilarityScore: Similarity score and details
        """
        # This would require additional monitoring data
        # For now, return a default similarity score
        return SimilarityScore(0.5, "Utilization comparison not implemented")

    async def _compare_location(self, device1: Dict[str, Any], device2: Dict[str, Any]) -> SimilarityScore:
        """Compare device locations for similarity.

        Args:
            device1: First device data
            device2: Second device data

        Returns:
            SimilarityScore: Similarity score and details
        """
        location1 = device1.get("location", "")
        location2 = device2.get("location", "")
        
        if not location1 or not location2:
            return SimilarityScore(0.5, "Missing location information")
            
        if location1 == location2:
            return SimilarityScore(1.0, f"Identical locations: {location1}")
            
        # Try to parse structured location information
        # Format: Building/Floor/Room or similar
        loc1_parts = location1.split("/")
        loc2_parts = location2.split("/")
        
        match_level = 0
        for i in range(min(len(loc1_parts), len(loc2_parts))):
            if loc1_parts[i] == loc2_parts[i]:
                match_level += 1
            else:
                break
                
        if match_level > 0:
            total_levels = max(len(loc1_parts), len(loc2_parts))
            score = match_level / total_levels
            details = f"Location match at {match_level}/{total_levels} levels"
            return SimilarityScore(score, details)
            
        return SimilarityScore(0.0, f"Different locations: {location1} vs {location2}")

    async def _compare_role(self, device1: Dict[str, Any], device2: Dict[str, Any]) -> SimilarityScore:
        """Compare device roles for similarity.

        Args:
            device1: First device data
            device2: Second device data

        Returns:
            SimilarityScore: Similarity score and details
        """
        role1 = device1.get("role", "")
        role2 = device2.get("role", "")
        
        if not role1 or not role2:
            return SimilarityScore(0.5, "Missing role information")
            
        if role1 == role2:
            return SimilarityScore(1.0, f"Identical roles: {role1}")
            
        # Define role hierarchies/families
        role_families = {
            "core": ["core", "backbone", "distribution-core"],
            "distribution": ["distribution", "aggregation", "dist"],
            "access": ["access", "edge", "client-access"],
            "internet": ["internet", "gateway", "edge-router", "border"],
            "datacenter": ["datacenter", "dc", "dc-access", "dc-core", "dc-agg"],
            "management": ["management", "mgmt", "mon", "monitoring"]
        }
        
        # Check if roles belong to the same family
        for family, roles in role_families.items():
            if any(r in role1.lower() for r in roles) and any(r in role2.lower() for r in roles):
                return SimilarityScore(0.8, f"Related roles in {family} family")
                
        return SimilarityScore(0.2, f"Different roles: {role1} vs {role2}")

    def _identify_changed_sections(self, diff_lines: List[str]) -> Dict[str, int]:
        """Identify which configuration sections have changes.

        Args:
            diff_lines: List of diff lines

        Returns:
            Dict[str, int]: Count of changes by section
        """
        sections = {}
        current_section = "general"
        section_pattern = r'^[+\-]([a-zA-Z\-]+)'
        
        for line in diff_lines:
            if line.startswith('+++') or line.startswith('---') or line.startswith('@@'):
                continue
                
            section_match = re.search(section_pattern, line)
            if section_match:
                current_section = section_match.group(1)
                
            if current_section not in sections:
                sections[current_section] = 0
                
            sections[current_section] += 1
            
        return sections

    def _categorize_changes(self, added_lines: List[str], removed_lines: List[str]) -> Dict[str, Dict[str, int]]:
        """Categorize configuration changes.

        Args:
            added_lines: Lines added to the configuration
            removed_lines: Lines removed from the configuration

        Returns:
            Dict[str, Dict[str, int]]: Categorized changes
        """
        categories = {
            "interface": r'interface',
            "routing": r'(router|ip route|ospf|eigrp|bgp)',
            "acl": r'access-list|ip access',
            "vlan": r'vlan',
            "security": r'(tacacs|radius|aaa|key|crypto|certificate)',
            "management": r'(snmp|syslog|ntp|logging)',
            "qos": r'(service-policy|policy-map|class-map)',
            "other": r'.*'
        }
        
        categorized = {
            "added": {cat: 0 for cat in categories},
            "removed": {cat: 0 for cat in categories}
        }
        
        for line in added_lines:
            for category, pattern in categories.items():
                if re.search(pattern, line):
                    categorized["added"][category] += 1
                    break
                    
        for line in removed_lines:
            for category, pattern in categories.items():
                if re.search(pattern, line):
                    categorized["removed"][category] += 1
                    break
                    
        return categorized 