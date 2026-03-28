"""Client for sending event data to the Retrace TUI server."""

from __future__ import annotations

import asyncio
import json
import logging
from typing import Any

logger = logging.getLogger(__name__)


class RetraceClient:
    """Singleton client that connects to the Retrace TCP server and sends JSON events."""

    _instance: RetraceClient | None = None
    _lock = asyncio.Lock()

    def __new__(cls) -> RetraceClient:
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._writer = None
            cls._instance._reader = None
            cls._instance._connected = False
        return cls._instance

    @classmethod
    def reset(cls) -> None:
        """Reset the singleton instance (useful for testing)."""
        cls._instance = None

    async def connect(self, host: str = "127.0.0.1", port: int = 8765) -> bool:
        """Establish a TCP connection to the Retrace server.

        Returns True if the connection was established, False otherwise.
        Does not raise exceptions — safe to call even if the server is not running.
        """
        if self._connected:
            return True
        try:
            self._reader, self._writer = await asyncio.open_connection(host, port)
            self._connected = True
            logger.info("Connected to Retrace server at %s:%d", host, port)
            return True
        except (ConnectionRefusedError, OSError) as exc:
            logger.debug("Could not connect to Retrace server at %s:%d: %s", host, port, exc)
            self._connected = False
            return False

    async def send_data(self, data: dict[str, Any]) -> None:
        """Send a JSON-encoded message to the server, terminated by a newline.

        Silently ignores errors to avoid crashing the host agent process.
        """
        if not self._connected or self._writer is None:
            return
        try:
            message = json.dumps(data) + "\n"
            self._writer.write(message.encode("utf-8"))
            await self._writer.drain()
        except (ConnectionResetError, BrokenPipeError, OSError) as exc:
            logger.debug("Failed to send data to Retrace server: %s", exc)
            self._connected = False

    async def disconnect(self) -> None:
        """Close the connection to the server."""
        if self._writer is not None:
            try:
                self._writer.close()
                await self._writer.wait_closed()
            except (ConnectionResetError, BrokenPipeError, OSError):
                pass
            finally:
                self._writer = None
                self._reader = None
                self._connected = False

    @property
    def connected(self) -> bool:
        """Whether the client is currently connected."""
        return self._connected
