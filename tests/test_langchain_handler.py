"""Tests for the LangChain callback handler."""

import asyncio
import json
from dataclasses import dataclass

import pytest

from retrace.callbacks.langchain import RetraceLangChainHandler, _extract_thought
from retrace.client import RetraceClient


@pytest.fixture(autouse=True)
def reset_client():
    RetraceClient.reset()
    yield
    RetraceClient.reset()


@dataclass
class FakeAgentAction:
    tool: str
    tool_input: str
    log: str


@pytest.mark.asyncio
async def test_handler_sends_thought_action_observation():
    """Test that the handler captures thought, action, and observation events."""
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

    handler = RetraceLangChainHandler(port=port)
    await asyncio.sleep(0.1)

    # Simulate an agent action with a thought in the log
    action = FakeAgentAction(
        tool="search",
        tool_input="capital of France",
        log="Thought: I need to find the capital of France.\nAction: search",
    )
    handler.on_agent_action(action)
    await asyncio.sleep(0.1)

    # Simulate a tool output
    handler.on_tool_end("The capital of France is Paris.")
    await asyncio.sleep(0.1)

    # Disconnect and stop
    await handler.client.disconnect()
    server.close()
    await server.wait_closed()

    # Parse all received messages
    messages = [json.loads(line) for line in received]
    types = [m["type"] for m in messages]

    assert "thought" in types
    assert "action" in types
    assert "observation" in types

    thought_msg = next(m for m in messages if m["type"] == "thought")
    assert "capital of France" in thought_msg["payload"]["content"]

    action_msg = next(m for m in messages if m["type"] == "action")
    assert action_msg["payload"]["tool"] == "search"
    assert action_msg["payload"]["tool_input"] == "capital of France"

    obs_msg = next(m for m in messages if m["type"] == "observation")
    assert obs_msg["payload"]["content"] == "The capital of France is Paris."


@pytest.mark.asyncio
async def test_handler_does_not_crash_without_server():
    """Test that creating a handler when the server is not running does not crash."""
    handler = RetraceLangChainHandler(port=19998)

    # These should all silently succeed
    action = FakeAgentAction(tool="test", tool_input="input", log="Thought: test\nAction: test")
    handler.on_agent_action(action)
    handler.on_tool_end("output")


def test_extract_thought_with_explicit_prefix():
    log = "Thought: I need to search for this.\nAction: search"
    assert _extract_thought(log) == "I need to search for this."


def test_extract_thought_without_prefix():
    log = "I should look this up\nAction: search"
    assert _extract_thought(log) == "I should look this up"


def test_extract_thought_returns_none_for_empty():
    assert _extract_thought("") is None
    assert _extract_thought("Action: search") is None
