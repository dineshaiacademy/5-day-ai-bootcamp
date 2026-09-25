# Day 4 Labs - Build Prompt (MCP Server + Gemini Agent App)

**How to use**
1. Open a new, empty folder in VS Code (any folder - for example `mcp-expense-lab`).
2. Open GitHub Copilot Chat and switch it to **Agent mode**.
3. Copy everything inside the fenced block below and paste it into Copilot Chat.
4. Copilot creates every file directly in the folder you opened (no extra wrapper folder), installs the packages and
   runs its own checks. No Gemini key is needed for the build - you add it afterwards.

Gemini is the only LLM provider. The code inside this prompt was tested end-to-end (a fresh Python install, the MCP
tools, the Streamlit UI in a browser, and 20 live Gemini questions including rate-limit recovery).

````text
ROLE
You are a senior Python engineer setting up a ready-made teaching lab for "Dinesh AI Academy - Day 4: Agents & MCP".
Your job is to CREATE the project files listed below exactly as written, install the dependencies, and verify the
result. The code has already been written and tested against the live Gemini API and a clean Python install. Do NOT
redesign, rename, "improve", reformat, shorten or add to it.

WHAT THIS BUILDS
A standalone MCP server (7 expense tools, 1 resource, 1 prompt) plus a Streamlit app whose MCP client lets Google
Gemini choose and call those tools. Gemini is the ONLY LLM provider - there is no LM Studio and no provider switch.
Retry with model rotation is built in, so a rate limit or a briefly overloaded model does not break a chat answer.

WHERE TO CREATE THE FILES (very important)
- Create every file directly in the CURRENT WORKSPACE ROOT - the folder that is open right now.
- Do NOT create a new project or wrapper folder (no "mcp-expense-lab/", no dated folder, nothing nested such as
  "Day 4/Labs/..."). The workspace root IS the project root.
- The only folders you may create are the four that the file list needs: .streamlit/  server/  client/  src/
- Do not read, modify or delete anything else that already exists in the workspace.

HOW TO WORK
1. Create the files in the FILES section. Each file starts with a line "<<<FILE: path>>>" and ends with
   "<<<END FILE: path>>>" - those two marker lines are NOT part of the file. Copy everything between them character for
   character. Save as UTF-8 without BOM and keep every emoji and symbol. Files marked EMPTY must be created empty
   (the "# EMPTY file." line is only a note for you, do not write it into the file).
2. `.env` and `.env.example` must both be created, with the identical content shown. Leave GEMINI_API_KEY empty -
   never invent, guess or hard-code a key. If a `.env` already exists in the workspace, do not overwrite it.
3. Install dependencies: `pip install -r requirements.txt`. Do not create a virtual environment unless one is already
   in use. (requirements.txt forces mcp>=2.0, so an older mcp already on the machine is upgraded.)
4. Run every check in the VERIFICATION section. If anything fails, fix the cause, re-run it, and continue - do not
   stop and just report the error.
5. Do NOT paste file contents into the chat. Finish with the short FINAL REPORT described at the end.

RULES
- No LM Studio, no other LLM provider, no extra features, and no files beyond the list below.
- Never print or log non-ASCII characters (emoji, arrows, currency symbols) with print() or logging in any command
  you run - Windows consoles can crash on them. They are fine inside the Streamlit UI strings in app.py.
- Do not use eval or exec, and do not put any secret in any file.

FILES

<<<FILE: .streamlit/config.toml>>>
# Dinesh AI Academy theme — deep indigo/violet brand color on a clean,
# premium neutral canvas, with a signature dark sidebar rail.
# https://docs.streamlit.io/develop/api-reference/configuration/config.toml

[theme.light]
primaryColor = "#5B4FE8"
backgroundColor = "#FFFFFF"
secondaryBackgroundColor = "#F5F4FC"
textColor = "#1C1B29"
linkColor = "#5B4FE8"
borderColor = "#E5E2F5"
codeBackgroundColor = "#F5F4FC"
codeTextColor = "#1C1B29"

redColor = "#DC2626"
orangeColor = "#D97706"
yellowColor = "#CA8A04"
greenColor = "#16A34A"
blueColor = "#2563EB"
violetColor = "#5B4FE8"
grayColor = "#6B7280"

chartCategoricalColors = ["#5B4FE8", "#16A34A", "#D97706", "#2563EB", "#DC2626", "#8B7FFF", "#6B7280"]

[theme.dark]
primaryColor = "#8B7FFF"
backgroundColor = "#100F1C"
secondaryBackgroundColor = "#1A1830"
textColor = "#EDEBFA"
linkColor = "#8B7FFF"
borderColor = "#2E2B57"
codeBackgroundColor = "#1A1830"
codeTextColor = "#EDEBFA"

redColor = "#F87171"
orangeColor = "#FBBF24"
yellowColor = "#FACC15"
greenColor = "#4ADE80"
blueColor = "#60A5FA"
violetColor = "#8B7FFF"
grayColor = "#9CA3AF"

chartCategoricalColors = ["#8B7FFF", "#4ADE80", "#FBBF24", "#60A5FA", "#F87171", "#5B4FE8", "#9CA3AF"]

# A single dark, branded rail for the sidebar in both modes — the
# "premium app" look of a fixed navigation column next to a light workspace.
[theme.light.sidebar]
backgroundColor = "#171532"
secondaryBackgroundColor = "#211F42"
textColor = "#E9E7F7"
borderColor = "#2E2B57"
primaryColor = "#8B7FFF"
linkColor = "#B3ABFF"
codeBackgroundColor = "#211F42"
codeTextColor = "#E9E7F7"

[theme.dark.sidebar]
backgroundColor = "#0B0A16"
secondaryBackgroundColor = "#171532"
textColor = "#E9E7F7"
borderColor = "#2E2B57"
primaryColor = "#8B7FFF"
linkColor = "#B3ABFF"
codeBackgroundColor = "#171532"
codeTextColor = "#E9E7F7"

