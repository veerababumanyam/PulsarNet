"""Error Handling Module for PulsarNet.

This module provides comprehensive error handling and recovery mechanisms
for the PulsarNet backup system, including error classification,
automatic recovery strategies, and monitoring integration.
"""

from .error_manager import (
    ErrorManager,
    ErrorCategory,
    ErrorSeverity,
    ErrorEvent
)

__all__ = [
    'ErrorManager',
    'ErrorCategory',
    'ErrorSeverity',
    'ErrorEvent'
]