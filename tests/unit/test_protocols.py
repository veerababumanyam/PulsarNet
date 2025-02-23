import pytest
from pulsarnet.backup_operations.backup_protocol import SFTPProtocol, TFTPProtocol

@pytest.mark.asyncio
class TestProtocols:
    async def test_sftp_protocol(self, resource_manager, async_helper):
        """Test SFTP protocol operations with proper resource management."""
        protocol = SFTPProtocol()
        
        try:
            # Test connection
            connected = await async_helper.with_timeout(
                protocol.connect(),
                timeout=5.0
            )
            assert connected is True
            
            # Test file transfer
            async with resource_manager.temp_file("test config") as test_file:
                success = await async_helper.with_timeout(
                    protocol.upload_config("192.168.1.1", test_file),
                    timeout=10.0
                )
                assert success is True
                
                # Verify backup
                verified = await async_helper.with_timeout(
                    protocol.verify_backup(test_file.name),
                    timeout=5.0
                )
                assert verified is True
        finally:
            await protocol.disconnect()

    async def test_protocol_error_handling(self, async_helper):
        """Test protocol error scenarios."""
        protocol = TFTPProtocol()
        
        # Test invalid connection
        with pytest.raises(ConnectionError):
            await async_helper.with_timeout(
                protocol.connect(host="invalid-host"),
                timeout=5.0
            )
        
        # Test timeout scenario
        with pytest.raises(TimeoutError):
            await async_helper.with_timeout(
                protocol.upload_config("192.168.1.1", "large_config"),
                timeout=1.0
            )