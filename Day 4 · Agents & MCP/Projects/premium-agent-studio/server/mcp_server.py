"""
MCP SERVER — "Premium Agent Studio" toolbox (Day 4 · Agents & MCP, Dinesh AI Academy)

Launch this on its own, in its own terminal, BEFORE running the agent (either
the CLI in agent/agent.py or the Streamlit app in app.py):

    python server/mcp_server.py

This is a real, standalone MCP server speaking **streamable HTTP** — a normal
network service with its own host/port and its own lifecycle. It does not
know or care who connects to it: the agent module, the Streamlit app, the
MCP Inspector, or a teammate's own client can all point at the same endpoint.
Stop it any time with Ctrl+C — every caller simply loses its connection
until you start it again.

Five tools + one resource, covering a spread of argument types an LLM has to
reason about (strings, ints, floats, optional defaults):

    Tool      get_current_time   — IANA timezone -> local date/time
              calculate          — safe arithmetic (AST-evaluated, no eval())
              get_weather        — REAL live weather, no API key required
              convert_units      — length / weight / temperature conversion
              add_task /
              list_tasks /
              complete_task      — a small shared, stateful task list
    Resource  task://all         — read-only snapshot of the task list

Every tool's input schema is generated automatically from its Python type
hints, and its description comes straight from its docstring — the agent
translates both, live, into Gemini function-calling declarations (see
agent/agent.py). Add a new @mcp.tool() here and it shows up for the agent
automatically, with zero changes anywhere else.
"""

from __future__ import annotations

import ast
import logging
import operator
import os
import sys
from datetime import datetime
from typing import Any
from zoneinfo import ZoneInfo

import httpx
from dotenv import load_dotenv
from mcp.server import MCPServer

load_dotenv()

logging.basicConfig(level=logging.INFO, format="%(asctime)s  %(levelname)-8s %(message)s", datefmt="%H:%M:%S")
logger = logging.getLogger("premium_agent_studio")

HOST = os.getenv("MCP_SERVER_HOST", "127.0.0.1")
PORT = int(os.getenv("MCP_SERVER_PORT", "8770"))
PATH = "/mcp"

mcp = MCPServer(
    "PremiumAgentStudioServer",
    instructions=(
        "A small everyday toolkit: tell the time anywhere in the world, do arithmetic, "
        "check the real current weather for a city, convert units, and manage a shared "
        "task list. Call a tool whenever the user's request matches what it does — never "
        "guess a time, weather condition, or task status yourself."
    ),
)


# ── Tool: time ───────────────────────────────────────────────────────────

@mcp.tool()
def get_current_time(timezone: str = "UTC") -> dict[str, str]:
    """Get the current date and time in an IANA timezone, e.g. 'UTC', 'Asia/Kolkata', 'America/New_York', 'Europe/London'."""
    try:
        tz = ZoneInfo(timezone)
    except Exception as e:
        raise ValueError(f"Unknown timezone '{timezone}' — use an IANA name like 'Asia/Kolkata' or 'UTC'.") from e
    now = datetime.now(tz)
    logger.info("get_current_time(timezone=%r) -> %s", timezone, now.isoformat())
    return {
        "timezone": timezone,
        "iso": now.isoformat(),
        "formatted": now.strftime("%A, %d %B %Y — %H:%M:%S %Z"),
    }


# ── Tool: calculator (AST-evaluated — never uses eval()) ───────────────────

_SAFE_OPS = {
    ast.Add: operator.add, ast.Sub: operator.sub, ast.Mult: operator.mul,
    ast.Div: operator.truediv, ast.FloorDiv: operator.floordiv,
    ast.Mod: operator.mod, ast.Pow: operator.pow,
    ast.USub: operator.neg, ast.UAdd: operator.pos,
}


