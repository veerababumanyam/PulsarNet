"""Unit tests for PulsarNet GUI components."""

import pytest
from PyQt6.QtWidgets import QApplication
from PyQt6.QtTest import QTest
from PyQt6.QtCore import Qt
from pulsarnet.gui.main_window import MainWindow
from pulsarnet.gui.device_dialog import DeviceDialog
from pulsarnet.gui.backup_dialog import BackupDialog

@pytest.fixture
def app():
    """Create a Qt Application instance for testing."""
    return QApplication([])

@pytest.fixture
def main_window(app):
    """Create a MainWindow instance for testing."""
    return MainWindow()

@pytest.fixture
def device_dialog(app):
    """Create a DeviceDialog instance for testing."""
    return DeviceDialog()

@pytest.fixture
def backup_dialog(app):
    """Create a BackupDialog instance for testing."""
    return BackupDialog()

def test_main_window_initialization(main_window):
    """Test main window initialization and basic properties."""
    assert main_window.windowTitle() == 'PulsarNet'
    assert main_window.isVisible() is False

def test_device_dialog_fields(device_dialog):
    """Test device dialog form fields and validation."""
    # Test initial state
    assert device_dialog.windowTitle() == 'Add Device'
    
    # Test form fields existence
    form_layout = device_dialog.layout()
    assert form_layout is not None
    
    # Simulate filling form fields
    device_dialog.name_input.setText('Test Device')
    device_dialog.ip_input.setText('192.168.1.1')
    device_dialog.type_combo.setCurrentText('Router')
    
    assert device_dialog.name_input.text() == 'Test Device'
    assert device_dialog.ip_input.text() == '192.168.1.1'
    assert device_dialog.type_combo.currentText() == 'Router'

def test_backup_dialog_configuration(backup_dialog):
    """Test backup dialog configuration options and validation."""
    # Test initial state
    assert backup_dialog.windowTitle() == 'Backup Configuration'
    
    # Test protocol selection
    backup_dialog.protocol_combo.setCurrentText('TFTP')
    assert backup_dialog.protocol_combo.currentText() == 'TFTP'
    
    # Test server configuration
    backup_dialog.server_input.setText('backup-server')
    backup_dialog.port_input.setValue(69)
    
    assert backup_dialog.server_input.text() == 'backup-server'
    assert backup_dialog.port_input.value() == 69

@pytest.mark.asyncio
async def test_backup_dialog_execution(backup_dialog):
    """Test backup dialog execution flow."""
    # Configure backup settings
    backup_dialog.protocol_combo.setCurrentText('SFTP')
    backup_dialog.server_input.setText('sftp.example.com')
    backup_dialog.port_input.setValue(22)
    backup_dialog.username_input.setText('backup-user')
    backup_dialog.password_input.setText('backup-pass')
    
    # Simulate backup execution
    assert backup_dialog.validate_inputs() is True
    
    # Test backup execution
    result = await backup_dialog.execute_backup()
    assert result is True

def test_main_window_menu_actions(main_window):
    """Test main window menu actions and responses."""
    # Test File menu
    file_menu = main_window.menuBar().findChild(QMenu, 'fileMenu')
    assert file_menu is not None
    
    # Test Edit menu
    edit_menu = main_window.menuBar().findChild(QMenu, 'editMenu')
    assert edit_menu is not None
    
    # Test Help menu
    help_menu = main_window.menuBar().findChild(QMenu, 'helpMenu')
    assert help_menu is not None

def test_device_list_operations(main_window):
    """Test device list operations in main window."""
    # Test adding device
    initial_count = main_window.device_list.count()
    main_window.add_device({
        'name': 'Test Router',
        'ip': '192.168.1.100',
        'type': 'Router'
    })
    assert main_window.device_list.count() == initial_count + 1
    
    # Test selecting device
    main_window.device_list.setCurrentRow(0)
    assert main_window.device_list.currentItem() is not None
    
    # Test removing device
    main_window.remove_selected_device()
    assert main_window.device_list.count() == initial_count

def test_status_bar_updates(main_window):
    """Test status bar message updates."""
    test_message = 'Testing status bar'
    main_window.statusBar().showMessage(test_message)
    assert main_window.statusBar().currentMessage() == test_message

def test_keyboard_shortcuts(main_window):
    """Test keyboard shortcuts and their actions."""
    # Test Add Device shortcut (Ctrl+N)
    QTest.keyClick(main_window, Qt.Key.Key_N, Qt.KeyboardModifier.ControlModifier)
    
    # Test Refresh shortcut (F5)
    QTest.keyClick(main_window, Qt.Key.Key_F5)
    
    # Test Delete shortcut (Delete)
    main_window.device_list.setCurrentRow(0)
    QTest.keyClick(main_window, Qt.Key.Key_Delete)