[theme]
font = "Inter:https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap"
headingFont = "Inter:https://fonts.googleapis.com/css2?family=Inter:wght@600;700&display=swap"
codeFont = "'JetBrains Mono':https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;500&display=swap"

baseFontSize = 15
baseFontWeight = 400
codeFontSize = "0.85rem"
headingFontSizes = ["30px", "22px", "18px", "16px", "14px", "13px"]
headingFontWeights = [700, 600, 600, 600, 500, 500]
linkUnderline = false

baseRadius = "10px"
buttonRadius = "10px"
showWidgetBorder = true
showSidebarBorder = true
<<<END FILE: .streamlit/config.toml>>>

<<<FILE: requirements.txt>>>
streamlit>=1.50
openai>=2.0
python-dotenv
mcp>=2.0,<3
httpx
pandas
tzdata
<<<END FILE: requirements.txt>>>

<<<FILE: .env>>>
# Get a Gemini API key at https://aistudio.google.com/apikey and paste it after the = sign
GEMINI_API_KEY=

# MCP server (the server and the app must agree on these)
MCP_SERVER_HOST=127.0.0.1
MCP_SERVER_PORT=8766
<<<END FILE: .env>>>

<<<FILE: .env.example>>>
# Get a Gemini API key at https://aistudio.google.com/apikey and paste it after the = sign
GEMINI_API_KEY=

# MCP server (the server and the app must agree on these)
MCP_SERVER_HOST=127.0.0.1
MCP_SERVER_PORT=8766
<<<END FILE: .env.example>>>

<<<FILE: .gitignore>>>
.env
__pycache__/
.venv/
<<<END FILE: .gitignore>>>

<<<FILE: start_server.bat>>>
@echo off
cd /d "%~dp0"
if exist ".venv\Scriptsctivate.bat" call ".venv\Scriptsctivate.bat"
python server\mcp_server.py
pause
<<<END FILE: start_server.bat>>>

<<<FILE: start_server.sh>>>
#!/usr/bin/env bash
cd "$(dirname "$0")"
[ -f ".venv/bin/activate" ] && source ".venv/bin/activate"
python server/mcp_server.py
<<<END FILE: start_server.sh>>>

<<<FILE: README.md>>>
# MCP Expense Lab

A standalone MCP server plus a Streamlit app where Google Gemini manages an in-memory Smart Expense Tracker by calling MCP tools.

## Architecture

```text
Human ──► HOST: Streamlit app.py ──► Gemini
              │                        │ chooses a tool
              ▼                        ▼
        MCP CLIENT ── streamable HTTP ──► MCP SERVER
       client/mcp_client.py               server/mcp_server.py
              ◄──────── tool result ─────────┘
```

| Capability | Name | Purpose |
|---|---|---|
| Tool | `add_expense` | Add one validated INR expense |
| Tool | `list_expenses` | List newest expenses, optionally by category / month |
| Tool | `delete_expense` | Safely delete an expense by id |
| Tool | `get_spending_summary` | Total, count, average, category breakdown (optional category / month) |
| Tool | `convert_currency` | Convert with fixed static demo rates |
| Tool | `calculate` | Safe arithmetic (no `eval`) |
| Tool | `get_current_date` | Date, weekday, ISO timestamp |
| Resource | `expenses://all` | JSON snapshot of the in-memory expense book |
| Prompt | `monthly_report` | Asks the model to build a monthly report with the tools |

## Quickstart

1. Install: `pip install -r requirements.txt`
2. Open `.env` and paste your Gemini key after `GEMINI_API_KEY=` (get one at https://aistudio.google.com/apikey). No `.env`? Copy `.env.example` to `.env`.
3. Terminal 1 - start the MCP server: `start_server.bat` (Windows) or `bash start_server.sh` (Mac/Linux). Leave it running.
4. Terminal 2 - start the app from the same folder: `streamlit run app.py`, then open http://localhost:8501

## Try these prompts

- How much did I spend on travel?
- Add 450 rupees for lunch today
- Convert my total spending to USD
- Delete expense 2 and show the new summary
- Give me a monthly report for September 2026
- What's the weather like today? (no tool exists for this - the agent should say so plainly)

## Reliability built in

If Gemini is rate-limited or briefly overloaded, the app automatically tries the other Gemini models in the Model list, then waits and retries, and shows a "retrying" notice instead of failing. The caption under each answer shows which model actually answered.

## Exercise: add your own tool

Add `set_budget(category, amount)` / `check_budget(category)` to `server/mcp_server.py` with full type hints, a one-line docstring and the `@mcp.tool()` decorator. Restart the server - the Tool Explorer tab discovers it automatically and the agent can use it with no client changes.

## Troubleshooting

- **"No GEMINI_API_KEY found":** paste the key into `.env`, save, refresh the page.
- **"API key was rejected":** re-copy the key from Google AI Studio (no spaces or quotes), save `.env`, refresh.
- **MCP server offline in the sidebar:** start `python server/mcp_server.py` in its own terminal first.
- **Port already in use:** change `MCP_SERVER_PORT` in `.env`, then restart both the server and the app.
- **`ImportError: MCPServer`:** you have an old `mcp` package - run `pip install -U "mcp>=2.0"`.
- **Answers are slow:** Gemini free-tier quotas are small; a paid key removes most waiting.

The expense book is in memory on purpose: restarting the MCP server restores the five sample records.
<<<END FILE: README.md>>>

<<<FILE: server/__init__.py>>>
# EMPTY file.
<<<END FILE: server/__init__.py>>>

<<<FILE: server/mcp_server.py>>>
"""Standalone Smart Expense Tracker MCP server over streamable HTTP."""
from __future__ import annotations

import ast
import json
import logging
import operator
import os
import re
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

PROJECT_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_DIR))
from src.env_setup import ensure_env_file  # noqa: E402

ensure_env_file()
from dotenv import load_dotenv  # noqa: E402

load_dotenv(PROJECT_DIR / ".env")
try:
    from mcp.server import MCPServer  # noqa: E402  (mcp >= 2.0; on mcp 1.x this class was called FastMCP)
