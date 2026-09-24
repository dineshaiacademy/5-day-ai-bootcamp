"""Reusable MCP client for the Streamlit host application."""
from __future__ import annotations

import asyncio
import json
import os
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any

import httpx
from mcp import ClientSession
from mcp.client.streamable_http import streamable_http_client
from mcp.types import CallToolResult, Tool as MCPTool

PROJECT_DIR = Path(__file__).resolve().parents[1]
MCP_SERVER_HOST = os.getenv("MCP_SERVER_HOST", "127.0.0.1")
MCP_SERVER_PORT = int(os.getenv("MCP_SERVER_PORT", "8766"))
MCP_SERVER_URL = os.getenv("MCP_SERVER_URL", f"http://{MCP_SERVER_HOST}:{MCP_SERVER_PORT}/mcp")

class MCPServerUnavailable(RuntimeError):
    """Raised when the standalone MCP server cannot be reached."""
    def __init__(self, message: str | None = None) -> None:
        super().__init__(message or f"MCP server is unavailable at {MCP_SERVER_URL}.")

def field(obj: Any, *names: str, default: Any = None) -> Any:
    """Return the first attribute present on an object, across MCP SDK naming variants."""
    for name in names:
        if hasattr(obj, name):
            return getattr(obj, name)
    return default

def _friendly_unavailable(exc: BaseException) -> MCPServerUnavailable:
    leaves: list[BaseException] = []
    def collect(error: BaseException) -> None:
        if isinstance(error, BaseExceptionGroup):
            for child in error.exceptions:
                collect(child)
        else:
            leaves.append(error)
    collect(exc)
    connection = next((item for item in leaves if isinstance(item, (httpx.ConnectError, ConnectionError, OSError))), None)
    reason = str(connection or exc)
    return MCPServerUnavailable(
        f"Couldn't reach the MCP server at {MCP_SERVER_URL}. Start it with `python server/mcp_server.py` "
        f"from {PROJECT_DIR}. ({reason})"
    )

@asynccontextmanager
async def open_session():
    """Connect to the standalone server over streamable HTTP and initialize MCP."""
    try:
        async with streamable_http_client(MCP_SERVER_URL) as streams:
            # MCP releases yield either two streams or two streams plus a session-id callable.
            read_stream, write_stream = streams[0], streams[1]
            async with ClientSession(read_stream, write_stream) as session:
                await session.initialize()
                yield session
    except MCPServerUnavailable:
        raise
    except BaseException as exc:
        raise _friendly_unavailable(exc) from exc

def _tool_value(result: CallToolResult) -> Any:
    structured = field(result, "structured_content", "structuredContent")
    if structured is not None:
        return structured
    blocks = field(result, "content", default=[]) or []
    texts = [getattr(block, "text") for block in blocks if hasattr(block, "text")]
    return "\n".join(texts) if texts else None

def tool_result_to_value(result: CallToolResult) -> Any:
    """Unwrap structured or human-readable MCP tool content."""
    return _tool_value(result)

def tool_call_is_error(result: CallToolResult) -> bool:
    """Read the MCP error flag across snake_case and camelCase SDK versions."""
    return bool(field(result, "is_error", "isError", default=False))

async def list_tools() -> list[MCPTool]:
    """Discover the server's tools."""
    async with open_session() as session:
        return list((await session.list_tools()).tools)

async def call_tool(name: str, arguments: dict[str, Any] | None = None) -> dict[str, Any]:
    """Call one server tool and return status, display text, and structured content."""
    async with open_session() as session:
        result = await session.call_tool(name, arguments or {})
    structured = field(result, "structured_content", "structuredContent")
    value = _tool_value(result)
    text = value if isinstance(value, str) else json.dumps(value, ensure_ascii=False, default=str)
    return {"ok": not tool_call_is_error(result), "text": text, "structured": structured if structured is not None else value}

async def list_resources() -> list[Any]:
    """Discover static resources exposed by the server."""
    async with open_session() as session:
        return list((await session.list_resources()).resources)

async def read_resource(uri: str) -> str:
    """Read a resource URI and join its text contents."""
    async with open_session() as session:
        result = await session.read_resource(uri)
    contents = field(result, "contents", default=[]) or []
    return "\n".join(getattr(item, "text") for item in contents if hasattr(item, "text"))

async def list_prompts() -> list[Any]:
    """Discover reusable prompt templates exposed by the server."""
    async with open_session() as session:
        return list((await session.list_prompts()).prompts)

async def get_prompt(name: str, args: dict[str, Any] | None = None) -> str:
    """Render a server-owned prompt template into plain text."""
    async with open_session() as session:
        result = await session.get_prompt(name, args or {})
    messages = field(result, "messages", default=[]) or []
    parts = []
    for message in messages:
        content = getattr(message, "content", None)
        parts.append(getattr(content, "text", None) or str(content))
    return "\n".join(parts)

async def ping() -> bool:
    """Check that the server accepts an MCP handshake and can answer a small request."""
    try:
        async with open_session() as session:
            ping_method = getattr(session, "ping", None)
            if ping_method is not None:
                await ping_method()
            else:
                await session.list_tools()
        return True
    except Exception:
        return False

def mcp_tool_to_openai_schema(tool: MCPTool) -> dict[str, Any]:
    """Convert an MCP tool description into an OpenAI-compatible function schema."""
    schema = field(tool, "input_schema", "inputSchema") or {"type": "object", "properties": {}}
    return {"type": "function", "function": {"name": tool.name, "description": field(tool, "description", default="") or "", "parameters": schema}}

def run_sync(coro: Any) -> Any:
    """Run one coroutine with a fresh event loop, unwrapping MCP ExceptionGroups."""
    try:
        return asyncio.run(coro)
    except MCPServerUnavailable:
        raise
    except BaseException as exc:
        raise _friendly_unavailable(exc) from exc
