"""
MCP CLIENT — reusable connection helper (Day 4 · Agents & MCP)

This is the piece a "host" application (our Streamlit app in app.py, Claude
Desktop, Claude Code, ...) uses to talk to the MCP server. Notice what it
does NOT contain: no LLM, no API key, no chat prompt. A client's only job
is to speak the MCP protocol to exactly one server. *Deciding which tool to
call* is someone else's problem — see the agent loop in app.py.

The key difference from a stdio client: this one does not know how to
START the server — it only knows its URL. There is no `StdioServerParameters`
here, no subprocess, no import of anything from `server/`. The server is
somebody else's problem too: it's already running (or it isn't, in which
case every call below fails with a clear connection error), on whatever
machine `MCP_SERVER_URL` points at. That's the whole demo — client and
server are two independent programs that just happen to agree on a URL
and a protocol.
"""

from __future__ import annotations

import os
import socket
from contextlib import asynccontextmanager
from typing import Any
from urllib.parse import urlparse

from mcp import ClientSession
from mcp.client.streamable_http import streamable_http_client
from mcp.types import CallToolResult, Tool as MCPTool

MCP_SERVER_HOST = os.getenv("MCP_SERVER_HOST", "127.0.0.1")
MCP_SERVER_PORT = int(os.getenv("MCP_SERVER_PORT", "8765"))
MCP_SERVER_URL = os.getenv("MCP_SERVER_URL", f"http://{MCP_SERVER_HOST}:{MCP_SERVER_PORT}/mcp")


def field(obj: Any, *names: str, default: Any = None) -> Any:
    """
    Return the first attribute present on `obj` out of `names`.

    A handful of fields on MCP's response models have changed casing
    between `mcp` package releases (`resource_templates`/`resourceTemplates`,
    `is_error`/`isError`, `input_schema`/`inputSchema`,
    `structured_content`/`structuredContent`) — including between two
    versions we've hit in this exact project. Reading through this instead
    of a hardcoded `obj.the_field` keeps the app working across those
    versions without pinning one exact release in requirements.txt.
    """
    for name in names:
        if hasattr(obj, name):
            return getattr(obj, name)
    return default


def is_server_reachable(timeout: float = 0.6) -> bool:
    """
    A fast, MCP-agnostic liveness check: can we even open a TCP socket to the
    server's host/port? Used by app.py to render a green/red status badge
    WITHOUT paying for a full MCP handshake on every Streamlit rerun.
    """
    parsed = urlparse(MCP_SERVER_URL)
    host, port = parsed.hostname or "127.0.0.1", parsed.port or 80
    try:
        with socket.create_connection((host, port), timeout=timeout):
            return True
    except OSError:
        return False


@asynccontextmanager
async def connect_to_server():
    """
    Open one MCP session for the lifetime of the `async with` block.

    Under the hood, in order:
      1. `streamable_http_client` opens an HTTP connection to MCP_SERVER_URL
         (an already-running, independently-launched process — see
         server/mcp_server.py) and wires it up as a pair of anyio streams.
      2. `ClientSession` wraps those streams with MCP's message framing
         (JSON-RPC requests/responses/notifications).
      3. `session.initialize()` performs the MCP handshake — client and
         server exchange protocol versions and capabilities before any
         tool/resource/prompt call is allowed.

    If the server isn't running, this raises a connection error immediately
    — there is no subprocess to spawn as a fallback, unlike the stdio
    variant of this same helper (see ../../mcp-notes-demo/client/mcp_client.py).

    Different releases of the `mcp` package yield a different number of
    values here — some give `(read_stream, write_stream)`, others add a
    third `get_session_id` callable. Indexing instead of unpacking keeps
    this working across both without pinning an exact version.
    """
    async with streamable_http_client(MCP_SERVER_URL) as streams:
        read_stream, write_stream = streams[0], streams[1]
        async with ClientSession(read_stream, write_stream) as session:
            await session.initialize()
            yield session


def mcp_tool_to_openai_schema(tool: MCPTool) -> dict[str, Any]:
    """
    Translate one MCP tool description into the `tools=[...]` format
    OpenAI-compatible chat APIs expect (which is what both Gemini's and LM
    Studio's OpenAI-compatible endpoints speak — see app.py).

    The MCP server already generated the tool's input schema straight from
    the target function's type hints — this just re-wraps it, nothing is
    hand-typed here. Add a new `@mcp.tool()` on the SERVER and it shows up
    in the LLM's tool menu automatically, with zero client-side changes.
    """
    schema = field(tool, "input_schema", "inputSchema")
    return {
        "type": "function",
        "function": {
            "name": tool.name,
            "description": tool.description or "",
            "parameters": schema or {"type": "object", "properties": {}},
        },
    }


def tool_result_to_value(result: CallToolResult) -> Any:
    """
    Unwrap a CallToolResult into something plain and JSON-friendly.

    Prefer the structured-content field (a typed result matching the
    tool's output schema — e.g. get_weather() really does return a JSON
    object). Fall back to the human-readable `content` blocks (TextContent,
    etc.) that every tool result carries for display purposes.
    """
    structured = field(result, "structured_content", "structuredContent")
    if structured is not None:
        return structured
    texts = [block.text for block in result.content if hasattr(block, "text")]
    return "\n".join(texts) if texts else None


def tool_call_is_error(result: CallToolResult) -> bool:
    """Same version-skew issue as `field()` above — `is_error` vs `isError`."""
    return bool(field(result, "is_error", "isError", default=False))
