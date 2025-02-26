"""Jump Host Module for PulsarNet.

This module provides the JumpHost class for managing connections through
intermediary routers to access legacy devices.
"""

import asyncio
from typing import Optional, Tuple
import logging
from .telnet_session import TelnetSession

class JumpHost:
    """Manages connections through intermediary routers.
    
    This class handles the establishment of connections through jump hosts
    to reach legacy devices that are not directly accessible.
    """

    def __init__(self, host: str, username: str, password: str,
                 enable_password: Optional[str] = None,
                 port: int = 23,
                 timeout: int = 10):
        """Initialize a new JumpHost.

        Args:
            host: IP address or hostname of the jump host
            username: Username for authentication
            password: Password for authentication
            enable_password: Enable mode password (if required)
            port: Port number (default: 23)
            timeout: Connection timeout in seconds (default: 10)
        """
        self.host = host
        self.username = username
        self.password = password
        self.enable_password = enable_password
        self.port = port
        self.timeout = timeout
        self.session: Optional[TelnetSession] = None
        self.last_error: Optional[str] = None

    async def connect(self) -> bool:
        """Establish a connection to the jump host.

        Returns:
            bool: True if connection successful, False otherwise
        """
        try:
            self.session = TelnetSession(
                host=self.host,
                username=self.username,
                password=self.password,
                enable_password=self.enable_password,
                port=self.port,
                timeout=self.timeout
            )
            return await self.session.connect()

        except Exception as e:
            self.last_error = f"Jump host connection failed: {str(e)}"
            logging.error(f"Failed to connect to jump host {self.host}: {str(e)}")
            return False

    async def connect_to_device(self, device_ip: str, username: str, password: str,
                              enable_password: Optional[str] = None) -> bool:
        """Connect to a target device through the jump host.

        Args:
            device_ip: IP address of the target device
            username: Username for target device
            password: Password for target device
            enable_password: Enable password for target device

        Returns:
            bool: True if connection successful, False otherwise
        """
        if not self.session:
            return False

        try:
            # Send telnet command to target device
            success, _ = await self.session.execute_command(f"telnet {device_ip}")
            if not success:
                return False

            # Handle target device authentication
            if not self.session._expect_and_send('Username:', username) or \
               not self.session._expect_and_send('Password:', password):
                return False

            # Enter enable mode if password provided
            if enable_password:
                self.session.session.write(b'enable\n')
                if not self.session._expect_and_send('Password:', enable_password):
                    return False

            return self.session._verify_prompt()

        except Exception as e:
            self.last_error = f"Target device connection failed: {str(e)}"
            logging.error(f"Failed to connect to device {device_ip} through jump host: {str(e)}")
            return False

    async def execute_device_command(self, command: str, timeout: int = 30) -> Tuple[bool, str]:
        """Execute a command on the target device.

        Args:
            command: Command to execute
            timeout: Command timeout in seconds

        Returns:
            Tuple[bool, str]: Success status and command output/error message
        """
        if not self.session:
            return False, "No active session"

        return await self.session.execute_command(command, timeout)

    def disconnect(self) -> None:
        """Close all sessions safely."""
        if self.session:
            try:
                # Exit from target device if connected
                self.session.session.write(b'exit\n')
                asyncio.sleep(1)
                # Exit from jump host
                self.session.disconnect()
            except:
                pass
            finally:
                self.session = None