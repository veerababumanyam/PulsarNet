import asyncio
import contextlib
import os
from pathlib import Path
from typing import AsyncGenerator, Generator
from datetime import datetime
import pytest
from PyQt6.QtTest import QTest
from PyQt6.QtCore import Qt, QTimer

class TestResourceManager:
    """Manages test resources and cleanup."""
    
    def __init__(self):
        self.temp_files: list[Path] = []
        self.temp_dirs: list[Path] = []
        self.active_connections: list[str] = []

    async def cleanup(self):
        """Clean up all test resources."""
        # Clean temporary files
        for file_path in self.temp_files:
            if file_path.exists():
                file_path.unlink()
        
        # Clean temporary directories
        for dir_path in self.temp_dirs:
            if dir_path.exists():
                for file in dir_path.glob("**/*"):
                    file.unlink()
                dir_path.rmdir()

        # Close active connections
        for conn in self.active_connections:
            await self.close_connection(conn)

    @contextlib.asynccontextmanager
    async def temp_file(self, content: str = "") -> AsyncGenerator[Path, None]:
        """Create a temporary file for testing."""
        temp_path = Path(f"test_file_{datetime.now().timestamp()}.tmp")
        self.temp_files.append(temp_path)
        temp_path.write_text(content)
        try:
            yield temp_path
        finally:
            if temp_path.exists():
                temp_path.unlink()
            self.temp_files.remove(temp_path)

class QtTestHelper:
    """Helper for Qt GUI testing."""
    
    @staticmethod
    def wait_for(widget, timeout: int = 1000):
        """Wait for widget to be ready."""
        timer = QTimer()
        timer.setSingleShot(True)
        timer.start(timeout)
        while timer.isActive() and not widget.isVisible():
            QTest.qWait(10)

    @staticmethod
    def simulate_user_input(widget, text: str):
        """Simulate user typing text."""
        widget.clear()
        QTest.keyClicks(widget, text)
        QTest.qWait(100)

class AsyncTestHelper:
    """Helper for async testing."""
    
    @staticmethod
    async def with_timeout(coro, timeout: float = 5.0):
        """Run coroutine with timeout."""
        try:
            return await asyncio.wait_for(coro, timeout=timeout)
        except asyncio.TimeoutError:
            raise TimeoutError(f"Operation timed out after {timeout} seconds")