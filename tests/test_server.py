"""Tests for the Retrace TCP server."""

import asyncio
import json

import pytest

from retrace.server import RetraceServer


@pytest.fixture
async def server_and_queue():
    queue: asyncio.Queue = asyncio.Queue()
    server = RetraceServer(queue, host="127.0.0.1", port=0)
    await server.start()
    # Get the actual port assigned by the OS
    port = server._server.sockets[0].getsockname()[1]
    yield server, queue, port
    await server.stop()


@pytest.mark.asyncio
async def test_server_receives_and_deserializes_json(server_and_queue):
    """Test that the server correctly receives and deserializes JSON data from the client."""
    server, queue, port = server_and_queue

    reader, writer = await asyncio.open_connection("127.0.0.1", port)

    # Wait for the connection status message
    status = await asyncio.wait_for(queue.get(), timeout=2.0)
    assert status["type"] == "status"

    # Send a thought message
    thought = {"type": "thought", "payload": {"timestamp": "2026-01-01T00:00:00Z", "content": "Test thought"}}
    writer.write((json.dumps(thought) + "\n").encode())
    await writer.drain()

    data = await asyncio.wait_for(queue.get(), timeout=2.0)
    assert data["type"] == "thought"
    assert data["payload"]["content"] == "Test thought"

    # Send an action message
    action = {"type": "action", "payload": {"timestamp": "2026-01-01T00:00:00Z", "tool": "search", "tool_input": "test"}}
    writer.write((json.dumps(action) + "\n").encode())
    await writer.drain()

    data = await asyncio.wait_for(queue.get(), timeout=2.0)
    assert data["type"] == "action"
    assert data["payload"]["tool"] == "search"

    # Send an observation message
    obs = {"type": "observation", "payload": {"timestamp": "2026-01-01T00:00:00Z", "content": "Result"}}
    writer.write((json.dumps(obs) + "\n").encode())
    await writer.drain()

    data = await asyncio.wait_for(queue.get(), timeout=2.0)
    assert data["type"] == "observation"
    assert data["payload"]["content"] == "Result"

    writer.close()
    await writer.wait_closed()


@pytest.mark.asyncio
async def test_server_handles_client_disconnect(server_and_queue):
    """Test that the server handles client disconnections without crashing."""
    server, queue, port = server_and_queue

    reader, writer = await asyncio.open_connection("127.0.0.1", port)

    # Wait for connection status
    await asyncio.wait_for(queue.get(), timeout=2.0)

    # Abruptly close the connection
    writer.close()
    await writer.wait_closed()

    # The server should emit a disconnect status message
    status = await asyncio.wait_for(queue.get(), timeout=2.0)
    assert status["type"] == "status"
    assert "disconnected" in status["payload"]["content"].lower() or "disconnect" in status["payload"]["content"].lower()

    # Server should still accept new connections
    reader2, writer2 = await asyncio.open_connection("127.0.0.1", port)
    status2 = await asyncio.wait_for(queue.get(), timeout=2.0)
    assert status2["type"] == "status"

    writer2.close()
    await writer2.wait_closed()


@pytest.mark.asyncio
async def test_server_handles_invalid_json(server_and_queue):
    """Test that the server handles malformed JSON without crashing."""
    server, queue, port = server_and_queue

    reader, writer = await asyncio.open_connection("127.0.0.1", port)
    await asyncio.wait_for(queue.get(), timeout=2.0)  # connection status

    # Send invalid JSON
    writer.write(b"this is not json\n")
    await writer.drain()

    # Send valid JSON after the invalid one — server should still work
    valid = {"type": "thought", "payload": {"content": "still works"}}
    writer.write((json.dumps(valid) + "\n").encode())
    await writer.drain()

    data = await asyncio.wait_for(queue.get(), timeout=2.0)
    assert data["type"] == "thought"
    assert data["payload"]["content"] == "still works"

    writer.close()
    await writer.wait_closed()
