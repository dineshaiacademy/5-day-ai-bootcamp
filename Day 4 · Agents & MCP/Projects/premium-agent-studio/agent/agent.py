"""
INDEPENDENT AGENT — Day 4 · Agents & MCP, Dinesh AI Academy

This module is the whole point of the "premium-agent-studio" project: an
agent that is completely independent of any particular front end. It has
no import of `streamlit`, no HTML, no UI code whatsoever — just Gemini
function calling (native `google-genai` SDK, the same pattern this course's
"Building AI Agents" notebook validates) wired to a real MCP tool server
over the network (the same pattern `mcp-live-toolkit` validates).

Two ways to prove it's independent:

  1. Run it completely on its own, no app around it at all:

         python agent/agent.py
         python agent/agent.py "What's the weather in Tokyo right now?"

     This drops you into a plain terminal chat loop. It streams tokens to
     stdout as Gemini generates them, prints every tool call and result as
     they happen, and talks to the MCP server over HTTP — proof this agent
     is a real, working program with zero UI framework involved.

  2. Import it from a host, like `app.py` does:

         from agent.agent import Agent
         agent = Agent(model="gemini-3.5-flash-lite")
         async for event in agent.run(history):
             ...  # the host decides how to display each event

The agent loop, in five steps, repeated until Gemini answers in plain text
or a safety cap is hit:

    1. Ask Gemini    — send the conversation so far, streamed, with the
                        MCP server's tools translated into Gemini function
                        declarations.
    2. Decide         — Gemini either streams back plain text (done) or
                        requests one or more function calls.
    3. Act            — for each function call, run it for real via
                        `session.call_tool(...)` — an HTTP round trip to
                        the standalone MCP server, not a local function.
    4. Observe        — feed each tool's result back to Gemini as a
                        function response.
    5. Repeat         — until step 2 yields plain text, or `max_steps` hits.

Every step is reported as an `AgentEvent` — the host (CLI or Streamlit)
just iterates them and renders however it likes. This module never prints
or logs anything itself when used as a library; the CLI's `print()` calls
live only in `_run_cli()` at the bottom.
"""

from __future__ import annotations

import asyncio
import os
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, AsyncIterator

from dotenv import load_dotenv
from google import genai
from google.genai import types

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from client.mcp_client import connect_to_server, tool_result_to_value  # noqa: E402

load_dotenv()

DEFAULT_MODEL = "gemini-3.5-flash-lite"

DEFAULT_SYSTEM_PROMPT = (
    "You are a helpful, precise assistant with tools to check the time anywhere in "
    "the world, do arithmetic, check REAL current weather, convert units, and manage "
    "a shared task list. Always call the matching tool instead of guessing a time, "
    "weather condition, calculation, or task result yourself. If a question needs "
    "more than one tool, call them one after another rather than guessing what an "
    "earlier one would have returned. If no tool is needed, just answer directly."
)


def _resolve_api_key() -> str | None:
    return os.getenv("GAISTUDIO_API_KEY") or os.getenv("GEMINI_API_KEY")


# ── AgentEvent — the one thing this module hands back to any host ─────────
# A host never touches Gemini or MCP types directly; it only ever sees these.

@dataclass
class AgentEvent:
    kind: str  # "status" | "tool_call" | "tool_result" | "token" | "final" | "usage" | "error"
    data: Any = field(default=None)


# ── MCP tool schema -> Gemini function declaration ──────────────────────
# The MCP server generates tool.input_schema straight from Python type
# hints (plain JSON Schema). Gemini's function-calling `parameters` field
# accepts a similar but stricter subset — this keeps only the keys Gemini
# understands so a schema pydantic adds extra metadata to (like "title" or
# "additionalProperties") never causes a 400 from the Gemini API.

_ALLOWED_SCHEMA_KEYS = {"type", "description", "properties", "items", "required", "enum", "format"}


