# retrace

The interactive TUI debugger for AI agents. Watch your agent think, act, and observe -- in real-time.

[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)

## The Problem

You run an AI agent. It calls tools, reasons over results, makes decisions -- and you see... a wall of text. Or nothing until it finishes. Debugging is guesswork.

**retrace** gives you a real-time TUI that shows every thought, action, and observation as it happens. Like browser DevTools, but for agents.

## Quick Start

```bash
pip install retrace-ai
```

**Terminal 1** -- Start the debugger:
```bash
retrace ui
```

**Terminal 2** -- Run your agent with retrace:
```python
from retrace.callbacks.langchain import RetraceLangChainHandler

handler = RetraceLangChainHandler()
agent.run("your query", callbacks=[handler])
```

That is it. Every thought, tool call, and observation streams to the TUI in real-time.

## What You See

The TUI displays a live feed of your agent execution:

- Thoughts -- the agent reasoning before each action
- Actions -- which tool was called and with what input
- Observations -- what the tool returned
- Status -- connection events, errors, system messages

Each event is color-coded and timestamped. Press `q` to quit, `c` to clear.

## Architecture

```
Your Agent  ----TCP/JSON---->  Retrace TUI
+ callback     thoughts,       (Textual app)
               actions,
               observations
```

- **client.py** -- singleton TCP client. Zero-crash: if server not running, agent continues normally
- **server.py** -- asyncio TCP server, receives newline-delimited JSON
- **tui.py** -- Textual app rendering styled event panels
- **callbacks/langchain.py** -- LangChain callback handler extracting thoughts, actions, observations

## Integrations

### LangChain

```python
from retrace.callbacks.langchain import RetraceLangChainHandler

handler = RetraceLangChainHandler()
agent.run("query", callbacks=[handler])
```

### Custom Agent (any framework)

```python
import asyncio
from retrace.client import RetraceClient

async def main():
    client = RetraceClient()
    await client.connect()

    await client.send_data({
        "type": "thought",
        "payload": {"content": "I should search for the answer"}
    })

    await client.send_data({
        "type": "action",
        "payload": {"tool": "search", "tool_input": "capital of France"}
    })

    await client.send_data({
        "type": "observation",
        "payload": {"content": "Paris is the capital of France"}
    })

    await client.disconnect()

asyncio.run(main())
```

## Configuration

| Env Var | Default | Description |
|---------|---------|-------------|
| `RETRACE_HOST` | `127.0.0.1` | Server bind address |
| `RETRACE_PORT` | `8765` | Server port |

Or pass directly:

```bash
retrace ui --host 0.0.0.0 --port 9000
```

```python
handler = RetraceLangChainHandler(host="0.0.0.0", port=9000)
```

## Design Decisions

- **Zero-crash guarantee** -- if the TUI is not running, the callback silently does nothing. Your agent never breaks because of debugging.
- **TCP, not HTTP** -- lower latency for real-time streaming. Newline-delimited JSON for simplicity.
- **Singleton client** -- one connection per process, shared across all callbacks.
- **Framework-agnostic** -- the core client speaks JSON over TCP. Framework callbacks are thin wrappers.

## Contributing

Issues and PRs welcome.

## License

MIT -- [Manish Rawal](https://github.com/manishrawal95)

---

If this saves you debugging time, consider giving it a star.