except ImportError:
    sys.exit('This lab needs mcp 2.x. Fix it with:  pip install -U "mcp>=2.0"')

logging.basicConfig(level=logging.INFO, format="%(asctime)s  %(levelname)-8s %(message)s", datefmt="%H:%M:%S")
logger = logging.getLogger("mcp_expense_lab")
HOST = os.getenv("MCP_SERVER_HOST", "127.0.0.1")
PORT = int(os.getenv("MCP_SERVER_PORT", "8766"))
PATH = "/mcp"

mcp = MCPServer("ExpenseLabServer", instructions=(
    "You manage an in-memory Smart Expense Tracker. Use the expense tools for every "
    "calculation or lookup instead of guessing numbers. Amounts default to INR. "
    "Changes reset when this demo server restarts."
))

ALLOWED_CATEGORIES = ("food", "travel", "shopping", "bills", "entertainment", "health", "other")
CURRENCIES = ("INR", "USD", "EUR", "GBP", "AED", "JPY")
USD_RATES = {"USD": 1.0, "INR": 83.0, "EUR": 0.92, "GBP": 0.79, "AED": 3.67, "JPY": 150.0}
EXPENSES: list[dict[str, Any]] = [
    {"id": 1, "date": "2026-09-18", "category": "food", "description": "Team lunch", "amount": 850.0, "currency": "INR"},
    {"id": 2, "date": "2026-09-19", "category": "travel", "description": "Metro recharge", "amount": 600.0, "currency": "INR"},
    {"id": 3, "date": "2026-09-20", "category": "shopping", "description": "Household supplies", "amount": 1250.0, "currency": "INR"},
    {"id": 4, "date": "2026-09-21", "category": "bills", "description": "Internet bill", "amount": 999.0, "currency": "INR"},
    {"id": 5, "date": "2026-09-22", "category": "entertainment", "description": "Cinema tickets", "amount": 720.0, "currency": "INR"},
]


def _record_call(name: str, **details: Any) -> None:
    logger.info("tool=%s args=%s", name, details)


def _error(message: str) -> dict[str, str]:
    return {"error": message}


def _category(value: str) -> str | None:
    normalized = str(value).strip().lower()
    return normalized if normalized in ALLOWED_CATEGORIES else None


def _month(value: str | None) -> str | None:
    """Return a clean YYYY-MM string, None when not given, or raise ValueError when malformed."""
    cleaned = (value or "").strip()
    if not cleaned:
        return None
    if not re.fullmatch(r"\d{4}-(0[1-9]|1[0-2])", cleaned):
        raise ValueError("Month must use YYYY-MM format, for example 2026-09.")
    return cleaned


def _select(category: str, month: str | None) -> list[dict[str, Any]]:
    return [item for item in EXPENSES
            if (category == "all" or item["category"] == category) and (not month or item["date"].startswith(month))]


@mcp.tool()
def add_expense(amount: float, category: str, description: str, date: str | None = None) -> dict[str, Any]:
    """Add ONE expense in INR (positive amount, allowed category, description, optional YYYY-MM-DD date); call once per expense."""
    _record_call("add_expense", amount=amount, category=category, description=description, date=date)
    try:
        amount = float(amount)
    except (TypeError, ValueError):
        return _error("Amount must be a number greater than zero.")
    if amount <= 0:
        return _error("Amount must be greater than zero.")
    normalized_category = _category(category)
    if normalized_category is None:
        return _error(f"Category must be one of: {', '.join(ALLOWED_CATEGORIES)}.")
    expense_date = date or datetime.now().date().isoformat()
    try:
        datetime.strptime(expense_date, "%Y-%m-%d")
    except (TypeError, ValueError):
        return _error("Date must use YYYY-MM-DD format.")
    record = {"id": max((item["id"] for item in EXPENSES), default=0) + 1, "date": expense_date,
              "category": normalized_category, "description": str(description).strip(),
              "amount": round(amount, 2), "currency": "INR"}
    EXPENSES.append(record)
    return record


@mcp.tool()
def list_expenses(category: str = "all", limit: int = 20, month: str | None = None) -> list[dict[str, Any]] | dict[str, str]:
    """List expenses newest first, optionally filtered by category and by month (YYYY-MM), limited to a number of records."""
    _record_call("list_expenses", category=category, limit=limit, month=month)
    normalized = str(category).strip().lower()
    if normalized != "all" and normalized not in ALLOWED_CATEGORIES:
        return _error(f"Category must be 'all' or one of: {', '.join(ALLOWED_CATEGORIES)}.")
    try:
        count = max(1, min(int(limit), 100))
    except (TypeError, ValueError):
        return _error("Limit must be a positive integer.")
    try:
        wanted_month = _month(month)
    except ValueError as exc:
        return _error(str(exc))
    matches = _select(normalized, wanted_month)
    return sorted(matches, key=lambda item: (item["date"], item["id"]), reverse=True)[:count]


@mcp.tool()
def delete_expense(expense_id: int) -> str:
    """Delete an expense by id safely and return a clear status message when it is missing."""
    _record_call("delete_expense", expense_id=expense_id)
    try:
        target = int(expense_id)
    except (TypeError, ValueError):
        return "No expense found with id supplied; expense id must be an integer."
    for index, expense in enumerate(EXPENSES):
        if expense["id"] == target:
            removed = EXPENSES.pop(index)
            return f"Deleted expense {target}: {removed['description']} (INR {removed['amount']:.2f})."
    return f"No expense found with id {target}; nothing was deleted."