def _sanitize_schema(schema: dict) -> dict:
    if not isinstance(schema, dict):
        return {"type": "string"}
    clean: dict = {}
    for key in _ALLOWED_SCHEMA_KEYS:
        if key not in schema:
            continue
        value = schema[key]
        if key == "properties" and isinstance(value, dict):
            clean[key] = {name: _sanitize_schema(v) for name, v in value.items()}
        elif key == "items" and isinstance(value, dict):
            clean[key] = _sanitize_schema(value)
        else:
            clean[key] = value
    clean.setdefault("type", "object" if "properties" in clean else "string")
    return clean


def _mcp_tool_to_gemini_declaration(tool) -> dict:
    schema = _sanitize_schema(tool.input_schema or {"type": "object", "properties": {}})
    return {"name": tool.name, "description": tool.description or "", "parameters": schema}


# ── The agent itself ─────────────────────────────────────────────────────

class Agent:
    """
    An independent, MCP-tool-using Gemini agent. Holds no conversation state
    of its own on purpose — the host passes in `history` (a plain list of
    {"role": "user"|"assistant", "content": str} dicts) on every call, the
    same way any stateless LLM API call works. That keeps this class usable
    from a one-shot CLI call, a REPL that keeps its own list, or a Streamlit
    app that keeps history in `st.session_state` — the agent doesn't care.
    """

    def __init__(
        self,
        model: str = DEFAULT_MODEL,
        temperature: float = 0.4,
        max_output_tokens: int = 1024,
        system_prompt: str = DEFAULT_SYSTEM_PROMPT,
        max_steps: int = 6,
        api_key: str | None = None,
    ) -> None:
        resolved_key = api_key or _resolve_api_key()
        if not resolved_key:
            raise ValueError(
                "No Gemini API key found. Set GAISTUDIO_API_KEY (or GEMINI_API_KEY) "
                "in your .env file — get a free key at aistudio.google.com/apikey."
            )
        self.model = model
        self.temperature = temperature
        self.max_output_tokens = max_output_tokens
        self.system_prompt = system_prompt
        self.max_steps = max_steps
        self._client = genai.Client(api_key=resolved_key)

    @staticmethod
    def _history_to_contents(history: list[dict]) -> list[types.Content]:
        contents = []
        for turn in history:
            role = "model" if turn["role"] == "assistant" else "user"
            contents.append(types.Content(role=role, parts=[types.Part.from_text(text=turn["content"])]))
        return contents

    async def run(self, history: list[dict]) -> AsyncIterator[AgentEvent]:
        """
        Run the full agent loop for the conversation in `history` (the last
        entry must be the newest user message) and yield AgentEvents live as
        they happen — tokens as Gemini streams them, tool calls/results as
        they're executed on the MCP server, then a final summary.
        """
        contents = self._history_to_contents(history)
        config = types.GenerateContentConfig(
            system_instruction=self.system_prompt,
            temperature=self.temperature,
            max_output_tokens=self.max_output_tokens,
        )

        try:
            yield AgentEvent("status", "Connecting to the MCP tool server…")
            async with connect_to_server() as session:
                mcp_tools = (await session.list_tools()).tools
                if mcp_tools:
                    declarations = [_mcp_tool_to_gemini_declaration(t) for t in mcp_tools]
                    config.tools = [types.Tool(function_declarations=declarations)]
                yield AgentEvent(
                    "status",
                    f"Discovered {len(mcp_tools)} tool(s): {', '.join(t.name for t in mcp_tools) or 'none'}",
                )

                for step in range(1, self.max_steps + 1):
                    yield AgentEvent("status", f"Asking {self.model} (step {step}/{self.max_steps})…")

                    full_text = ""
                    function_calls: list[Any] = []
                    usage = None

                    stream = self._client.models.generate_content_stream(
                        model=self.model, contents=contents, config=config
                    )
                    for chunk in stream:
                        usage = getattr(chunk, "usage_metadata", None) or usage
                        candidates = getattr(chunk, "candidates", None) or []
                        if not candidates or not candidates[0].content:
                            continue
                        for part in candidates[0].content.parts or []:
                            if getattr(part, "function_call", None) is not None:
                                function_calls.append(part.function_call)
                            elif getattr(part, "text", None):
                                full_text += part.text
                                yield AgentEvent("token", part.text)

                    # Rebuild Gemini's own turn from what the stream produced (it
                    # arrives as deltas, not one ready-made Content) so the next
                    # request in this loop — or the next turn after we return —
                    # includes exactly what the model said this time.
                    model_parts = []
                    if full_text:
                        model_parts.append(types.Part.from_text(text=full_text))
                    for fc in function_calls:
                        model_parts.append(types.Part.from_function_call(name=fc.name, args=dict(fc.args or {})))
                    contents.append(types.Content(role="model", parts=model_parts))

                    if not function_calls:
                        if usage is not None:
                            yield AgentEvent("usage", {
                                "prompt_tokens": getattr(usage, "prompt_token_count", 0) or 0,
                                "completion_tokens": getattr(usage, "candidates_token_count", 0) or 0,
                                "total_tokens": getattr(usage, "total_token_count", 0) or 0,
                            })
                        yield AgentEvent("status", "Done — no further tool needed.")
                        yield AgentEvent("final", full_text)
                        return

                    result_parts = []
                    for fc in function_calls:
                        args = dict(fc.args or {})
                        yield AgentEvent("tool_call", {"name": fc.name, "args": args})
                        try:
                            call_result = await session.call_tool(fc.name, args)
                            value = tool_result_to_value(call_result)
                            is_error = call_result.is_error
                        except Exception as e:
                            value, is_error = {"error": str(e)}, True
                        yield AgentEvent("tool_result", {"name": fc.name, "result": value, "is_error": is_error})
                        payload = value if isinstance(value, dict) else {"result": value}
                        result_parts.append(types.Part.from_function_response(name=fc.name, response=payload))

                    contents.append(types.Content(role="user", parts=result_parts))

                yield AgentEvent("status", f"Hit the {self.max_steps}-step safety cap.")
                yield AgentEvent(
                    "final",
                    f"I hit my {self.max_steps}-step safety limit before finishing — try rephrasing your question.",
                )
        except Exception as e:
            yield AgentEvent("error", str(e))


