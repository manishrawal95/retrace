"""TCP server that receives JSON event data from instrumented agents."""

from __future__ import annotations

import asyncio
import json
import logging
from typing import Any

logger = logging.getLogger(__name__)


class RetraceServer:
    """Asyncio TCP server that accepts connections and pushes parsed events to a queue."""

    def __init__(self, queue: asyncio.Queue[dict[str, Any]], host: str = "127.0.0.1", port: int = 8765) -> None:
        self.queue = queue
        self.host = host
        self.port = port
        self._server: asyncio.Server | None = None

    async def handle_connection(self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter) -> None:
        """Handle an incoming client connection, reading newline-delimited JSON."""
        peer = writer.get_extra_info("peername")
        logger.info("Client connected: %s", peer)
        await self.queue.put({"type": "status", "payload": {"content": f"Client connected: {peer}"}})

        try:
            while True:
                line = await reader.readline()
                if not line:
                    break
                try:
                    data = json.loads(line.decode("utf-8").strip())
                    await self.queue.put(data)
                except (json.JSONDecodeError, UnicodeDecodeError) as exc:
                    logger.warning("Failed to parse message: %s", exc)
        except (asyncio.IncompleteReadError, ConnectionResetError):
            logger.info("Client disconnected unexpectedly: %s", peer)
        finally:
            logger.info("Client disconnected: %s", peer)
            await self.queue.put({"type": "status", "payload": {"content": f"Client disconnected: {peer}"}})
            writer.close()
            try:
                await writer.wait_closed()
            except (ConnectionResetError, BrokenPipeError):
                pass

    async def start(self) -> None:
        """Start the TCP server."""
        self._server = await asyncio.start_server(self.handle_connection, self.host, self.port)
        logger.info("Retrace server listening on %s:%d", self.host, self.port)

    async def stop(self) -> None:
        """Stop the TCP server."""
        if self._server is not None:
            self._server.close()
            await self._server.wait_closed()
            self._server = None
