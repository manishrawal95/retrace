"""Tests for the Retrace TUI application."""

import asyncio
from typing import Any

import pytest

from retrace.tui import EventPanel, RetraceTUI


@pytest.mark.asyncio
async def test_tui_renders_events_from_queue():
    """Test that the TUI receives data from the queue and renders widgets."""
    queue: asyncio.Queue[dict[str, Any]] = asyncio.Queue()

    app = RetraceTUI(queue)

    async with app.run_test() as pilot:
        # Push events into the queue
        await queue.put({"type": "thought", "payload": {"content": "I need to search"}})
        await queue.put({"type": "action", "payload": {"tool": "search", "tool_input": "test query"}})
        await queue.put({"type": "observation", "payload": {"content": "Search result here"}})

        # Give the worker time to process
        await pilot.pause()
        await pilot.pause()
        await pilot.pause()

        # Check that EventPanel widgets were created
        panels = app.query(EventPanel)
        assert len(panels) >= 3

        # Verify each type is present
        classes = set()
        for panel in panels:
            for cls in ("event-thought", "event-action", "event-observation"):
                if panel.has_class(cls):
                    classes.add(cls)
        assert "event-thought" in classes
        assert "event-action" in classes
        assert "event-observation" in classes


@pytest.mark.asyncio
async def test_tui_clear_action():
    """Test that the clear action removes all events."""
    queue: asyncio.Queue[dict[str, Any]] = asyncio.Queue()
    app = RetraceTUI(queue)

    async with app.run_test() as pilot:
        await queue.put({"type": "thought", "payload": {"content": "test"}})
        await pilot.pause()
        await pilot.pause()

        panels = app.query(EventPanel)
        assert len(panels) >= 1

        await pilot.press("c")
        await pilot.pause()

        panels = app.query(EventPanel)
        assert len(panels) == 0
