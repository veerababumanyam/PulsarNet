import pytest
from PyQt6.QtWidgets import QApplication
import os
import sys

# Ensure proper path setup
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

@pytest.fixture(scope="session")
def qapp():
    """Create a Qt Application instance for the entire test session."""
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    return app

@pytest.fixture(autouse=True)
def setup_test_env():
    """Setup test environment variables."""
    os.environ['TESTING'] = 'true'
    os.environ['TEST_DB_PATH'] = ':memory:'
    yield
    os.environ.pop('TESTING', None)
    os.environ.pop('TEST_DB_PATH', None)