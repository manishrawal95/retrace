"""Textual TUI application for visualizing AI agent execution in real-time."""

from __future__ import annotations

import asyncio
from typing import Any

from rich.text import Text
from textual.app import App, ComposeResult
from textual.containers import VerticalScroll
from textual.widgets import Footer, Header, Static


STYLE_MAP: dict[str, tuple[str, str]] = {
    "thought": ("bold blue", "💭 Thought"),
    "action": ("bold yellow", "⚡ Action"),
    "observation": ("bold green", "👁 Observation"),
    "status": ("bold magenta", "ℹ Status"),
}


class EventPanel(Static):
    """A styled panel representing a single agent event."""

    def __init__(self, event_type: str, content: str) -> None:
        style_color, label = STYLE_MAP.get(event_type, ("bold white", event_type.title()))
        text = Text()
        text.append(f"[{label}]", style=style_color)
        text.append(f"\n{content}")
        super().__init__(text)
        self.add_class(f"event-{event_type}")


class RetraceTUI(App[None]):
    """The Retrace TUI application — renders agent events from an asyncio queue."""

    CSS = """
    EventPanel {
        margin: 0 1;
        padding: 1 2;
        border: round $accent;
        margin-bottom: 1;
    }
    EventPanel.event-thought {
        border: round dodgerblue;
    }
    EventPanel.event-action {
        border: round yellow;
    }
    EventPanel.event-observation {
        border: round green;
    }
    EventPanel.event-status {
        border: round magenta;
    }
    #event-log {
        height: 1fr;
    }
    """

    BINDINGS = [
        ("q", "quit", "Quit"),
        ("c", "clear", "Clear"),
    ]

    def __init__(self, queue: asyncio.Queue[dict[str, Any]], **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self.queue = queue

    def compose(self) -> ComposeResult:
        """Create the TUI layout."""
        yield Header(show_clock=True)
        yield VerticalScroll(id="event-log")
        yield Footer()

    def on_mount(self) -> None:
        """Start the background worker that reads from the queue."""
        self.title = "Retrace"
        self.sub_title = "AI Agent Debugger"
        self.run_worker(self._consume_queue(), exclusive=True)

    async def _consume_queue(self) -> None:
        """Continuously read events from the queue and render them."""
        while True:
            data = await self.queue.get()
            self.call_from_thread(self._render_event, data) if False else self._render_event(data)

    def _render_event(self, data: dict[str, Any]) -> None:
        """Create and mount a new EventPanel for the given event data."""
        event_type = data.get("type", "unknown")
        payload = data.get("payload", {})

        if event_type == "action":
            tool = payload.get("tool", "unknown")
            tool_input = payload.get("tool_input", "")
            content = f"Tool: {tool}\nInput: {tool_input}"
        else:
            content = payload.get("content", str(payload))

        panel = EventPanel(event_type, content)
        log = self.query_one("#event-log", VerticalScroll)
        log.mount(panel)
        panel.scroll_visible()

    def action_clear(self) -> None:
        """Clear all events from the log."""
        log = self.query_one("#event-log", VerticalScroll)
        log.remove_children()
