"""TCP client for Flashforge 3D printers.

Provides a client class to send M-code commands to Flashforge printers
over a TCP connection, typically on port 8899. Implements a
connect-send-receive-close pattern for each command.
"""
import asyncio
import logging

_LOGGER = logging.getLogger(__name__)

from .const import (
    DEFAULT_TCP_TIMEOUT,
    TCP_BUFFER_SIZE,
    TCP_RESPONSE_TERMINATOR_OK,
    ENCODING_UTF8,
)

# For StreamReader and StreamWriter type hints
from asyncio import StreamReader, StreamWriter
from typing import Optional, Tuple # For Optional and tuple

class FlashforgeTCPClient:
    """
    Client for sending M-code commands to Flashforge printers via TCP.

    This client implements a 'connect-send-close' strategy for each command.
    This enhances robustness by avoiding issues with stale or half-open
    connections that some printer firmwares might not handle well over time.
    The trade-off is potentially higher latency for sequences of rapid commands.
    If different behavior is needed (e.g., for very high-frequency command
    sequences), this client could be adapted to manage persistent connections,
    though that would require more complex connection state management.
    """

    def __init__(self, host: str, port: int, timeout: float = DEFAULT_TCP_TIMEOUT) -> None:
        """
        Initialize the TCP client.
        Args:
            host: The printer's IP address or hostname.
            port: The TCP port to connect to (typically 8899 for M-codes).
            timeout: Timeout for network operations.
        """
        self._host = host
        self._port = port
        self._timeout = timeout
        self._reader: Optional[StreamReader] = None
        self._writer: Optional[StreamWriter] = None

    async def _ensure_connected(self) -> None:
        """Ensures a connection is established. Reconnects if necessary."""
        if not self._writer or self._writer.is_closing():
            _LOGGER.debug(
                f"No active connection or writer closing, attempting to connect to {self._host}:{self._port}"
            )
            try:
                self._reader, self._writer = await asyncio.wait_for(
                    asyncio.open_connection(self._host, self._port),
                    timeout=self._timeout,
                )
                _LOGGER.debug(f"Successfully connected to {self._host}:{self._port}")
            except asyncio.TimeoutError:
                _LOGGER.error(f"Timeout connecting to {self._host}:{self._port}")
                self.close()  # Ensure cleanup on timeout
                raise
            except ConnectionRefusedError:
                _LOGGER.error(f"Connection refused by {self._host}:{self._port}")
                self.close()
                raise
            except OSError as e:
                _LOGGER.error(
                    f"Network error connecting to {self._host}:{self._port}: {e}"
                )
                self.close()
                raise

    def close(self) -> None:
        """Closes the connection."""
        if self._writer and not self._writer.is_closing():
            try:
                self._writer.close()
            except Exception as e:
                _LOGGER.debug(f"Error closing writer: {e}")
        self._reader = None
        self._writer = None
        _LOGGER.debug("TCP connection closed.")

    async def send_command(
        self, command: str, response_terminator: str = TCP_RESPONSE_TERMINATOR_OK
    ) -> Tuple[bool, str]: # Use Tuple from typing
        """
        Connects, sends a command, waits for a response ending with the terminator, and closes.

        Args:
            command: The M-code command string to send (e.g., "~M146 ...\r\n").
            response_terminator: The string that indicates the end of a successful response.

        Returns:
            A tuple (success: bool, response_data: str).
            'success' is True if the command was sent and the terminator was found in the response.
            'response_data' contains the full response from the printer.
        """
        full_response_data = ""
        try:
            await self._ensure_connected()
            if not self._writer:  # Connection failed in _ensure_connected
                return False, "Connection failed"

            _LOGGER.debug(
                f"Sending command to {self._host}:{self._port}: {command.strip()}"
            )
            self._writer.write(command.encode(ENCODING_UTF8))
            await asyncio.wait_for(self._writer.drain(), timeout=self._timeout)

            # Read response until terminator or timeout
            while True:
                try:
                    chunk = await asyncio.wait_for(
                        self._reader.read(TCP_BUFFER_SIZE), timeout=self._timeout
                    )
                    if not chunk:  # Connection closed by peer
                        _LOGGER.warning(
                            f"Connection closed by {self._host}:{self._port} while awaiting response."
                        )
                        break

                    # Decode using ENCODING_UTF8, ignoring errors. This is to handle potential
                    # non-UTF-8 characters or binary noise from the printer without crashing.
                    # May result in some data loss if malformed multi-byte UTF-8 sequences
                    # or other encodings are present.
                    decoded_chunk = chunk.decode(ENCODING_UTF8, errors="ignore")
                    full_response_data += decoded_chunk
                    _LOGGER.debug(f"Received chunk: {decoded_chunk.strip()}")

                    if response_terminator in full_response_data:
                        _LOGGER.debug(
                            f"Response terminator '{response_terminator.strip()}' found."
                        )
                        return True, full_response_data.strip()
                except asyncio.TimeoutError:
                    _LOGGER.warning(
                        f"Timeout waiting for response from {self._host}:{self._port} after sending command. Partial response: {full_response_data.strip()}"
                    )
                    break  # Exit loop on timeout
                except ConnectionResetError:
                    _LOGGER.warning(
                        f"Connection reset by {self._host}:{self._port} while awaiting response."
                    )
                    break
                except Exception as e:  # Catch other read errors
                    _LOGGER.error(
                        f"Error reading response from {self._host}:{self._port}: {e}. Partial response: {full_response_data.strip()}"
                    )
                    break

            return (
                False,
                full_response_data.strip(),
            )  # Terminator not found or other read issue

        except (ConnectionRefusedError, asyncio.TimeoutError, OSError) as e:
            _LOGGER.error(f"Failed to send command to {self._host}:{self._port}: {e}")
            return False, str(e)
        except Exception as e:
            _LOGGER.error(f"An unexpected error occurred in send_command: {e}")
            return False, str(e)
        finally:
            self.close()  # Ensure connection is closed after each command attempt
