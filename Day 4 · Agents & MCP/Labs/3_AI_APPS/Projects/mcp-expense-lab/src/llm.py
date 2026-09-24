"""Provider configuration and the MCP-backed OpenAI-compatible agent loop."""
from __future__ import annotations

import json
import os
import time
from collections import OrderedDict
from typing import Any

from openai import APIConnectionError, APIStatusError, APITimeoutError, AuthenticationError, BadRequestError, NotFoundError, OpenAI, PermissionDeniedError, RateLimitError
from client.mcp_client import MCPServerUnavailable, call_tool, list_tools, mcp_tool_to_openai_schema, run_sync

GEMINI_NAME = "Gemini (Google AI)"
LMSTUDIO_NAME = "LM Studio (local)"
PROVIDERS: OrderedDict[str, dict[str, Any]] = OrderedDict([
    (GEMINI_NAME, {"base_url": "https://generativelanguage.googleapis.com/v1beta/openai/", "api_key": os.getenv("GEMINI_API_KEY", ""), "needs_key": True, "default_model": os.getenv("GEMINI_MODEL", "gemini-3.6-flash")}),
    (LMSTUDIO_NAME, {"base_url": os.getenv("LOCAL_LLM_BASE_URL", "http://localhost:1234/v1"), "api_key": "lm-studio", "needs_key": False, "default_model": os.getenv("LMSTUDIO_MODEL", "qwen2.5-7b-instruct")}),
])
DEFAULT_PROVIDER = GEMINI_NAME if os.getenv("DEFAULT_PROVIDER", "gemini").lower() == "gemini" else LMSTUDIO_NAME
FALLBACK_PROVIDER = LMSTUDIO_NAME
SYSTEM_PROMPT = ("You are the Smart Expense Tracker assistant. Use MCP tools instead of guessing numbers, "
                 "expense records, dates, or conversion results. Amounts are INR unless the user explicitly "
                 "states another currency. Explain tool results clearly and briefly.")

class ProviderError(RuntimeError):
    """A friendly provider-specific failure that the UI can explain or recover from."""
    def __init__(self, provider: str, reason: str) -> None:
        self.provider, self.reason = provider, reason
        super().__init__(f"{provider}: {reason}")

def _config(provider: str) -> dict[str, Any]:
    if provider not in PROVIDERS:
        raise ProviderError(provider, "unknown provider")
    config = dict(PROVIDERS[provider])
    if provider == GEMINI_NAME:
        config["api_key"] = os.getenv("GEMINI_API_KEY", "")
        config["default_model"] = os.getenv("GEMINI_MODEL", config["default_model"])
    elif provider == LMSTUDIO_NAME:
        config["base_url"] = os.getenv("LOCAL_LLM_BASE_URL", config["base_url"])
        config["default_model"] = os.getenv("LMSTUDIO_MODEL", config["default_model"])
    return config

def make_client(provider: str) -> OpenAI:
    """Build an OpenAI SDK client for Gemini or LM Studio using current environment values."""
    config = _config(provider)
    return OpenAI(base_url=config["base_url"], api_key=config["api_key"], timeout=60, max_retries=1)

def _default_model(provider: str) -> str:
    return str(_config(provider)["default_model"])

def list_models(provider: str) -> list[str]:
    """List usable chat models while always retaining the configured default on failures."""
    default = _default_model(provider)
    try:
        ids = [str(item.id).removeprefix("models/") for item in make_client(provider).models.list().data]
        if provider == GEMINI_NAME:
            excluded = ("image", "audio", "tts", "live", "embedding", "veo", "imagen", "aqa", "learnlm")
            ids = [item for item in ids if "gemini" in item.lower() and not any(word in item.lower() for word in excluded)]
            ids.sort(reverse=True)
        else:
            ids = [item for item in ids if "embed" not in item.lower()]
        ids = list(dict.fromkeys(ids))
        if default in ids:
            ids.remove(default)
        ids.insert(0, default)
        return ids
    except Exception:
        return [default]

def check_provider(provider: str) -> tuple[bool, str]:
    """Perform a quick provider health check without raising exceptions."""
    try:
        config = _config(provider)
        if provider == GEMINI_NAME and not config["api_key"]:
            return False, "Gemini API key is not set"
        ids = [str(item.id) for item in make_client(provider).models.list().data]
        if provider == LMSTUDIO_NAME and not ids:
            return False, "LM Studio is reachable but no model is loaded"
        return True, f"ready ({len(ids)} model{'s' if len(ids) != 1 else ''})"
    except Exception as exc:
        return False, ("LM Studio is unreachable — start Developer → Start Server and load a tool-capable model" if provider == LMSTUDIO_NAME else _classify_reason(exc))

