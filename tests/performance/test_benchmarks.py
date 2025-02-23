import pytest
import time
from pulsarnet.backup_operations.backup_manager import BackupManager
from pulsarnet.storage_management.storage_manager import StorageManager

@pytest.mark.benchmark
class TestPerformance:
    @pytest.fixture
    async def benchmark_setup(self, resource_manager):
        """Setup for benchmark tests."""
        backup_manager = BackupManager()
        storage_manager = StorageManager()
        await backup_manager.initialize()
        await storage_manager.initialize()
        yield backup_manager, storage_manager
        await backup_manager.shutdown()
        await storage_manager.shutdown()
        await resource_manager.cleanup()

    async def test_backup_performance(self, benchmark_setup, async_helper):
        """Test backup operation performance."""
        backup_manager, _ = benchmark_setup
        
        start_time = time.time()
        for i in range(10):
            await async_helper.with_timeout(
                backup_manager.backup_device(f"device_{i}"),
                timeout=30.0
            )
        duration = time.time() - start_time
        
        # Assert performance requirements
        assert duration < 60.0, f"Backup operations took too long: {duration} seconds"

    async def test_storage_performance(self, benchmark_setup, async_helper):
        """Test storage operation performance."""
        _, storage_manager = benchmark_setup
        
        # Test write performance
        start_time = time.time()
        for i in range(100):
            await async_helper.with_timeout(
                storage_manager.store_backup(f"test_data_{i}"),
                timeout=1.0
            )
        write_duration = time.time() - start_time
        
        # Test read performance
        start_time = time.time()
        for i in range(100):
            await async_helper.with_timeout(
                storage_manager.get_backup_content(f"test_data_{i}"),
                timeout=1.0
            )
        read_duration = time.time() - start_time
        
        # Assert performance requirements
        assert write_duration < 10.0, f"Write operations took too long: {write_duration} seconds"
        assert read_duration < 5.0, f"Read operations took too long: {read_duration} seconds"