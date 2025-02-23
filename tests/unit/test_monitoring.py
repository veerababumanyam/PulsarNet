"""Unit tests for monitoring functionality."""

import pytest
from pulsarnet.monitoring.monitor_manager import MonitorManager
from pulsarnet.monitoring.audit_logger import AuditLogger
from pulsarnet.monitoring.operation_tracker import OperationTracker

@pytest.fixture
def monitor_manager():
    return MonitorManager()

@pytest.fixture
def audit_logger():
    return AuditLogger()

@pytest.fixture
def operation_tracker():
    return OperationTracker()

@pytest.mark.asyncio
async def test_monitor_manager_operations(monitor_manager):
    # Test monitoring initialization
    assert await monitor_manager.initialize() is True
    
    # Test device monitoring
    device_id = 'test-device-1'
    assert await monitor_manager.start_monitoring(device_id) is True
    assert await monitor_manager.is_device_monitored(device_id) is True
    assert await monitor_manager.stop_monitoring(device_id) is True

@pytest.mark.asyncio
async def test_audit_logger_operations(audit_logger):
    # Test audit log creation
    event_data = {
        'event_type': 'device_backup',
        'device_id': 'test-device-1',
        'status': 'success'
    }
    assert await audit_logger.log_event(event_data) is True
    
    # Test audit log retrieval
    logs = await audit_logger.get_logs(limit=1)
    assert len(logs) == 1
    assert logs[0]['event_type'] == 'device_backup'

@pytest.mark.asyncio
async def test_operation_tracker_functions(operation_tracker):
    # Test operation tracking
    operation_id = await operation_tracker.start_operation('backup', 'test-device-1')
    assert operation_id is not None
    
    # Test status updates
    assert await operation_tracker.update_status(operation_id, 'in_progress') is True
    assert await operation_tracker.update_status(operation_id, 'completed') is True
    
    # Test operation retrieval
    operation = await operation_tracker.get_operation(operation_id)
    assert operation['status'] == 'completed'

@pytest.mark.asyncio
async def test_monitor_manager_validation(monitor_manager):
    # Test invalid device monitoring
    with pytest.raises(ValueError):
        await monitor_manager.start_monitoring('')
    
    # Test stopping non-existent monitoring
    with pytest.raises(KeyError):
        await monitor_manager.stop_monitoring('non-existent-device')

@pytest.mark.asyncio
async def test_audit_logger_validation(audit_logger):
    # Test invalid event logging
    with pytest.raises(ValueError):
        await audit_logger.log_event(None)
    
    # Test invalid log retrieval
    with pytest.raises(ValueError):
        await audit_logger.get_logs(limit=-1)

@pytest.mark.asyncio
async def test_operation_tracker_validation(operation_tracker):
    # Test invalid operation start
    with pytest.raises(ValueError):
        await operation_tracker.start_operation('', '')
    
    # Test invalid status update
    with pytest.raises(KeyError):
        await operation_tracker.update_status('invalid-id', 'completed')
    
    # Test invalid operation retrieval
    with pytest.raises(KeyError):
        await operation_tracker.get_operation('non-existent-id')