def _classify_reason(exc: Exception) -> str:
    if isinstance(exc, (AuthenticationError, PermissionDeniedError)):
        return "invalid or missing API key"
    if isinstance(exc, RateLimitError):
        return "quota / rate limit hit"
    if isinstance(exc, NotFoundError):
        return "model not found — pick another model"
    if isinstance(exc, (APIConnectionError, APITimeoutError, TimeoutError, ConnectionError)):
        return "provider unreachable"
    if isinstance(exc, BadRequestError) and "tool" in str(exc).lower():
        return "this model does not support tool calling"
    if isinstance(exc, APIStatusError) and "tool" in str(exc).lower():
        return "this model does not support tool calling"
    return str(exc) or exc.__class__.__name__

def _plain(value: Any) -> Any:
    return value.model_dump(exclude_none=True) if hasattr(value, "model_dump") else value

def run_agent(provider: str, model: str, user_message: str, history: list[dict[str, Any]] | None, max_steps: int = 5) -> dict[str, Any]:
    """Run an LLM tool-calling loop where every tool execution goes through the MCP client."""
    mcp_tools = run_sync(list_tools())
    tool_schemas = [mcp_tool_to_openai_schema(tool) for tool in mcp_tools]
    messages: list[Any] = [{"role": "system", "content": SYSTEM_PROMPT}, *(history or []), {"role": "user", "content": user_message}]
    trace: list[dict[str, Any]] = []
    client = make_client(provider)
    for _ in range(max(1, int(max_steps))):
        try:
            response = client.chat.completions.create(model=model, messages=messages, tools=tool_schemas, tool_choice="auto")
        except Exception as exc:
            raise ProviderError(provider, _classify_reason(exc)) from exc
        choices = getattr(response, "choices", None) or []
        message = getattr(choices[0], "message", None) if choices else None
        if message is None:
            raise ProviderError(provider, "the provider returned an empty response")
        messages.append(_plain(message))
        tool_calls = getattr(message, "tool_calls", None) or []
        if not tool_calls:
            return {"text": getattr(message, "content", None) or "", "trace": trace, "provider": provider, "model": model}
        for tool_call in tool_calls:
            function = getattr(tool_call, "function", None)
            name = getattr(function, "name", "")
            try:
                arguments = json.loads(getattr(function, "arguments", "{}") or "{}")
                if not isinstance(arguments, dict):
                    arguments = {}
            except (TypeError, json.JSONDecodeError):
                arguments = {}
            started = time.perf_counter()
            result = run_sync(call_tool(name, arguments))
            duration_ms = round((time.perf_counter() - started) * 1000, 1)
            trace.append({"tool": name, "args": arguments, "result": result, "ms": duration_ms})
            content = result.get("structured") if result.get("structured") is not None else result.get("text", "")
            messages.append({"role": "tool", "tool_call_id": getattr(tool_call, "id", ""), "content": json.dumps(content, ensure_ascii=False, default=str)})
    return {"text": f"I reached the {max_steps}-step safety limit before finishing. Please try a shorter request.", "trace": trace, "provider": provider, "model": model}

def run_agent_with_fallback(provider: str, model: str, user_message: str, history: list[dict[str, Any]] | None, max_steps: int = 5, auto_fallback: bool = True, fallback_model: str | None = None) -> dict[str, Any]:
    """Run the chosen provider once, optionally retrying Gemini once on LM Studio."""
    try:
        return run_agent(provider, model, user_message, history, max_steps=max_steps)
    except MCPServerUnavailable:
        raise
    except ProviderError as first_error:
        if provider != GEMINI_NAME or not auto_fallback:
            raise
        chosen_fallback_model = fallback_model or _default_model(FALLBACK_PROVIDER)
        try:
            result = run_agent(FALLBACK_PROVIDER, chosen_fallback_model, user_message, history, max_steps=max_steps)
            result["fell_back"], result["fallback_reason"] = True, first_error.reason
            return result
        except MCPServerUnavailable:
            raise
        except ProviderError as second_error:
            raise ProviderError(provider, f"Gemini failed ({first_error.reason}); LM Studio failed ({second_error.reason})") from second_error

