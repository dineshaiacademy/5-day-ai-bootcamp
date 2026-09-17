"""
MCP CLIENT — reusable connection helper (Day 4 · Agents & MCP)

This is the piece a "host" application (our Streamlit app below, Claude
Desktop, Claude Code, ...) uses to talk to an MCP server. Notice what it
does NOT contain: no LLM, no API key, no chat prompt. A client's only job
is to speak the MCP protocol to exactly one server. *Deciding which tool to
call* is someone else's problem — see the agent loop in app.py.

Everything here is async because the real MCP protocol is: talking to a
subprocess over stdin/stdout (or a server over HTTP) is I/O, and the SDK
is built on `anyio`. app.py bridges this into Streamlit's synchronous
script model with `asyncio.run(...)`.
"""

from __future__ import annotations

import sys
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from mcp.types import CallToolResult, Tool as MCPTool

SERVER_SCRIPT = str(Path(__file__).resolve().parent.parent / "server" / "mcp_server.py")

# Tells the client HOW to start the server: run THIS Python interpreter
# (the same venv the Streamlit app is using) against THIS script, and talk
# to it over stdin/stdout. Nothing here is Streamlit-, Gemini-, or LM
# Studio-specific — a Claude Desktop config pointed at mcp_server.py would
# look almost identical, and the server file itself would not change at all.
SERVER_PARAMS = StdioServerParameters(command=sys.executable, args=[SERVER_SCRIPT])


@asynccontextmanager
async def connect_to_server():
    """
    Open one MCP session for the lifetime of the `async with` block.

    Under the hood, in order:
      1. `stdio_client` spawns `mcp_server.py` as a child process and wires
         up its stdin/stdout as a pair of anyio streams.
      2. `ClientSession` wraps those streams with the MCP message framing
         (JSON-RPC requests/responses/notifications).
      3. `session.initialize()` performs the MCP handshake — client and
         server exchange protocol versions and capabilities before any
         tool/resource/prompt call is allowed.

    The subprocess is terminated automatically when the `async with` block
    exits, even if an exception is raised inside it.
    """
    async with stdio_client(SERVER_PARAMS) as (read_stream, write_stream):
        async with ClientSession(read_stream, write_stream) as session:
            await session.initialize()
            yield session


def mcp_tool_to_openai_schema(tool: MCPTool) -> dict[str, Any]:
    """
    Translate one MCP tool description into the `tools=[...]` format
    OpenAI-compatible chat APIs expect (which is what both Gemini's and LM
    Studio's OpenAI-compatible endpoints speak — see app.py).

    The MCP server already generated `tool.input_schema` straight from the
    target function's type hints — this just re-wraps it, nothing is
    hand-typed here. That's the concrete payoff over Day 3's hardcoded
    TOOL_SCHEMAS list: add a new `@mcp.tool()` to the SERVER, and it shows
    up in the LLM's tool menu automatically, with zero client-side changes.
    """
    return {
        "type": "function",
        "function": {
            "name": tool.name,
            "description": tool.description or "",
            "parameters": tool.input_schema or {"type": "object", "properties": {}},
        },
    }


def tool_result_to_value(result: CallToolResult) -> Any:
    """
    Unwrap a CallToolResult into something plain and JSON-friendly.

    Prefer `structured_content` (a typed result matching the tool's output
    schema — e.g. list_notes() really does return a JSON array). Fall back
    to the human-readable `content` blocks (a list of TextContent, etc.)
    that every tool result carries for display purposes.
    """
    if result.structured_content is not None:
        return result.structured_content
    texts = [block.text for block in result.content if hasattr(block, "text")]
    return "\n".join(texts) if texts else None
