"""LangChain callback handler that sends agent events to the Retrace TUI."""

from __future__ import annotations

import asyncio
import os
import re
from datetime import datetime, timezone
from typing import Any

from retrace.client import RetraceClient


def _get_or_create_event_loop() -> asyncio.AbstractEventLoop:
    """Get the running event loop or create a new one."""
    try:
        return asyncio.get_running_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        return loop


def _run_async(coro: Any) -> Any:
    """Run a coroutine, handling both sync and async contexts."""
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        loop = None

    if loop is not None and loop.is_running():
        # We're inside an async context — schedule as a task
        task = loop.create_task(coro)
        return task
    else:
        loop = asyncio.new_event_loop()
        try:
            return loop.run_until_complete(coro)
        finally:
            loop.close()


def _extract_thought(log: str) -> str | None:
    """Extract the thought portion from a LangChain agent log string."""
    match = re.search(r"Thought:\s*(.*?)(?:\nAction:|\Z)", log, re.DOTALL)
    if match:
        return match.group(1).strip()
    # If no explicit "Thought:" prefix, take everything before "Action:"
    parts = log.split("Action:")
    if len(parts) > 1:
        thought = parts[0].strip()
        if thought:
            return thought
    return None


def _timestamp() -> str:
    return datetime.now(timezone.utc).isoformat()


class RetraceLangChainHandler:
    """LangChain callback handler that streams agent events to the Retrace TUI.

    Usage::

        from retrace.callbacks.langchain import RetraceLangChainHandler
        handler = RetraceLangChainHandler()
        agent.run("some query", callbacks=[handler])
    """

    def __init__(
        self,
        host: str | None = None,
        port: int | None = None,
    ) -> None:
        self.host = host or os.environ.get("RETRACE_HOST", "127.0.0.1")
        self.port = port or int(os.environ.get("RETRACE_PORT", "8765"))
        self.client = RetraceClient()
        self._ensure_connected()

    def _ensure_connected(self) -> None:
        """Attempt to connect to the Retrace server (non-blocking, non-fatal)."""
        try:
            _run_async(self.client.connect(self.host, self.port))
        except Exception:
            pass

    def _send(self, data: dict[str, Any]) -> None:
        """Send data to the server, silently ignoring failures."""
        try:
            _run_async(self.client.send_data(data))
        except Exception:
            pass

    def on_agent_action(self, action: Any, **kwargs: Any) -> Any:
        """Called when the agent selects an action to take.

        Sends both the extracted thought and the action to the Retrace TUI.
        """
        # Extract thought from the log
        log = getattr(action, "log", "")
        thought = _extract_thought(log)
        if thought:
            self._send({
                "type": "thought",
                "payload": {"timestamp": _timestamp(), "content": thought},
            })

        # Send the action
        tool = getattr(action, "tool", "unknown")
        tool_input = getattr(action, "tool_input", "")
        self._send({
            "type": "action",
            "payload": {
                "timestamp": _timestamp(),
                "tool": tool,
                "tool_input": str(tool_input),
            },
        })

    def on_tool_end(self, output: str, **kwargs: Any) -> Any:
        """Called when a tool finishes execution.

        Sends the observation (tool output) to the Retrace TUI.
        """
        self._send({
            "type": "observation",
            "payload": {"timestamp": _timestamp(), "content": output},
        })

    # Stubs for other callbacks to prevent AttributeError if LangChain calls them
    def on_llm_start(self, *args: Any, **kwargs: Any) -> None:
        pass

    def on_llm_end(self, *args: Any, **kwargs: Any) -> None:
        pass

    def on_llm_error(self, *args: Any, **kwargs: Any) -> None:
        pass

    def on_chain_start(self, *args: Any, **kwargs: Any) -> None:
        pass

    def on_chain_end(self, *args: Any, **kwargs: Any) -> None:
        pass

    def on_chain_error(self, *args: Any, **kwargs: Any) -> None:
        pass

    def on_tool_start(self, *args: Any, **kwargs: Any) -> None:
        pass

    def on_tool_error(self, *args: Any, **kwargs: Any) -> None:
        pass

    def on_agent_finish(self, *args: Any, **kwargs: Any) -> None:
        pass

    def on_text(self, *args: Any, **kwargs: Any) -> None:
        pass
