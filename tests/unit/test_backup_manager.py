import pytest
from pulsarnet.backup_operations.backup_manager import BackupManager

@pytest.mark.asyncio
class TestBackupManager:
    async def test_bulk_upload(self, resource_manager, async_helper):
        """Test bulk upload functionality."""
        backup_manager = BackupManager(resource_manager.get_temp_dir())
        
        # Test devices
        devices = [
            {"ip": f"192.168.1.{i}", "config": {"credentials": f"device_{i}"}}
            for i in range(1, 6)
        ]
        
        # Perform bulk upload
        result = await async_helper.with_timeout(
            backup_manager.bulk_upload(
                devices=devices,
                protocol_type="SFTP",
                priority=5,
                max_concurrent=3
            ),
            timeout=30.0
        )
        
        # Verify results
        assert len(result.successful) > 0, "No successful uploads"
        assert len(result.failed) == 0, f"Failed uploads: {result.failed}"
        assert result.total_time < 20.0, "Bulk upload took too long"

    async def test_bulk_upload_with_failures(self, resource_manager, async_helper):
        """Test bulk upload with some failing devices."""
        backup_manager = BackupManager(resource_manager.get_temp_dir())
        
        # Mix of valid and invalid devices
        devices = [
            {"ip": "192.168.1.1", "config": {"credentials": "valid"}},
            {"ip": "invalid-ip", "config": {"credentials": "invalid"}},
            {"ip": "192.168.1.2", "config": {"credentials": "valid"}}
        ]
        
        result = await async_helper.with_timeout(
            backup_manager.bulk_upload(
                devices=devices,
                protocol_type="SFTP"
            ),
            timeout=30.0
        )
        
        # Verify mixed results
        assert len(result.successful) == 2, "Expected 2 successful uploads"
        assert len(result.failed) == 1, "Expected 1 failed upload"
        assert "invalid-ip" in result.failed, "Expected invalid-ip to fail"