# ── Standalone CLI — proves this agent runs with zero UI framework ────────

async def _run_cli() -> None:
    print("=" * 72)
    print("  INDEPENDENT AGENT — running standalone (no Streamlit, no app around it)")
    print("=" * 72)
    print(f"  Model            : {DEFAULT_MODEL}")
    print("  MCP tool server  : must already be running — see server/mcp_server.py")
    print("  Type 'exit' to quit. Pass a message as argv to run one turn and exit.")
    print("=" * 72)

    try:
        agent = Agent()
    except ValueError as e:
        print(f"\n[setup error] {e}")
        return

    single_shot = " ".join(sys.argv[1:]).strip()
    history: list[dict] = []

    while True:
        if single_shot:
            user_text = single_shot
        else:
            try:
                user_text = input("\nyou> ").strip()
            except (EOFError, KeyboardInterrupt):
                print()
                break
        if not user_text:
            if single_shot:
                break
            continue
        if user_text.lower() in {"exit", "quit"}:
            break

        history.append({"role": "user", "content": user_text})
        answer = ""
        printed_agent_prefix = False

        async for event in agent.run(history):
            if event.kind == "status":
                print(f"\n  · {event.data}")
            elif event.kind == "tool_call":
                print(f"  🔧 calling {event.data['name']}({event.data['args']})")
            elif event.kind == "tool_result":
                tag = "error" if event.data["is_error"] else "result"
                print(f"     -> {tag}: {event.data['result']}")
            elif event.kind == "token":
                if not printed_agent_prefix:
                    print("\nagent> ", end="", flush=True)
                    printed_agent_prefix = True
                print(event.data, end="", flush=True)
                answer += event.data
            elif event.kind == "usage":
                print(f"\n  · tokens — prompt {event.data['prompt_tokens']}, "
                      f"completion {event.data['completion_tokens']}, total {event.data['total_tokens']}")
            elif event.kind == "error":
                print(f"\n  [error] {event.data}")

        print()
        if answer:
            history.append({"role": "assistant", "content": answer})
        if single_shot:
            break


if __name__ == "__main__":
    asyncio.run(_run_cli())