@mcp.tool()
def get_spending_summary(category: str = "all", month: str | None = None) -> dict[str, Any]:
    """Get total, count, average and per-category spending; use this for ANY total, optionally for one category and/or one month (YYYY-MM)."""
    _record_call("get_spending_summary", category=category, month=month)
    normalized = str(category).strip().lower()
    if normalized != "all" and normalized not in ALLOWED_CATEGORIES:
        return _error(f"Category must be 'all' or one of: {', '.join(ALLOWED_CATEGORIES)}.")
    try:
        wanted_month = _month(month)
    except ValueError as exc:
        return _error(str(exc))
    matches = _select(normalized, wanted_month)
    total = round(sum(item["amount"] for item in matches), 2)
    breakdown = {name: round(sum(item["amount"] for item in matches if item["category"] == name), 2)
                 for name in ALLOWED_CATEGORIES if any(item["category"] == name for item in matches)}
    return {"category": normalized, "month": wanted_month or "all", "currency": "INR", "total": total,
            "count": len(matches), "average": round(total / len(matches), 2) if matches else 0.0, "per_category": breakdown}


@mcp.tool()
def convert_currency(amount: float, from_currency: str, to_currency: str) -> dict[str, Any]:
    """Convert an amount using fixed static demo rates for INR, USD, EUR, GBP, AED, and JPY."""
    _record_call("convert_currency", amount=amount, from_currency=from_currency, to_currency=to_currency)
    source, target = str(from_currency).strip().upper(), str(to_currency).strip().upper()
    if source not in CURRENCIES or target not in CURRENCIES:
        return _error(f"Currencies must be one of: {', '.join(CURRENCIES)}.")
    try:
        value = float(amount)
    except (TypeError, ValueError):
        return _error("Amount must be a number.")
    converted = value / USD_RATES[source] * USD_RATES[target]
    return {"amount": value, "from_currency": source, "to_currency": target,
            "converted_amount": round(converted, 2), "rate_type": "static demo rates",
            "note": "This conversion uses fixed static demo rates, not live exchange rates."}


_SAFE_OPS = {ast.Add: operator.add, ast.Sub: operator.sub, ast.Mult: operator.mul,
             ast.Div: operator.truediv, ast.FloorDiv: operator.floordiv, ast.Mod: operator.mod,
             ast.Pow: operator.pow, ast.USub: operator.neg, ast.UAdd: operator.pos}


def _safe_eval(node: ast.AST) -> float | int:
    if isinstance(node, ast.Constant) and isinstance(node.value, (int, float)) and not isinstance(node.value, bool):
        return node.value
    if isinstance(node, ast.BinOp) and type(node.op) in _SAFE_OPS:
        return _SAFE_OPS[type(node.op)](_safe_eval(node.left), _safe_eval(node.right))
    if isinstance(node, ast.UnaryOp) and type(node.op) in _SAFE_OPS:
        return _SAFE_OPS[type(node.op)](_safe_eval(node.operand))
    raise ValueError("Only numbers, + - * / // % **, unary signs, and parentheses are allowed.")


@mcp.tool()
def calculate(expression: str) -> dict[str, Any]:
    """Safely calculate arithmetic using + - * / // % ** and parentheses without evaluating arbitrary code."""
    _record_call("calculate", expression=expression)
    try:
        result = _safe_eval(ast.parse(str(expression), mode="eval").body)
        if isinstance(result, float) and not result.is_integer():
            result = round(result, 10)
        return {"expression": expression, "result": result}
    except Exception as exc:
        return _error(f"Could not evaluate expression safely: {exc}")


@mcp.tool()
def get_current_date() -> dict[str, str]:
    """Return today's local date, weekday, and ISO timestamp."""
    _record_call("get_current_date")
    now = datetime.now().astimezone()
    return {"date": now.date().isoformat(), "weekday": now.strftime("%A"), "iso_timestamp": now.isoformat()}


@mcp.resource("expenses://all")
def all_expenses_resource() -> str:
    """Return a JSON snapshot of every expense in the in-memory book."""
    _record_call("resource:expenses://all")
    return json.dumps(EXPENSES, ensure_ascii=False, indent=2)


@mcp.prompt()
def monthly_report(month: str) -> str:
    """Ask the model to call get_spending_summary and list_expenses before writing a short monthly report."""
    _record_call("prompt:monthly_report", month=month)
    return (f"Prepare a short, useful expense report for {month} (use the YYYY-MM form for the month argument). "
            "First call get_spending_summary and list_expenses yourself for that month, then summarize total "
            "spending, the category breakdown, and two practical observations. Do not invent figures.")


if __name__ == "__main__":
    print("=" * 72)
    print("  MCP EXPENSE LAB - Smart Expense Tracker server starting")
    print("  Transport : streamable-http")
    print(f"  Endpoint  : http://{HOST}:{PORT}{PATH}")
    print("  Tools     : add_expense, list_expenses, delete_expense, get_spending_summary,")
    print("              convert_currency, calculate, get_current_date")
    print("  Resource  : expenses://all    Prompt: monthly_report")
    print("=" * 72)
    sys.stdout.flush()
    mcp.run(transport="streamable-http", host=HOST, port=PORT, streamable_http_path=PATH)
<<<END FILE: server/mcp_server.py>>>

<<<FILE: client/__init__.py>>>
# EMPTY file.
<<<END FILE: client/__init__.py>>>

<<<FILE: client/mcp_client.py>>>
﻿"""Reusable MCP client for the Streamlit host application."""
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
<<<END FILE: client/mcp_client.py>>>

<<<FILE: src/__init__.py>>>
# EMPTY file.
<<<END FILE: src/__init__.py>>>

<<<FILE: src/env_setup.py>>>
"""First-run environment setup for the MCP Expense Lab."""
from __future__ import annotations

from pathlib import Path

PROJECT_DIR = Path(__file__).resolve().parents[1]
ENV_PATH = PROJECT_DIR / ".env"
EXAMPLE_PATH = PROJECT_DIR / ".env.example"

DEFAULT_ENV_TEXT = """# Get a Gemini API key at https://aistudio.google.com/apikey and paste it after the = sign
GEMINI_API_KEY=

# MCP server (the server and the app must agree on these)
MCP_SERVER_HOST=127.0.0.1
MCP_SERVER_PORT=8766
"""


