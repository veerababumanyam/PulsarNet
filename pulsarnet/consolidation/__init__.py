"""Device Consolidation module for PulsarNet.

This module provides functionality for analyzing network devices,
identifying consolidation opportunities, and planning for network
simplification based on device similarities and redundancies.
"""

from .consolidation_manager import DeviceConsolidationManager
from .similarity_analyzer import SimilarityAnalyzer
from .consolidation_plan import ConsolidationPlan, ConsolidationGroup

__all__ = [
    'DeviceConsolidationManager',
    'SimilarityAnalyzer',
    'ConsolidationPlan',
    'ConsolidationGroup'
] 