def _safe_eval(node: ast.AST) -> float:
    if isinstance(node, ast.Constant) and isinstance(node.value, (int, float)) and not isinstance(node.value, bool):
        return node.value
    if isinstance(node, ast.BinOp) and type(node.op) in _SAFE_OPS:
        return _SAFE_OPS[type(node.op)](_safe_eval(node.left), _safe_eval(node.right))
    if isinstance(node, ast.UnaryOp) and type(node.op) in _SAFE_OPS:
        return _SAFE_OPS[type(node.op)](_safe_eval(node.operand))
    raise ValueError("Only numbers, + - * / // % **, unary minus, and parentheses are allowed.")


@mcp.tool()
def calculate(expression: str) -> dict[str, Any]:
    """Safely evaluate a plain arithmetic expression, e.g. '480 * 0.23'. Supports + - * / // % ** and parentheses."""
    try:
        tree = ast.parse(expression, mode="eval")
        result = _safe_eval(tree.body)
    except Exception as e:
        raise ValueError(f"Could not evaluate '{expression}': {e}") from e
    logger.info("calculate(%r) -> %s", expression, result)
    return {"expression": expression, "result": result}


# ── Tool: live weather (Open-Meteo — free, no API key) ──────────────────────

_WEATHER_CODES = {
    0: "Clear sky", 1: "Mainly clear", 2: "Partly cloudy", 3: "Overcast",
    45: "Fog", 48: "Depositing rime fog",
    51: "Light drizzle", 53: "Moderate drizzle", 55: "Dense drizzle",
    61: "Slight rain", 63: "Moderate rain", 65: "Heavy rain",
    71: "Slight snow", 73: "Moderate snow", 75: "Heavy snow",
    80: "Rain showers", 81: "Moderate rain showers", 82: "Violent rain showers",
    95: "Thunderstorm", 96: "Thunderstorm with hail", 99: "Thunderstorm with heavy hail",
}


@mcp.tool()
async def get_weather(city: str) -> dict[str, Any]:
    """Get the REAL current weather for a city anywhere in the world. No API key needed — uses the free Open-Meteo public API."""
    async with httpx.AsyncClient(timeout=10) as http:
        geo = await http.get(
            "https://geocoding-api.open-meteo.com/v1/search",
            params={"name": city, "count": 1, "language": "en", "format": "json"},
        )
        geo.raise_for_status()
        results = geo.json().get("results") or []
        if not results:
            raise ValueError(f"Could not find a location named '{city}'.")
        place = results[0]

        wx = await http.get(
            "https://api.open-meteo.com/v1/forecast",
            params={
                "latitude": place["latitude"],
                "longitude": place["longitude"],
                "current": "temperature_2m,apparent_temperature,relative_humidity_2m,wind_speed_10m,weather_code",
                "timezone": "auto",
            },
        )
        wx.raise_for_status()
        current = wx.json()["current"]

    result = {
        "city": city,
        "resolved_location": ", ".join(filter(None, [place.get("name"), place.get("admin1"), place.get("country")])),
        "temperature_c": current["temperature_2m"],
        "feels_like_c": current["apparent_temperature"],
        "humidity_pct": current["relative_humidity_2m"],
        "wind_kph": current["wind_speed_10m"],
        "condition": _WEATHER_CODES.get(current["weather_code"], "Unknown"),
    }
    logger.info("get_weather(city=%r) -> %s, %s°C, %s", city, result["resolved_location"], result["temperature_c"], result["condition"])
    return result


# ── Tool: unit conversion ───────────────────────────────────────────────────

_LENGTH_TO_METERS = {"m": 1.0, "km": 1000.0, "cm": 0.01, "mm": 0.001, "mi": 1609.344, "ft": 0.3048, "in": 0.0254, "yd": 0.9144}
_WEIGHT_TO_KG = {"kg": 1.0, "g": 0.001, "mg": 0.000001, "lb": 0.45359237, "oz": 0.028349523125}
_TEMPERATURE_UNITS = {"c", "f", "k"}


def _convert_temperature(value: float, from_unit: str, to_unit: str) -> float:
    celsius = {"c": value, "f": (value - 32) * 5 / 9, "k": value - 273.15}[from_unit]
    return {"c": celsius, "f": celsius * 9 / 5 + 32, "k": celsius + 273.15}[to_unit]