def ensure_env_file() -> bool:
    """Create .env (and .env.example) when missing; never overwrite an existing .env."""
    if ENV_PATH.exists():
        return False
    if not EXAMPLE_PATH.exists():
        EXAMPLE_PATH.write_text(DEFAULT_ENV_TEXT, encoding="utf-8")
    ENV_PATH.write_text(EXAMPLE_PATH.read_text(encoding="utf-8"), encoding="utf-8")
    print(f"Created .env at {ENV_PATH}")
    return True
<<<END FILE: src/env_setup.py>>>

<<<FILE: src/llm.py>>>
"""Gemini-only agent loop: LLM <-> MCP tools, with retry and model rotation so every question gets an answer."""
from __future__ import annotations

import json
import os
import re
import time
from typing import Any, Callable

from openai import (
    APIConnectionError,
    APIStatusError,
    APITimeoutError,
    AuthenticationError,
    BadRequestError,
    NotFoundError,
    OpenAI,
    PermissionDeniedError,
    RateLimitError,
)

from client.mcp_client import call_tool, list_tools, mcp_tool_to_openai_schema, run_sync

GEMINI_BASE_URL = "https://generativelanguage.googleapis.com/v1beta/openai/"
MODEL_CHOICES = ["gemini-3.6-flash", "gemini-3.1-flash-lite", "gemini-3.5-flash-lite"]  # first = default
MAX_ATTEMPTS = 4

SYSTEM_PROMPT = (
    "You are the Smart Expense Tracker assistant. Amounts are INR unless the user states another currency. "
    "Always use the tools for expense data, dates, currency conversion and arithmetic. Never add up, average, "
    "count or convert numbers yourself: for any total, count, average or category breakdown call "
    "get_spending_summary (it accepts an optional month such as 2026-09, which is how you build monthly reports); "
    "to show individual expenses call list_expenses; for any other math call calculate. Use the fewest tool "
    "calls needed, call independent tools together in one step, and never repeat a tool call with the same "
    "arguments. Call add_expense exactly once per expense. If a request needs no tool (general knowledge, or "
    "something none of the tools can do, such as weather), answer directly and say plainly when a capability "
    "is not available. Explain results clearly and briefly."
)


KEY_REJECTED = "The Gemini API key was rejected. Check GEMINI_API_KEY in your .env file, save it, then refresh the page."


class ProviderError(RuntimeError):
    """A friendly Gemini failure that the UI can show as-is."""

    def __init__(self, reason: str) -> None:
        self.reason = reason
        super().__init__(reason)


def _is_key_problem(exc: Exception) -> bool:
    """Gemini reports a wrong or expired key as HTTP 400 ('Please pass a valid API key'), not 401, so check the text too."""
    return isinstance(exc, (AuthenticationError, PermissionDeniedError)) or (
        isinstance(exc, BadRequestError) and "api key" in str(exc).lower()
    )


def make_client() -> OpenAI:
    """Build the Gemini client from the current environment (the key is read at call time)."""
    return OpenAI(base_url=GEMINI_BASE_URL, api_key=os.getenv("GEMINI_API_KEY", ""), timeout=45, max_retries=0)


def _retry_delay(exc: Exception | None, attempt: int) -> float:
    """Seconds to wait: Retry-After header, then a 'retry in Ns' hint in the error text, then exponential backoff."""
    headers = getattr(getattr(exc, "response", None), "headers", None)
    if headers and headers.get("retry-after"):
        try:
            return min(float(headers["retry-after"]), 60.0)
        except ValueError:
            pass
    hint = re.search(r"retry\w*\D{0,15}?(\d+(?:\.\d+)?)\s*s", str(exc), re.I)
    if hint:
        return min(float(hint.group(1)) + 1.0, 60.0)
    return min(3.0 * (2 ** attempt), 30.0)


def _create_with_retry(client: OpenAI, models: list[str], messages: list[Any], tools: list[dict] | None,
                       on_status: Callable[[str], None] | None) -> tuple[Any, str]:
    """Call Gemini. On rate limits / 5xx / timeouts try the next model, then wait and retry. Returns (response, model)."""
    last: Exception | None = None
    for attempt in range(MAX_ATTEMPTS):
        for model in models:
            kwargs: dict[str, Any] = {"model": model, "messages": messages, "reasoning_effort": "low"}
            if tools:
                kwargs.update(tools=tools, tool_choice="auto")
            try:
                response = client.chat.completions.create(**kwargs)
                if not getattr(response, "choices", None):
                    last = RuntimeError("empty response")
                    continue
                return response, model
            except (AuthenticationError, PermissionDeniedError) as exc:
                raise ProviderError(KEY_REJECTED) from exc
            except BadRequestError as exc:
                if _is_key_problem(exc):
                    raise ProviderError(KEY_REJECTED) from exc
                raise ProviderError(f"Gemini rejected the request: {str(exc)[:200]}") from exc
            except NotFoundError as exc:  # a retired model id: just try the next one
                last = exc
                continue
            except (RateLimitError, APITimeoutError, APIConnectionError) as exc:
                last = exc
                continue
            except APIStatusError as exc:
                if exc.status_code >= 500:
                    last = exc
                    continue
                raise ProviderError(f"Gemini returned an error ({exc.status_code}).") from exc
        if attempt < MAX_ATTEMPTS - 1:
            delay = _retry_delay(last, attempt)
            if on_status:
                on_status(f"Gemini is busy or rate-limited. Retrying in {delay:.0f}s (attempt {attempt + 2} of {MAX_ATTEMPTS})...")
            time.sleep(delay)
    raise ProviderError("Gemini is not responding right now (rate limit or high demand). Please wait a minute and try again.")


_TOOL_CACHE: dict[str, Any] = {"at": 0.0, "schemas": []}


def _tool_schemas() -> list[dict]:
    """Discover the MCP server's tools (cached for 60 s) and convert them to OpenAI function schemas."""
    if not _TOOL_CACHE["schemas"] or time.time() - _TOOL_CACHE["at"] > 60:
        _TOOL_CACHE["schemas"] = [mcp_tool_to_openai_schema(tool) for tool in run_sync(list_tools())]
        _TOOL_CACHE["at"] = time.time()
    return _TOOL_CACHE["schemas"]


