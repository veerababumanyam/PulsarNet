"""Base Controller Class for PulsarNet GUI.

This module provides a foundation class for all controllers in the application.
"""

class BaseController:
    """Base class for controllers handling tab logic."""
    
    def __init__(self, main_window, view):
        """Initialize the base controller.
        
        Args:
            main_window: Reference to the main window instance
            view: Reference to the associated view instance
        """
        self.main_window = main_window
        self.view = view
        self.connect_signals()
        
    def connect_signals(self):
        """Connect signals to slots. To be implemented by subclasses."""
        pass 