@mcp.tool()
def convert_units(value: float, from_unit: str, to_unit: str) -> dict[str, Any]:
    """Convert a number between units. Length: m, km, cm, mm, mi, ft, in, yd. Weight: kg, g, mg, lb, oz. Temperature: c, f, k."""
    f, t = from_unit.strip().lower(), to_unit.strip().lower()
    if f in _TEMPERATURE_UNITS and t in _TEMPERATURE_UNITS:
        result = _convert_temperature(value, f, t)
    elif f in _LENGTH_TO_METERS and t in _LENGTH_TO_METERS:
        result = value * _LENGTH_TO_METERS[f] / _LENGTH_TO_METERS[t]
    elif f in _WEIGHT_TO_KG and t in _WEIGHT_TO_KG:
        result = value * _WEIGHT_TO_KG[f] / _WEIGHT_TO_KG[t]
    else:
        raise ValueError(
            f"Don't know how to convert '{from_unit}' to '{to_unit}'. "
            "Supported — length: m, km, cm, mm, mi, ft, in, yd · weight: kg, g, mg, lb, oz · temperature: c, f, k."
        )
    result = round(result, 4)
    logger.info("convert_units(%s %s -> %s) -> %s", value, from_unit, to_unit, result)
    return {"value": value, "from_unit": from_unit, "to_unit": to_unit, "result": result}


# ── Tools + resource: a small shared, stateful task list ───────────────────
# In-memory only — resets every time this process restarts.

_tasks: list[dict] = []
_VALID_PRIORITIES = {"low", "normal", "high"}


@mcp.tool()
def add_task(title: str, priority: str = "normal") -> str:
    """Add a new task to the shared task list. priority is 'low', 'normal', or 'high'."""
    priority = priority.lower() if priority.lower() in _VALID_PRIORITIES else "normal"
    _tasks.append({"title": title, "priority": priority, "done": False})
    logger.info("add_task(%r, priority=%r)", title, priority)
    return f"Added task '{title}' (priority: {priority})."


@mcp.tool()
def list_tasks(status: str = "all") -> list[dict[str, Any]]:
    """List tasks on the shared task list. status is 'all', 'open', or 'done'."""
    status = status.lower()
    if status == "open":
        return [t for t in _tasks if not t["done"]]
    if status == "done":
        return [t for t in _tasks if t["done"]]
    return list(_tasks)


@mcp.tool()
def complete_task(title: str) -> str:
    """Mark a task as done by its exact title. Safe to call even if the title doesn't exist."""
    for t in _tasks:
        if t["title"] == title:
            t["done"] = True
            logger.info("complete_task(%r)", title)
            return f"Marked '{title}' as done."
    return f"No task found with title '{title}'."


@mcp.resource("task://all")
def get_all_tasks() -> str:
    """A read-only snapshot of every task, open and done, no LLM decision required to read it."""
    if not _tasks:
        return "No tasks yet."
    lines = [f"[{'x' if t['done'] else ' '}] ({t['priority']}) {t['title']}" for t in sorted(_tasks, key=lambda x: x["done"])]
    return "\n".join(lines)


if __name__ == "__main__":
    print("=" * 72)
    print("  PREMIUM AGENT STUDIO — MCP tool server, its own standalone process")
    print("=" * 72)
    print(f"  Transport   : streamable-http")
    print(f"  Endpoint    : http://{HOST}:{PORT}{PATH}")
    print(f"  Tools       : get_current_time, calculate, get_weather, convert_units,")
    print(f"                add_task, list_tasks, complete_task")
    print(f"  Resource    : task://all")
    print("  This process has no idea what agent connects to it — the CLI agent in")
    print("  agent/agent.py, the Streamlit app in app.py, or the MCP Inspector can")
    print("  all point at the endpoint above. Press Ctrl+C to stop it.")
    print("=" * 72)
    sys.stdout.flush()
    mcp.run(transport="streamable-http", host=HOST, port=PORT, streamable_http_path=PATH)
