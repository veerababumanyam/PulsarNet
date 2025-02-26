#!/usr/bin/env python3
"""
PulsarNet Application Main Entry

This file serves as the main entry point for the PulsarNet GUI application.
It adheres to ISO/IEC standards for accessibility and usability.
"""

import sys
from PyQt6.QtWidgets import QApplication
from pulsarnet.gui.main_window import MainWindow


def main():
    """Main application entry point."""
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == '__main__':
    main() 