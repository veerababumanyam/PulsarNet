"""Unit tests for device management functionality."""

import pytest
from pulsarnet.device_management.device import Device
from pulsarnet.device_management.device_group import DeviceGroup
from pulsarnet.device_management.device_manager import DeviceManager

@pytest.fixture
def sample_device():
    return Device(
        name='test-device',
        ip_address='192.168.1.100',
        device_type='router',
        credentials={
            'username': 'admin',
            'password': 'password'
        }
    )

@pytest.fixture
def sample_device_group():
    return DeviceGroup(
        name='test-group',
        description='Test device group'
    )

@pytest.fixture
def device_manager():
    return DeviceManager()

@pytest.mark.asyncio
async def test_device_creation(sample_device):
    assert sample_device.name == 'test-device'
    assert sample_device.ip_address == '192.168.1.100'
    assert sample_device.device_type == 'router'
    assert sample_device.credentials['username'] == 'admin'

@pytest.mark.asyncio
async def test_device_group_operations(sample_device_group, sample_device):
    # Test adding device to group
    sample_device_group.add_device(sample_device)
    assert len(sample_device_group.devices) == 1
    assert sample_device in sample_device_group.devices
    
    # Test removing device from group
    sample_device_group.remove_device(sample_device)
    assert len(sample_device_group.devices) == 0

@pytest.mark.asyncio
async def test_device_manager_operations(device_manager, sample_device):
    # Test adding device
    await device_manager.add_device(sample_device)
    assert len(device_manager.devices) == 1
    
    # Test getting device
    retrieved_device = await device_manager.get_device(sample_device.name)
    assert retrieved_device == sample_device
    
    # Test removing device
    await device_manager.remove_device(sample_device.name)
    assert len(device_manager.devices) == 0

@pytest.mark.asyncio
async def test_device_connection(sample_device):
    # Test device connection simulation
    assert await sample_device.connect() is True
    assert await sample_device.disconnect() is True

@pytest.mark.asyncio
async def test_device_configuration(sample_device):
    # Test configuration operations
    config = 'interface GigabitEthernet0/1\n no shutdown'
    assert await sample_device.backup_config() == config
    assert await sample_device.restore_config(config) is True

@pytest.mark.asyncio
async def test_device_manager_validation(device_manager):
    # Test invalid device addition
    with pytest.raises(ValueError):
        await device_manager.add_device(None)
    
    # Test invalid device removal
    with pytest.raises(KeyError):
        await device_manager.remove_device('non-existent-device')

@pytest.mark.asyncio
async def test_device_group_validation(sample_device_group):
    # Test invalid device addition to group
    with pytest.raises(ValueError):
        sample_device_group.add_device(None)
    
    # Test duplicate device addition
    device = Device(name='test', ip_address='192.168.1.1', device_type='switch')
    sample_device_group.add_device(device)
    with pytest.raises(ValueError):
        sample_device_group.add_device(device)