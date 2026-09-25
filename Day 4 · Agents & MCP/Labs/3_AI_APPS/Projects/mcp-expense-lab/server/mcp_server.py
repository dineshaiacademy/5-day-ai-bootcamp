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
