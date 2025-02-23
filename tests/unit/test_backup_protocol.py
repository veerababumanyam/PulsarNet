"""Unit tests for backup protocol implementations."""

import pytest
from pulsarnet.backup_operations.backup_protocol import (
    ProtocolType,
    BackupProtocol,
    TFTPProtocol,
    SCPProtocol,
    SFTPProtocol,
    FTPProtocol
)

@pytest.fixture
def tftp_config():
    return {
        'server': 'localhost',
        'port': 69
    }

@pytest.fixture
def sample_config():
    return {
        'server': 'test-server',
        'port': 22,
        'username': 'test-user',
        'password': 'test-pass'
    }

@pytest.mark.asyncio
async def test_tftp_protocol_connect(tftp_config):
    protocol = TFTPProtocol(tftp_config)
    result = await protocol.connect()
    assert result is True

@pytest.mark.asyncio
async def test_tftp_protocol_validate_config():
    protocol = TFTPProtocol({})
    # Test empty config
    result, error = await protocol.validate_config('')
    assert result is False
    assert error == 'Configuration data is empty'

    # Test valid config
    result, error = await protocol.validate_config('interface GigabitEthernet0/1\n no shutdown')
    assert result is True
    assert error is None

@pytest.mark.asyncio
async def test_tftp_protocol_config_diff():
    protocol = TFTPProtocol({})
    old_config = 'interface GigabitEthernet0/1\n shutdown'
    new_config = 'interface GigabitEthernet0/1\n no shutdown'
    
    has_changes, diff = await protocol.get_config_diff(old_config, new_config)
    assert has_changes is True
    assert 'shutdown' in diff
    assert 'no shutdown' in diff

@pytest.mark.asyncio
async def test_sftp_protocol_operations(sample_config):
    protocol = SFTPProtocol(sample_config)
    
    # Test connection
    assert await protocol.connect() is True
    
    # Test config validation
    result, error = await protocol.validate_config('valid config data')
    assert result is True
    assert error is None
    
    # Test upload
    assert await protocol.upload_config('192.168.1.1', 'test config', 'test.cfg') is True
    
    # Test verification
    assert await protocol.verify_backup('test.cfg') is True

@pytest.mark.asyncio
async def test_protocol_type_enum():
    assert ProtocolType.TFTP.value == 'tftp'
    assert ProtocolType.SCP.value == 'scp'
    assert ProtocolType.SFTP.value == 'sftp'
    assert ProtocolType.FTP.value == 'ftp'

@pytest.mark.asyncio
async def test_protocol_error_handling(sample_config):
    protocol = FTPProtocol(sample_config)
    
    # Test validation with invalid config
    result, error = await protocol.validate_config('')
    assert result is False
    assert error == 'Configuration data is empty'
    
    # Test diff with identical configs
    has_changes, diff = await protocol.get_config_diff('config', 'config')
    assert has_changes is False
    assert diff is None