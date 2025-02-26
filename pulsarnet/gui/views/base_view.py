"""Base View Class for PulsarNet GUI Tabs.

This module provides a foundation class for all tab views in the application.
"""

from PyQt6.QtWidgets import QWidget

class BaseTabView(QWidget):
    """Base class for all tab views."""
    
    def __init__(self, main_window):
        """Initialize the base tab view.
        
        Args:
            main_window: Reference to the main window instance
        """
        super().__init__()
        self.main_window = main_window
        self.setup_ui()
        
    def setup_ui(self):
        """Set up the UI components. To be implemented by subclasses."""
        pass 