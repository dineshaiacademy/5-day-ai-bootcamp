"""
MCP CLIENT — reusable connection helper (Day 4 · Agents & MCP)

This is the piece a "host" (the independent agent in agent/agent.py, and
through it the Streamlit app or the CLI) uses to talk to the MCP server.
Notice what it does NOT contain: no LLM, no API key, no chat prompt, no
knowledge of Gemini. A client's only job is to speak the MCP protocol to
exactly one server — *deciding* which tool to call is the agent's problem.

This client does not know how to START the server, either — it only knows
its URL. The server is somebody else's problem: it's already running (or it
isn't, in which case every call below fails with a clear connection error),
wherever MCP_SERVER_URL points. Client and server are two independent
programs that just happen to agree on a URL and a protocol.
"""

from __future__ import annotations

import os
import socket
from contextlib import asynccontextmanager
from typing import Any
from urllib.parse import urlparse

from mcp import ClientSession
from mcp.client.streamable_http import streamable_http_client
from mcp.types import CallToolResult

MCP_SERVER_HOST = os.getenv("MCP_SERVER_HOST", "127.0.0.1")
MCP_SERVER_PORT = int(os.getenv("MCP_SERVER_PORT", "8770"))
MCP_SERVER_URL = os.getenv("MCP_SERVER_URL", f"http://{MCP_SERVER_HOST}:{MCP_SERVER_PORT}/mcp")


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
         tool/resource call is allowed.

    If the server isn't running, this raises a connection error immediately.
    """
    async with streamable_http_client(MCP_SERVER_URL) as (read_stream, write_stream):
        async with ClientSession(read_stream, write_stream) as session:
            await session.initialize()
            yield session


def tool_result_to_value(result: CallToolResult) -> Any:
    """
    Unwrap a CallToolResult into something plain and JSON-friendly.

    Prefer `structured_content` (a typed result matching the tool's output
    schema — e.g. get_weather() really does return a JSON object). Fall
    back to the human-readable `content` blocks (TextContent, etc.) that
    every tool result carries for display purposes.
    """
    if result.structured_content is not None:
        return result.structured_content
    texts = [block.text for block in result.content if hasattr(block, "text")]
    return "\n".join(texts) if texts else None