def check_connection() -> tuple[bool, str]:
    """Cheap health check: is a key set, and does Gemini accept it?"""
    if not os.getenv("GEMINI_API_KEY", "").strip():
        return False, "No GEMINI_API_KEY found. Open the .env file, paste your key after GEMINI_API_KEY=, save, then refresh this page."
    try:
        make_client().models.list()
        return True, "Connected to Gemini"
    except Exception as exc:  # noqa: BLE001
        if _is_key_problem(exc):
            return False, KEY_REJECTED
        return False, f"Could not reach Gemini: {str(exc)[:120]}"


def run_agent(model: str, user_message: str, history: list[dict] | None, max_steps: int = 6,
              on_status: Callable[[str], None] | None = None) -> dict[str, Any]:
    """Answer one user turn. Returns {"text", "trace", "model"} with non-empty text, or raises ProviderError."""
    tools = _tool_schemas()
    order = [model, *[name for name in MODEL_CHOICES if name != model]]
    client = make_client()
    messages: list[Any] = [{"role": "system", "content": SYSTEM_PROMPT}, *(history or []), {"role": "user", "content": user_message}]
    trace: list[dict[str, Any]] = []
    done: dict[str, str] = {}  # tool name + arguments -> result already sent this turn (blocks duplicate side effects)
    used = model

    def finish(instruction: str) -> str:
        nonlocal used
        messages.append({"role": "user", "content": instruction})
        response, used = _create_with_retry(client, order, messages, None, on_status)
        return (response.choices[0].message.content or "").strip()

    for _ in range(max(1, int(max_steps))):
        response, used = _create_with_retry(client, order, messages, tools, on_status)
        message = response.choices[0].message
        messages.append(message.model_dump(exclude_none=True))
        calls = message.tool_calls or []
        if not calls:
            text = (message.content or "").strip() or finish("Please answer my last question in plain words using the tool results above.")
            return {"text": text or "I could not produce an answer. Please rephrase and try again.", "trace": trace, "model": used}
        for call in calls:
            try:
                args = json.loads(call.function.arguments or "{}")
                args = args if isinstance(args, dict) else {}
            except json.JSONDecodeError:
                args = {}
            signature = f"{call.function.name}:{json.dumps(args, sort_keys=True, default=str)}"
            if signature in done:
                content = done[signature]
            else:
                started = time.perf_counter()
                result = run_sync(call_tool(call.function.name, args))  # MCPServerUnavailable propagates to the UI
                trace.append({"tool": call.function.name, "args": args, "result": result, "ms": round((time.perf_counter() - started) * 1000, 1)})
                value = result["structured"] if result.get("structured") is not None else result.get("text", "")
                content = done[signature] = json.dumps(value, ensure_ascii=False, default=str)
            messages.append({"role": "tool", "tool_call_id": call.id or f"call_{len(messages)}", "content": content})
    text = finish("Stop calling tools. Give the best final answer now using the results above.")
    return {"text": text or "I reached the step limit. Please try a shorter request.", "trace": trace, "model": used}
<<<END FILE: src/llm.py>>>

<<<FILE: app.py>>>
"""Streamlit host for the MCP Expense Lab (Gemini only)."""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path
from typing import Any

import pandas as pd
import streamlit as st
from dotenv import load_dotenv

PROJECT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(PROJECT_DIR))
from src.env_setup import ensure_env_file  # noqa: E402

created_env = ensure_env_file()
load_dotenv(PROJECT_DIR / ".env", override=True)  # re-read on every rerun, so a newly pasted key works after a page refresh

from client.mcp_client import (  # noqa: E402
    MCP_SERVER_URL,
    MCPServerUnavailable,
    call_tool,
    field,
    get_prompt,
    list_prompts,
    list_resources,
    list_tools,
    ping,
    read_resource,
    run_sync,
)
from src.llm import MODEL_CHOICES, ProviderError, check_connection, run_agent  # noqa: E402

st.set_page_config(page_title="MCP Expense Lab", page_icon="💸", layout="wide")

st.session_state.setdefault("messages", [])


def md(text: str) -> str:
    """Escape $ so currency like $58.66 is not rendered as LaTeX math by Streamlit."""
    return str(text).replace("$", "\\$")


@st.cache_data(ttl=30)
def cached_connection(key_fingerprint: str) -> tuple[bool, str]:
    return check_connection()


@st.cache_data(ttl=10)
def cached_mcp_ping() -> bool:
    return run_sync(ping())


def mcp_help() -> str:
    return (
        f"Couldn't reach the MCP server at `{MCP_SERVER_URL}`. Start it first (in a separate terminal) with:\n\n"
        f"```text\ncd \"{PROJECT_DIR}\"\npython server/mcp_server.py\n```\n\nor run `start_server.bat` (Windows) / `start_server.sh` (Mac/Linux)."
    )


def render_schema_form(schema: dict[str, Any] | None, prefix: str) -> dict[str, Any]:
    """Build input widgets directly from an MCP tool's JSON schema."""
    properties = (schema or {}).get("properties", {}) or {}
    required = set((schema or {}).get("required", []) or [])
    values: dict[str, Any] = {}
    if not properties:
        st.caption("This tool takes no arguments.")
        return values
    for name, spec in properties.items():
        spec = spec or {}
        label = f"{name}{' *' if name in required else ''}"
        help_text = spec.get("description", "")
        widget_key = f"{prefix}_{name}"
        kind = spec.get("type", "string")
        default = spec.get("default")
        if kind == "integer":
            values[name] = st.number_input(label, value=int(default or 0), step=1, help=help_text, key=widget_key)
        elif kind == "number":
            values[name] = st.number_input(label, value=float(default or 0.0), help=help_text, key=widget_key)
        elif kind == "boolean":
            values[name] = st.checkbox(label, value=bool(default), help=help_text, key=widget_key)
        else:
            values[name] = st.text_input(label, value=str(default or ""), help=help_text, key=widget_key)
    return {key: value for key, value in values.items() if value != "" or key in required}


