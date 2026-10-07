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
