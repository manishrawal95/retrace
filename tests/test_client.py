"""Tests for the Retrace client."""

import asyncio
import json

import pytest

from retrace.client import RetraceClient


@pytest.fixture(autouse=True)
def reset_client():
    """Reset the singleton before each test."""
    RetraceClient.reset()
    yield
    RetraceClient.reset()


@pytest.mark.asyncio
async def test_client_graceful_failure_when_server_not_running():
    """Test that the agent process does not crash if the retrace server is not running."""
    client = RetraceClient()
    # Connecting to a port with no server should return False, not raise
    result = await client.connect("127.0.0.1", 19999)
    assert result is False
    assert client.connected is False

    # Sending data when not connected should silently do nothing
    await client.send_data({"type": "thought", "payload": {"content": "test"}})


@pytest.mark.asyncio
async def test_client_connects_and_sends():
    """Test that the client can connect and send data to a real server."""
    received: list[bytes] = []

    async def handle(reader: asyncio.StreamReader, writer: asyncio.StreamWriter) -> None:
        while True:
            line = await reader.readline()
            if not line:
                break
            received.append(line)
        writer.close()

    server = await asyncio.start_server(handle, "127.0.0.1", 0)
    port = server.sockets[0].getsockname()[1]

    client = RetraceClient()
    result = await client.connect("127.0.0.1", port)
    assert result is True
    assert client.connected is True

    await client.send_data({"type": "thought", "payload": {"content": "hello"}})
    await asyncio.sleep(0.1)

    await client.disconnect()
    server.close()
    await server.wait_closed()

    assert len(received) == 1
    data = json.loads(received[0])
    assert data["type"] == "thought"
    assert data["payload"]["content"] == "hello"


@pytest.mark.asyncio
async def test_client_is_singleton():
    """Test that RetraceClient uses singleton pattern."""
    a = RetraceClient()
    b = RetraceClient()
    assert a is b
