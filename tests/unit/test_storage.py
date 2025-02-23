\"""Unit tests for storage management functionality."""

import pytest
from pulsarnet.storage_management.storage_manager import StorageManager
from pulsarnet.storage_management.storage_location import StorageLocation
from pulsarnet.storage_management.retention_policy import RetentionPolicy

@pytest.fixture
def sample_storage_location():
    return StorageLocation(
        name='test-location',
        path='/backup/configs',
        max_size=1024 * 1024 * 100  # 100MB
    )

@pytest.fixture
def sample_retention_policy():
    return RetentionPolicy(
        name='test-policy',
        max_backups=5,
        retention_days=30
    )

@pytest.fixture
def storage_manager():
    return StorageManager()

@pytest.mark.asyncio
async def test_storage_location_operations(sample_storage_location):
    # Test basic properties
    assert sample_storage_location.name == 'test-location'
    assert sample_storage_location.path == '/backup/configs'
    assert sample_storage_location.max_size == 1024 * 1024 * 100
    
    # Test space management
    assert await sample_storage_location.get_available_space() > 0
    assert await sample_storage_location.is_space_available(1024) is True

@pytest.mark.asyncio
async def test_retention_policy_operations(sample_retention_policy):
    # Test policy rules
    assert sample_retention_policy.name == 'test-policy'
    assert sample_retention_policy.max_backups == 5
    assert sample_retention_policy.retention_days == 30
    
    # Test policy validation
    assert await sample_retention_policy.validate_backup('test_backup.cfg') is True
    assert await sample_retention_policy.should_retain_backup('old_backup.cfg', 31) is False

@pytest.mark.asyncio
async def test_storage_manager_operations(storage_manager, sample_storage_location):
    # Test location management
    await storage_manager.add_location(sample_storage_location)
    assert len(storage_manager.locations) == 1
    
    # Test backup operations
    backup_data = 'interface GigabitEthernet0/1\n no shutdown'
    filename = 'device_backup.cfg'
    assert await storage_manager.store_backup(backup_data, filename) is True
    assert await storage_manager.verify_backup(filename) is True
    
    # Test cleanup
    assert await storage_manager.cleanup_old_backups() is True

@pytest.mark.asyncio
async def test_storage_validation(storage_manager):
    # Test invalid location addition
    with pytest.raises(ValueError):
        await storage_manager.add_location(None)
    
    # Test invalid backup storage
    with pytest.raises(ValueError):
        await storage_manager.store_backup('', '')
    
    # Test storage limits
    large_data = 'x' * (1024 * 1024 * 200)  # 200MB
    with pytest.raises(ValueError):
        await storage_manager.store_backup(large_data, 'large_backup.cfg')

@pytest.mark.asyncio
async def test_retention_policy_validation(sample_retention_policy):
    # Test invalid policy parameters
    with pytest.raises(ValueError):
        RetentionPolicy(name='', max_backups=-1, retention_days=0)
    
    # Test policy limits
    assert await sample_retention_policy.should_retain_backup('test.cfg', 0) is True
    assert await sample_retention_policy.should_retain_backup('test.cfg', 100) is False"}}}}