def render_trace(trace: list[dict[str, Any]]) -> None:
    if not trace:
        return
    with st.expander("🔧 Tool calls"):
        for step in trace:
            st.markdown(f"**{step.get('tool', 'tool')}** · `{step.get('ms', 0)} ms`")
            st.code(json.dumps({"args": step.get("args", {}), "result": step.get("result", {})}, indent=2, ensure_ascii=False, default=str), language="json")


def discover() -> None:
    try:
        st.session_state.mcp_tools = run_sync(list_tools())
        st.session_state.mcp_resources = run_sync(list_resources())
        st.session_state.mcp_prompts = run_sync(list_prompts())
    except MCPServerUnavailable:
        st.error(mcp_help())


api_key = os.getenv("GEMINI_API_KEY", "").strip()
has_key = bool(api_key)

with st.sidebar:
    st.markdown("### 💸 Smart Expense Tracker")
    st.caption("Day 4 · Agents & MCP — Host + Client + Server")

    st.markdown("### 🤖 Gemini")
    ready, status = cached_connection(f"{len(api_key)}:{api_key[-4:]}")
    st.caption(("✅ " if ready else "❌ ") + status)
    selected_model = st.selectbox("Model", MODEL_CHOICES, key="model_choice")
    custom_model = st.text_input("…or type a custom model name", key="custom_model", placeholder="Optional")
    active_model = custom_model.strip() or selected_model
    st.markdown(f"**Using:** `{active_model}`")

    st.markdown("### 🔌 MCP Server")
    server_ok = cached_mcp_ping()
    st.markdown(("✅ Online" if server_ok else "❌ Offline") + f"  · `{MCP_SERVER_URL}`")
    if not server_ok:
        st.caption("Start the standalone server before using tools or chat.")
    st.markdown("---")
    max_steps = st.slider("Max agent steps", 1, 8, 6)
    if st.button("Clear chat"):
        st.session_state.messages = []
        st.rerun()

st.title("💸 MCP Expense Lab")
st.caption(f"Smart Expense Tracker · Gemini · `{active_model}`")
tab_chat, tab_tools, tab_resources, tab_how = st.tabs(["💬 Agent Chat", "🧰 Tool Explorer", "📚 Resources & Prompts", "🏗️ How it works"])

with tab_chat:
    if not has_key:
        st.warning(
            "**Add your Gemini API key to start chatting.** Open the `.env` file in this project folder, "
            "paste your key after `GEMINI_API_KEY=` (get one at [aistudio.google.com/apikey](https://aistudio.google.com/apikey)), "
            "save the file, then refresh this page."
        )
    elif not ready:
        st.error(status)
    if not server_ok:
        st.error(mcp_help())

    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            if message.get("error"):
                st.error(message["content"])
            else:
                st.markdown(md(message["content"]))
                if message["role"] == "assistant":
                    st.caption(f"answered by Gemini · {message.get('model', active_model)}")
                    render_trace(message.get("trace", []))

    examples = ["Add 450 rupees for lunch today", "How much did I spend on travel?", "Convert my total spending to USD", "Delete expense 2 and show the new summary"]
    examples_slot = st.empty()
    if not st.session_state.messages:
        with examples_slot.container():
            st.markdown("**Try an example:**")
            columns = st.columns(2)
            for index, example in enumerate(examples):
                if columns[index % 2].button(example, key=f"example_{index}"):
                    st.session_state.pending_prompt = example

    prompt = st.chat_input("Ask the expense assistant…", disabled=not has_key) or st.session_state.pop("pending_prompt", None)
    if prompt and has_key:
        examples_slot.empty()  # hide the example buttons as soon as a question is being answered
        history = [{"role": item["role"], "content": item["content"]} for item in st.session_state.messages
                   if item["role"] in ("user", "assistant") and not item.get("skip")]
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(md(prompt))
        with st.chat_message("assistant"):
            status_box = st.empty()
            try:
                with st.spinner("Thinking…"):
                    result = run_agent(active_model, prompt, history, max_steps=max_steps, on_status=lambda text: status_box.info("⏳ " + text))
                status_box.empty()
                st.markdown(md(result["text"]))
                st.caption(f"answered by Gemini · {result['model']}")
                render_trace(result["trace"])
                st.session_state.messages.append({"role": "assistant", "content": result["text"], "trace": result["trace"], "model": result["model"]})
            except Exception as exc:  # never show a raw traceback; keep the chat usable
                status_box.empty()
                if isinstance(exc, MCPServerUnavailable):
                    reason = mcp_help()
                elif isinstance(exc, ProviderError):
                    reason = exc.reason
                else:
                    reason = f"Something went wrong: {str(exc)[:200]}. Please try again."
                st.error(reason)
                st.session_state.messages[-1]["skip"] = True  # keep the failed question out of the LLM history
                st.session_state.messages.append({"role": "assistant", "content": reason, "error": True, "skip": True})

with tab_tools:
    st.write("Discover and call MCP tools directly — no LLM is involved.")
    if st.button("Discover server tools", key="discover_tools") or "mcp_tools" not in st.session_state:
        discover()
    tools = st.session_state.get("mcp_tools", [])
    if tools:
        picked_name = st.selectbox("Pick a tool", [tool.name for tool in tools], key="picked_tool")
        picked = next(tool for tool in tools if tool.name == picked_name)
        st.write(field(picked, "description", default="") or "No description")
        schema = field(picked, "input_schema", "inputSchema", default={})
        with st.expander("Input schema"):
            st.json(schema)
        args = render_schema_form(schema, f"explorer_{picked_name}")
        if st.button("Call tool", type="primary", key="call_selected_tool"):
            try:
                result = run_sync(call_tool(picked_name, args))
                (st.success if result["ok"] else st.error)(md(result["text"]))
                st.json(result["structured"])
            except MCPServerUnavailable:
                st.error(mcp_help())

