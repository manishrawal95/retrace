"""CLI entry point for the Retrace TUI debugger."""

from __future__ import annotations

import asyncio
from typing import Any

import typer

app = typer.Typer(help="Retrace — The interactive TUI debugger for AI agents.")


@app.command()
def ui(
    port: int = typer.Option(8765, help="Port for the TCP server to listen on."),
    host: str = typer.Option("127.0.0.1", help="Host for the TCP server to bind to."),
) -> None:
    """Launch the Retrace TUI and start the data server."""
    from retrace.server import RetraceServer
    from retrace.tui import RetraceTUI

    queue: asyncio.Queue[dict[str, Any]] = asyncio.Queue()
    server = RetraceServer(queue, host=host, port=port)
    tui = RetraceTUI(queue)

    async def run_server_alongside_tui() -> None:
        await server.start()
        try:
            await tui.run_async()
        finally:
            await server.stop()

    asyncio.run(run_server_alongside_tui())


if __name__ == "__main__":
    app()
