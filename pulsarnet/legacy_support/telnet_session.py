"""Telnet Session Module for PulsarNet.

This module provides the TelnetSession class for managing Telnet connections
to legacy Cisco devices, including command execution and error handling.
"""

import telnetlib
import time
from typing import Optional, List, Tuple
from datetime import datetime
import logging

class TelnetSession:
    """Manages Telnet connections to legacy Cisco devices.
    
    This class handles the establishment of Telnet connections, command execution,
    and proper session cleanup. It includes support for connection timeouts and
    error handling.
    """

    def __init__(self, host: str, username: str, password: str,
                 enable_password: Optional[str] = None,
                 port: int = 23,
                 timeout: int = 10):
        """Initialize a new TelnetSession.

        Args:
            host: IP address or hostname of the target device
            username: Username for authentication
            password: Password for authentication
            enable_password: Enable mode password (if required)
            port: Telnet port number (default: 23)
            timeout: Connection timeout in seconds (default: 10)
        """
        self.host = host
        self.username = username
        self.password = password
        self.enable_password = enable_password
        self.port = port
        self.timeout = timeout
        self.session: Optional[telnetlib.Telnet] = None
        self.last_error: Optional[str] = None

    async def connect(self) -> bool:
        """Establish a Telnet connection to the device.

        Returns:
            bool: True if connection successful, False otherwise
        """
        try:
            self.session = telnetlib.Telnet(self.host, self.port, self.timeout)
            
            # Handle login
            if self._expect_and_send('Username:', self.username) and \
               self._expect_and_send('Password:', self.password):
                
                # Enter enable mode if password provided
                if self.enable_password:
                    self.session.write(b'enable\n')
                    if self._expect_and_send('Password:', self.enable_password):
                        return self._verify_prompt()
                else:
                    return self._verify_prompt()
            
            return False

        except Exception as e:
            self.last_error = f"Connection failed: {str(e)}"
            logging.error(f"Telnet connection failed to {self.host}: {str(e)}")
            return False

    def disconnect(self) -> None:
        """Close the Telnet session safely."""
        if self.session:
            try:
                self.session.write(b'exit\n')
                self.session.close()
            except:
                pass
            finally:
                self.session = None

    async def execute_command(self, command: str, timeout: int = 30) -> Tuple[bool, str]:
        """Execute a command on the device.

        Args:
            command: Command to execute
            timeout: Command timeout in seconds

        Returns:
            Tuple[bool, str]: Success status and command output/error message
        """
        if not self.session:
            return False, "No active session"

        try:
            # Send command
            self.session.write(f"{command}\n".encode('ascii'))
            
            # Wait for command output
            output = self.session.read_until(b'#', timeout).decode('ascii')
            
            # Remove command echo and prompt
            lines = output.split('\n')
            if len(lines) > 1:
                # Remove first line (command echo) and last line (prompt)
                output = '\n'.join(lines[1:-1])
            
            return True, output.strip()

        except Exception as e:
            error_msg = f"Command execution failed: {str(e)}"
            self.last_error = error_msg
            logging.error(f"Telnet command failed on {self.host}: {error_msg}")
            return False, error_msg

    async def execute_commands(self, commands: List[str]) -> List[Tuple[str, bool, str]]:
        """Execute multiple commands sequentially.

        Args:
            commands: List of commands to execute

        Returns:
            List[Tuple[str, bool, str]]: List of (command, success, output)
        """
        results = []
        for cmd in commands:
            success, output = await self.execute_command(cmd)
            results.append((cmd, success, output))
            if not success:
                break
        return results

    def _expect_and_send(self, expect: str, send: str) -> bool:
        """Wait for expected string and send response.

        Args:
            expect: String to wait for
            send: String to send in response

        Returns:
            bool: True if successful, False otherwise
        """
        try:
            self.session.read_until(expect.encode('ascii'), self.timeout)
            self.session.write(f"{send}\n".encode('ascii'))
            time.sleep(0.5)  # Brief pause for device processing
            return True
        except Exception as e:
            self.last_error = f"Expect/Send failed: {str(e)}"
            return False

    def _verify_prompt(self) -> bool:
        """Verify we have reached the device prompt.

        Returns:
            bool: True if prompt found, False otherwise
        """
        try:
            # Send empty line and look for prompt
            self.session.write(b'\n')
            response = self.session.read_until(b'#', self.timeout)
            return b'#' in response
        except Exception as e:
            self.last_error = f"Prompt verification failed: {str(e)}"
            return False