with tab_resources:
    if st.button("Refresh resources and prompts", key="discover_resources") or "mcp_resources" not in st.session_state:
        discover()
    resources = st.session_state.get("mcp_resources", [])
    prompts = st.session_state.get("mcp_prompts", [])
    st.subheader("Resources")
    if resources:
        resource_uri = st.selectbox("Resource", [str(resource.uri) for resource in resources], key="resource_uri")
        try:
            st.dataframe(pd.DataFrame(json.loads(run_sync(read_resource(resource_uri)))))
        except MCPServerUnavailable:
            st.error(mcp_help())
        except (json.JSONDecodeError, ValueError) as exc:
            st.error(str(exc))
    else:
        st.info("Start the server and refresh to discover resources.")
    st.subheader("Prompts")
    if prompts:
        prompt_obj = prompts[0]
        prompt_args = {argument.name: st.text_input(argument.name, key=f"prompt_arg_{argument.name}", placeholder="e.g. 2026-09")
                       for argument in (getattr(prompt_obj, "arguments", None) or [])}
        if st.button("Render monthly report prompt", key="render_prompt"):
            try:
                st.code(run_sync(get_prompt(prompt_obj.name, prompt_args)))
            except MCPServerUnavailable:
                st.error(mcp_help())
    else:
        st.info("No prompts discovered yet.")

with tab_how:
    st.subheader("Host → Client → Server")
    st.code("HOST (Streamlit app)\n  │  Gemini chooses a function\n  ▼\nCLIENT (client/mcp_client.py) ── streamable HTTP ──► SERVER (server/mcp_server.py)\n  │                                                   │\n  └──────────── tool result over MCP ◄───────────────┘", language="text")
    st.markdown("| Layer | Responsibility | File |\n|---|---|---|\n| **Host** | Chat UI, model choice, history | `app.py`, `src/llm.py` |\n| **Client** | MCP handshake, discovery, calls, schema conversion | `client/mcp_client.py` |\n| **Server** | In-memory expense tools, resource, prompt | `server/mcp_server.py` |")
    st.info("Gemini decides which tool to call; the MCP client executes it on the independent server process.")
<<<END FILE: app.py>>>

VERIFICATION (mandatory - none of these need a Gemini key)
A. Syntax:  python -m py_compile app.py server/mcp_server.py client/mcp_client.py src/env_setup.py src/llm.py
B. Version:  python -c "from mcp.server import MCPServer; print('mcp OK')"
   If this raises ImportError, run  pip install -U "mcp>=2.0"  and repeat.
C. Start the MCP server in a BACKGROUND terminal:  python server/mcp_server.py
   Wait until it reports it is listening on http://127.0.0.1:8766/mcp. If port 8766 is already in use, change
   MCP_SERVER_PORT in BOTH .env and .env.example to a free port, then start it again.
D. Save the following as _smoke_test.py in the workspace root, run it with `python _smoke_test.py`, and it must
   print "MCP layer OK":

<<<FILE: _smoke_test.py>>>
import json
from dotenv import load_dotenv
load_dotenv()
from client import mcp_client as C

tools = C.run_sync(C.list_tools())
assert len(tools) == 7, [t.name for t in tools]


def call(name, args):
    return C.run_sync(C.call_tool(name, args))["structured"]


assert call("get_spending_summary", {})["total"] == 4419.0
assert call("get_spending_summary", {"month": "2026-09"})["count"] == 5
assert call("get_spending_summary", {"category": "travel"})["total"] == 600.0
assert call("calculate", {"expression": "(120+80)*3"})["result"] == 600
assert "error" in str(call("get_spending_summary", {"month": "bad"}))
assert "error" in str(call("add_expense", {"amount": 5, "category": "nope", "description": "x"}))
assert "nothing was deleted" in str(call("delete_expense", {"expense_id": 999}))
assert call("convert_currency", {"amount": 4419, "from_currency": "INR", "to_currency": "USD"})["converted_amount"] == 53.24
assert len(json.loads(C.run_sync(C.read_resource("expenses://all")))) == 5
print("MCP layer OK")
<<<END FILE: _smoke_test.py>>>

E. Confirm the Streamlit app loads without an exception (this works with an empty API key):
   python -c "from streamlit.testing.v1 import AppTest; at = AppTest.from_file('app.py', default_timeout=120).run(); assert not at.exception, at.exception; print('App loads OK')"
F. ONLY if GEMINI_API_KEY in .env is non-empty (it will normally be empty at build time - that is expected), run one
   live agent turn and confirm it prints a non-empty answer that mentions 600:
   python -c "from dotenv import load_dotenv; load_dotenv(); from src.llm import run_agent, MODEL_CHOICES; r = run_agent(MODEL_CHOICES[0], 'How much did I spend on travel?', []); print(r['text']); assert r['text'].strip()"
   If the key is empty, skip this step and say so in the final report.
G. Cleanup: stop the background MCP server and delete _smoke_test.py.

FINAL REPORT (keep it short)
1. The created file tree (relative to the workspace root).
2. Which verification steps (A-G) passed, and clearly say if step F was skipped because no Gemini key is set yet.
3. The three next steps for the user:
   a) Open the .env file and paste the Gemini API key after GEMINI_API_KEY= (get one at https://aistudio.google.com/apikey), then save.
   b) Start the MCP server and leave it running: double-click start_server.bat (Windows) or run `bash start_server.sh` (Mac/Linux).
   c) In a second terminal, in the same folder, run: streamlit run app.py   then open http://localhost:8501
````

## After the prompt finishes

1. Open `.env` and paste your Gemini key after `GEMINI_API_KEY=` (get one at https://aistudio.google.com/apikey), then save.
2. Terminal 1 - start the MCP server and leave it running:

```bash
python server/mcp_server.py
```

(or double-click `start_server.bat` on Windows / run `bash start_server.sh` on Mac and Linux)

3. Terminal 2 - from the same folder, start the app, then open http://localhost:8501:

```bash
streamlit run app.py
```
