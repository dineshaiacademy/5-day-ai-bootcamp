"""
MCP Live Toolkit — Chat App (Dinesh AI Academy, Day 4 · Agents & MCP)

The story this app tells, made physical instead of theoretical:

    Server   server/mcp_server.py — a standalone process with its own
             lifecycle. YOU launch it (sidebar button, or a terminal
             command). It runs over real network HTTP, on its own port,
             and keeps running whether or not this app — or any client at
             all — is connected to it.
    Client   client/mcp_client.py — lives inside this app (the "host").
             It never starts the server; it only knows the server's URL.
             Every action below opens a fresh MCP session, speaks the MCP
             protocol over that HTTP connection, and closes it again.
    Host     This Streamlit app. A human uses it. It owns the chat UI, the
             LLM call, and (optionally, via the sidebar) a convenience
             button that launches the server FOR you — but that button is
             just running the exact same command you could type yourself.

Two tabs prove the same point the sibling `mcp-notes-demo` project makes,
against a richer toolkit and a real network transport instead of stdio:

    1. Toolkit Explorer   No LLM anywhere. Pick a tool the server reports
                           it has — live, nothing hardcoded — and call it
                           by hand. This is what an MCP client does,
                           LLM or not.
    2. Chat (LLM + MCP)   An agent loop where the LLM only ever *decides*
                           which tool to call; the MCP client is what
                           actually executes it, over the network, on a
                           process you can watch running in its own
                           terminal window.
"""

from __future__ import annotations

import asyncio
import json
import os
import subprocess
import sys
from datetime import datetime
from pathlib import Path

import streamlit as st
from dotenv import load_dotenv
from openai import OpenAI

sys.path.insert(0, str(Path(__file__).resolve().parent))
from client.mcp_client import (
    MCP_SERVER_URL,
    connect_to_server,
    field,
    is_server_reachable,
    mcp_tool_to_openai_schema,
    tool_call_is_error,
    tool_result_to_value,
)

load_dotenv()

# ── Config ───────────────────────────────────────────────────────────────

PROJECT_ROOT = Path(__file__).resolve().parent
REPO_ROOT = PROJECT_ROOT.parents[2]  # .../Projects/mcp-live-toolkit -> .../Day 4 .../ -> repo root
PROJECT_REL_PATH = PROJECT_ROOT.relative_to(REPO_ROOT).as_posix()
SERVER_SCRIPT = PROJECT_ROOT / "server" / "mcp_server.py"
SERVER_LOG = PROJECT_ROOT / "server" / ".server.log"

GEMINI_REASONING_EFFORT = "low"
GEMINI_EXCLUDE = (
    "image", "audio", "tts", "live", "transcribe", "computer-use", "robotics",
    "veo", "lyria", "aqa", "deep-research", "antigravity", "nano-banana",
)

PROVIDERS = {
    "LM Studio (local)": {
        "base_url": os.getenv("LOCAL_LLM_BASE_URL", "http://localhost:1234/v1"),
        "api_key": "local",
        "needs_key": False,
        "default_model": "lfm2.5-350m",
    },
    "Gemini (Google AI)": {
        "base_url": "https://generativelanguage.googleapis.com/v1beta/openai/",
        "api_key": os.getenv("GEMINI_API_KEY") or os.getenv("GAISTUDIO_API_KEY"),
        "needs_key": True,
        "default_model": "gemini-3.6-flash",
    },
}

DEFAULT_MAX_STEPS = 5

SYSTEM_PROMPT_AGENT = (
    "You are a helpful everyday assistant with tools to check the time anywhere in the world, "
    "do arithmetic, check REAL current weather, convert units, and manage a shared task list. "
    "Always call the matching tool instead of guessing a time, weather condition, calculation, "
    "or task result yourself. If a question needs more than one tool, call them one after "
    "another rather than guessing what an earlier one would have returned. If no tool is "
    "needed, just answer directly."
)

TOOL_ICONS = {
    "get_current_time": ":material/schedule:",
    "calculate": ":material/calculate:",
    "get_weather": ":material/partly_cloudy_day:",
    "convert_units": ":material/swap_horiz:",
    "add_task": ":material/add_task:",
    "list_tasks": ":material/checklist:",
    "complete_task": ":material/task_alt:",
    "roll_dice": ":material/casino:",
}

SUGGESTIONS = {
    ":material/partly_cloudy_day: Weather": "What's the weather in Paris right now?",
    ":material/schedule: World clock": "What time is it in Tokyo and in New York right now?",
    ":material/calculate: Math": "What's 18% of 245.50?",
    ":material/swap_horiz: Convert": "Convert 5 miles to kilometers, and 30°C to °F.",
    ":material/add_task: Tasks": "Add a task 'Prepare MCP demo slides' with high priority, then show my open tasks.",
    ":material/wb_sunny: Briefing": "Give me a daily briefing for London.",
    ":material/casino: Dice": "Roll two 20-sided dice for me.",
}

st.set_page_config(page_title="MCP Live Toolkit", page_icon=":material/handyman:", layout="wide")


# ── Server process control (the sidebar "launch button") ───────────────────
# This does nothing magic — it runs the exact same command the README tells
# you to type in a terminal (`python server/mcp_server.py`), just from
# inside this app, with output redirected to a log file so you can watch it
# without a second window. The server has no idea it was started this way.

def _server_owned_by_this_app() -> bool:
    proc = st.session_state.get("server_proc")
    return proc is not None and proc.poll() is None


def launch_server_in_background():
    SERVER_LOG.parent.mkdir(parents=True, exist_ok=True)
    log_file = open(SERVER_LOG, "a", buffering=1, encoding="utf-8")
    log_file.write("\n" + "=" * 72 + f"\nLaunched from the Streamlit app at {datetime.now().isoformat()}\n")
    creationflags = subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0
    proc = subprocess.Popen(
        [sys.executable, str(SERVER_SCRIPT)],
        stdout=log_file, stderr=subprocess.STDOUT,
        cwd=str(PROJECT_ROOT), creationflags=creationflags,
    )
    st.session_state.server_proc = proc


def stop_owned_server():
    proc = st.session_state.get("server_proc")
    if proc and proc.poll() is None:
        proc.terminate()
        try:
            proc.wait(timeout=3)
        except subprocess.TimeoutExpired:
            proc.kill()
    st.session_state.server_proc = None


def tail_server_log(lines: int = 40) -> str:
    if not SERVER_LOG.exists():
        return "(no log yet — launch the server to see its output here)"
    text = SERVER_LOG.read_text(encoding="utf-8", errors="replace").splitlines()
    return "\n".join(text[-lines:]) or "(empty)"


# ── Async <-> Streamlit bridge ──────────────────────────────────────────────
# The MCP SDK is async (talking over HTTP is I/O). Streamlit's script model
# is synchronous and re-runs top-to-bottom on every interaction, so each
# user action below opens ONE fresh `asyncio.run(...)` call that does
# everything that action needs, then closes the session. Simple over
# clever: a beginner reading this can trace exactly one request at a time.

async def _list_everything_async():
    async with connect_to_server() as session:
        tools = (await session.list_tools()).tools
        resources = (await session.list_resources()).resources
        templates_result = await session.list_resource_templates()
        templates = field(templates_result, "resource_templates", "resourceTemplates", default=[])
        prompts = (await session.list_prompts()).prompts
        return tools, resources, templates, prompts


async def _call_tool_async(name: str, args: dict):
    async with connect_to_server() as session:
        result = await session.call_tool(name, args)
        return tool_result_to_value(result), tool_call_is_error(result)


async def _read_resource_async(uri: str):
    async with connect_to_server() as session:
        result = await session.read_resource(uri)
        texts = [c.text for c in result.contents if hasattr(c, "text")]
        return "\n".join(texts)


async def _get_prompt_async(name: str, args: dict):
    async with connect_to_server() as session:
        result = await session.get_prompt(name, args)
        return "\n".join(m.content.text for m in result.messages if hasattr(m.content, "text"))


def _plain(message) -> dict:
    if hasattr(message, "model_dump"):
        return message.model_dump(exclude_none=True)
    return message


async def _run_agent_async(client, model, messages, temperature, max_tokens, extra_args, max_steps, on_step=None):
    """
    The MCP-backed agent loop. Step 3 below is the one line that matters:
    the tool doesn't run in this process — `session.call_tool(...)` sends it
    over HTTP to the standalone server and waits for its answer.

      1. Open ONE MCP session and ask the server what it can do right now —
         `list_tools()`. Live discovery: nothing is hardcoded here.
      2. Translate those MCP tool schemas into OpenAI's `tools=[...]` format
         and send them + the conversation to the model.
      3. If the model requests a tool call, execute it ON THE SERVER via
         `session.call_tool(name, args)` and feed the (JSON) result back.
      4. Repeat until the model answers in plain text, or `max_steps` is hit.

    `on_step`, if given, is called with a short human-readable string at
    every one of those moments — this is what makes the client's existence
    and its two separate conversations (with the LLM, with the server)
    visible in real time instead of buried in a trace you inspect after
    the fact. See app.py's chat handler for how it's wired into a live
    `st.status()` box.
    """
    def emit(text: str) -> None:
        if on_step:
            on_step(text)

    trace = []
    working = list(messages)

    emit(":material/cable: Creating an MCP **client** session…")
    async with connect_to_server() as session:
        emit(f":material/lan: **Client → Server** — connected over HTTP to `{MCP_SERVER_URL}`")
        tools_result = await session.list_tools()
        mcp_tools = tools_result.tools
        openai_tools = [mcp_tool_to_openai_schema(t) for t in mcp_tools]
        trace.append({
            "kind": "mcp_call", "op": "list_tools",
            "request": {}, "response": [t.name for t in mcp_tools],
        })
        emit(f":material/build: **Server → Client** — discovered {len(mcp_tools)} tool(s): `{'`, `'.join(t.name for t in mcp_tools)}`")

        for step_num in range(max_steps):
            request = {
                "model": model,
                "messages": [_plain(m) for m in working],
                "tools": [t["function"]["name"] for t in openai_tools],
                "temperature": temperature, "max_tokens": max_tokens, **extra_args,
            }
            emit(f":material/psychology: **Client → LLM** — sending the conversation + {len(openai_tools)} tool schema(s) to `{model}`, asking it to pick one…")
            response = client.chat.completions.create(
                model=model, messages=working, tools=openai_tools,
                temperature=temperature, max_tokens=max_tokens, **extra_args,
            )
            message = response.choices[0].message
            trace.append({"kind": "llm_call", "request": request, "response": _plain(message)})
            working.append(message)

            if not message.tool_calls:
                emit(":material/check_circle: **LLM → Client** — answered directly, no tool needed. Closing the MCP session.")
                return message.content or "", trace, [t.name for t in mcp_tools]

            names = ", ".join(tc.function.name for tc in message.tool_calls)
            emit(f":material/target: **LLM → Client** — selected tool(s): `{names}`")

            for tool_call in message.tool_calls:
                name = tool_call.function.name
                try:
                    args = json.loads(tool_call.function.arguments or "{}")
                except json.JSONDecodeError:
                    args = {}
                emit(f":material/upload: **Client → Server** — `session.call_tool(\"{name}\", {json.dumps(args, ensure_ascii=False)})` over HTTP")
                result = await session.call_tool(name, args)
                value = tool_result_to_value(result)
                is_error = tool_call_is_error(result)
                trace.append({
                    "kind": "mcp_call", "op": "call_tool", "tool_name": name,
                    "arguments": args, "response": value, "is_error": is_error,
                })
                short = json.dumps(value, default=str, ensure_ascii=False)
                short = short if len(short) <= 160 else short[:160] + "…"
                emit(f"{':material/error:' if is_error else ':material/download:'} **Server → Client** — result: `{short}`")
                working.append({"role": "tool", "tool_call_id": tool_call.id, "content": json.dumps(value)})

        emit(":material/warning: Hit the agent-step safety cap — stopping here.")
        return f"Hit the {max_steps}-step safety cap for this demo — try rephrasing your question.", trace, [t.name for t in mcp_tools]


def run_async(coro):
    """
    `asyncio.run(...)` plus one polish pass: the MCP client manages its HTTP
    connection with an anyio task group, so ANY exception raised while a
    session is open (server offline, a bad tool argument, a provider rate
    limit) surfaces as an opaque `ExceptionGroup` wrapping it, not the
    original error. Unwrap down to the real, useful message before it ever
    reaches an `st.error(...)`.
    """
    try:
        return asyncio.run(coro)
    except BaseExceptionGroup as eg:
        leaf = eg
        while isinstance(leaf, BaseExceptionGroup) and leaf.exceptions:
            leaf = leaf.exceptions[0]
        raise leaf from eg


def friendly_connection_error(e: Exception) -> str:
    return (
        f"Couldn't reach the MCP server at `{MCP_SERVER_URL}`.\n\n"
        f"**Start it first** — click **Launch** in the sidebar, or run this in a terminal:\n"
        f"```\ncd \"{PROJECT_REL_PATH}\"\npython server/mcp_server.py\n```\n\n"
        f"Underlying error: `{e}`"
    )


# ── LLM client (identical pattern to agent-workflow-demo / mcp-notes-demo) ──

@st.cache_resource
def get_client(base_url: str, api_key: str) -> OpenAI:
    return OpenAI(base_url=base_url, api_key=api_key)


@st.cache_data(ttl=30)
def list_models(base_url: str, api_key: str) -> list[str]:
    client = get_client(base_url, api_key)
    return sorted(m.id.removeprefix("models/") for m in client.models.list().data)


# ── Dynamic form: render input widgets straight from an MCP JSON schema ────
# This app never hand-writes "city: text input, value: number input"
# anywhere. Every field below comes from tool.input_schema, which the
# SERVER generated from its own function's type hints. Add a parameter to a
# tool on the server, and a matching field appears here automatically.

def render_dynamic_form(schema: dict, key_prefix: str) -> dict:
    props = (schema or {}).get("properties", {}) or {}
    required = set((schema or {}).get("required", []))
    values = {}
    if not props:
        st.caption("This tool takes no arguments.")
        return values
    for name, spec in props.items():
        label = f"`{name}`" + (" *" if name in required else "")
        help_text = spec.get("description", "")
        ptype = spec.get("type", "string")
        default = spec.get("default")
        widget_key = f"{key_prefix}_{name}"
        if ptype == "integer":
            values[name] = st.number_input(label, value=int(default) if default is not None else 0, step=1, help=help_text, key=widget_key)
        elif ptype == "number":
            values[name] = st.number_input(label, value=float(default) if default is not None else 0.0, help=help_text, key=widget_key)
        elif ptype == "boolean":
            values[name] = st.checkbox(label, value=bool(default) if default is not None else False, help=help_text, key=widget_key)
        else:
            values[name] = st.text_input(label, value=str(default) if default is not None else "", help=help_text, key=widget_key)
    return values


# ── Live activity log — the easy "yes, a client is really talking to both
# the server AND the LLM" proof. Rendered progressively while a chat request
# is in flight (see on_step below) and replayed identically, all at once,
# for past messages — same container, same look, live or not. ─────────────

def render_activity_log(lines: list[str], state: str = "complete"):
    label = lines[-1] if lines else "MCP client activity"
    with st.status(label, state=state, expanded=True):
        for line in lines:
            st.markdown(f"- {line}")


# ── Trace renderer ──────────────────────────────────────────────────────────

def render_trace(trace, title="Raw request/response JSON"):
    with st.expander(f":material/route: {title}"):
        for i, step in enumerate(trace):
            if step["kind"] == "llm_call":
                tool_calls = (step["response"] or {}).get("tool_calls")
                if tool_calls:
                    names = ", ".join(tc["function"]["name"] for tc in tool_calls)
                    st.markdown(f"**Step {i + 1} · :material/psychology: LLM call** — requested MCP tool(s): `{names}`")
                else:
                    st.markdown(f"**Step {i + 1} · :material/psychology: LLM call** — answered directly, no tool needed")
                tab_req, tab_res = st.tabs(["Request", "Response"])
                with tab_req:
                    st.code(json.dumps(step["request"], indent=2, default=str, ensure_ascii=False), language="json")
                with tab_res:
                    st.code(json.dumps(step["response"], indent=2, default=str, ensure_ascii=False), language="json")
            elif step["op"] == "list_tools":
                st.markdown(f"**Step {i + 1} · :material/lan: MCP protocol** — `session.list_tools()` over HTTP (discovers the tool menu live)")
                st.code(json.dumps(step["response"], indent=2), language="json")
            else:  # call_tool
                icon = TOOL_ICONS.get(step["tool_name"], ":material/build:")
                st.markdown(f"**Step {i + 1} · {icon} MCP protocol** — `session.call_tool(\"{step['tool_name']}\", ...)` on the SERVER process, over HTTP")
                tab_args, tab_res = st.tabs(["Arguments", "Result"])
                with tab_args:
                    st.code(json.dumps(step["arguments"], indent=2, ensure_ascii=False), language="json")
                with tab_res:
                    st.code(json.dumps(step["response"], indent=2, default=str, ensure_ascii=False), language="json")
            if i < len(trace) - 1:
                st.divider()


# ── Sidebar ──────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("### :material/auto_awesome: Dinesh AI Academy")
    st.caption("Day 4 · Agents & MCP — MCP server + client, live over HTTP")
    st.space("small")

    with st.container(border=True):
        st.markdown("**:material/dns: MCP server**")
        owned = _server_owned_by_this_app()
        reachable = owned or is_server_reachable()

        if reachable:
            how = "launched by this app" if owned else "running externally"
            st.badge(f"Online · {how}", icon=":material/check_circle:", color="green")
        else:
            st.badge("Offline", icon=":material/error:", color="red")

        st.caption(f"Endpoint: `{MCP_SERVER_URL}`")

        col_a, col_b = st.columns(2)
        with col_a:
            if st.button(":material/rocket_launch: Launch", width="stretch", disabled=reachable, key="launch_btn"):
                launch_server_in_background()
                st.rerun()
        with col_b:
            if st.button(":material/stop_circle: Stop", width="stretch", disabled=not owned, key="stop_btn"):
                stop_owned_server()
                st.rerun()

        if not reachable:
            st.caption("Or run it yourself in a terminal:")
            st.code(f'cd "{PROJECT_REL_PATH}"\npython server/mcp_server.py', language="bash")

        with st.expander("Server log", icon=":material/terminal:"):
            st.code(tail_server_log(), language="text")
            if st.button("Refresh log", icon=":material/refresh:", key="refresh_log_btn", width="stretch"):
                st.rerun()

    with st.container(border=True):
        st.markdown("**:material/cloud: Provider & model**")
        provider_name = st.segmented_control(
            "Provider", list(PROVIDERS), default="LM Studio (local)", required=True, label_visibility="collapsed"
        )
        provider = PROVIDERS[provider_name]

        if provider["needs_key"] and not provider["api_key"]:
            st.error(
                f"No API key found for {provider_name}. Add `GEMINI_API_KEY=...` to your "
                "`.env` file (get a free key at aistudio.google.com/apikey), then reload."
            )
            st.stop()

        client = get_client(provider["base_url"], provider["api_key"])

        try:
            all_models = list_models(provider["base_url"], provider["api_key"])
        except Exception:
            all_models = []

        if not all_models:
            if provider_name.startswith("LM Studio"):
                st.error(
                    f"Can't reach a local LLM server at `{provider['base_url']}`.\n\n"
                    "Start LM Studio, load a **tool-calling capable** chat model, click "
                    "**Start Server**, then reload this page."
                )
            else:
                st.error("Couldn't list Gemini models. Check that your API key is valid, then reload.")
            st.stop()

        st.badge(f"Connected · {len(all_models)} model(s)", icon=":material/check_circle:", color="green")

        if provider_name.startswith("Gemini"):
            chat_models = sorted(m for m in all_models if "embed" not in m and not any(x in m for x in GEMINI_EXCLUDE))
        else:
            chat_models = [m for m in all_models if "embed" not in m.lower()] or all_models

        if not chat_models:
            st.error(f"{provider_name} has no usable chat models loaded/available.")
            st.stop()

        default_model = provider["default_model"]
        default_chat = default_model if default_model in chat_models else chat_models[0]
        model = st.selectbox("Chat model", chat_models, index=chat_models.index(default_chat))

        with st.expander("Advanced", icon=":material/tune:"):
            temperature = st.slider("Temperature", 0.0, 1.5, 0.3, 0.1)
            max_tokens = st.slider("Max tokens", 50, 2000, 500, 50)
            max_steps = st.slider("Max agent steps (safety cap)", 2, 8, DEFAULT_MAX_STEPS, 1)

    extra_args = {"reasoning_effort": GEMINI_REASONING_EFFORT} if provider_name.startswith("Gemini") else {}

    with st.container(border=True):
        st.markdown("**:material/lan: Architecture**")
        st.caption("This Streamlit app is the **Host**.")
        st.markdown(
            "```text\n"
            "HOST (this app)\n"
            "  └─ CLIENT  (client/mcp_client.py)\n"
            "       │  MCP protocol, streamable-HTTP\n"
            "       ▼\n"
            f"     SERVER  (its OWN process, port {MCP_SERVER_URL.split(':')[-1].split('/')[0]})\n"
            "       — launched separately, keeps running —\n"
            "```"
        )
        st.caption("Stop the server, keep chatting: every tool call below will fail with a clear error until you start it again.")

    st.space("small")
    if st.button("Clear conversation", icon=":material/mop:", width="stretch"):
        st.session_state.messages = []
        st.rerun()


# ── Session state ────────────────────────────────────────────────────────
if "messages" not in st.session_state:
    st.session_state.messages = []


# ── Header ───────────────────────────────────────────────────────────────
st.title(":material/handyman: MCP Live Toolkit")
st.caption(f"A real MCP client talking to a real, separately-launched MCP server over HTTP. Provider: {provider_name} · `{model}`")

with st.expander(":material/menu_book: Host, Client, Server — what am I looking at?"):
    st.markdown(
        "| | What it is | In this app |\n"
        "|---|---|---|\n"
        "| **Host** | The application a human actually uses | This Streamlit app |\n"
        "| **Client** | Lives in the host, one dedicated connection to one server | `client/mcp_client.py` |\n"
        "| **Server** | A standalone process, its own lifecycle, exposing tools/resources/prompts over HTTP | `server/mcp_server.py` |\n\n"
        "**The test that proves it's a real protocol, not a shortcut:** the *Toolkit Explorer* tab below calls the "
        "server directly — **no LLM involved at all.** Only the *Chat* tab adds an LLM, and even then the LLM only "
        "ever *decides* which tool to call; the MCP client is still what actually calls it, over the network, on a "
        "process you launched yourself and can watch running in the sidebar's server log."
    )

tab_explorer, tab_chat = st.tabs([":material/lan: Toolkit Explorer (no LLM)", ":material/smart_toy: Chat (LLM + MCP)"])


# ── Tab 1: Toolkit Explorer — raw protocol, zero LLM ────────────────────
with tab_explorer:
    st.caption(
        "Everything below is discovered LIVE from the server via `list_tools()` / `list_resources()` / "
        "`list_prompts()` — nothing is hardcoded in this app. Call anything directly and watch the raw result."
    )

    if st.button(":material/refresh: Discover server capabilities", type="primary"):
        try:
            with st.spinner("Connecting to the MCP server over HTTP…"):
                tools, resources, templates, prompts = run_async(_list_everything_async())
            st.session_state.mcp_tools = tools
            st.session_state.mcp_resources = resources
            st.session_state.mcp_templates = templates
            st.session_state.mcp_prompts = prompts
        except Exception as e:
            st.error(friendly_connection_error(e))

    if "mcp_tools" not in st.session_state:
        st.info("Click **Discover server capabilities** to connect and see what this server exposes.", icon=":material/info:")
    else:
        col_tools, col_resources, col_prompts = st.columns(3)

        with col_tools:
            st.markdown("**:material/build: Tools**")
            tools = st.session_state.mcp_tools
            tool_names = [t.name for t in tools]
            picked = st.selectbox("Pick a tool", tool_names, key="explorer_tool")
            tool = next(t for t in tools if t.name == picked)
            st.caption(tool.description or "_no description_")
            args = render_dynamic_form(field(tool, "input_schema", "inputSchema"), f"tool_{picked}")
            if st.button("Call tool", icon=":material/play_arrow:", key="call_tool_btn"):
                try:
                    with st.spinner(f"session.call_tool('{picked}', ...)"):
                        value, is_error = run_async(_call_tool_async(picked, args))
                    (st.error if is_error else st.success)(f"Result from `{picked}`:")
                    st.code(json.dumps(value, indent=2, default=str, ensure_ascii=False), language="json")
                except Exception as e:
                    st.error(friendly_connection_error(e))

        with col_resources:
            st.markdown("**:material/description: Resources**")
            st.caption("Read-only data, fetched by URI — no 'action', no side effects.")
            static_uris = [r.uri for r in st.session_state.mcp_resources]
            template_uris = [t.uri_template for t in st.session_state.mcp_templates]
            st.caption("Static: " + (", ".join(f"`{u}`" for u in static_uris) or "none"))
            st.caption("Template: " + (", ".join(f"`{u}`" for u in template_uris) or "none"))
            resource_uri = st.text_input("URI to read", value="task://all", key="explorer_resource_uri")
            if st.button("Read resource", icon=":material/download:", key="read_resource_btn"):
                try:
                    with st.spinner(f"session.read_resource('{resource_uri}')"):
                        text = run_async(_read_resource_async(resource_uri))
                    st.text_area("Content", text, height=140, key="resource_result")
                except Exception as e:
                    st.error(friendly_connection_error(e))

        with col_prompts:
            st.markdown("**:material/chat_bubble: Prompts**")
            st.caption("Reusable, parameterized prompt templates the server owns.")
            prompts = st.session_state.mcp_prompts
            if prompts:
                prompt_names = [p.name for p in prompts]
                picked_prompt = st.selectbox("Pick a prompt", prompt_names, key="explorer_prompt")
                prompt_obj = next(p for p in prompts if p.name == picked_prompt)
                st.caption(prompt_obj.description or "_no description_")
                prompt_schema = {
                    "properties": {a.name: {"type": "string", "description": a.description} for a in (prompt_obj.arguments or [])},
                    "required": [a.name for a in (prompt_obj.arguments or []) if a.required],
                }
                p_args = render_dynamic_form(prompt_schema, f"prompt_{picked_prompt}")
                if st.button("Get prompt", icon=":material/text_snippet:", key="get_prompt_btn"):
                    try:
                        with st.spinner(f"session.get_prompt('{picked_prompt}', ...)"):
                            text = run_async(_get_prompt_async(picked_prompt, p_args))
                        st.text_area("Generated prompt text", text, height=140, key="prompt_result")
                    except Exception as e:
                        st.error(friendly_connection_error(e))
            else:
                st.caption("No prompts exposed by this server.")


# ── Tab 2: Chat — LLM decides, MCP client executes ──────────────────────
with tab_chat:
    st.caption(
        "Same agent loop as Day 4's `agent-workflow-demo` — the model still only *decides* which tool to call. "
        "The difference: execution now happens over the MCP protocol, on a server you launched yourself."
    )

    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.write(message["content"])
            if message.get("live_log"):
                render_activity_log(message["live_log"])
            if message.get("trace"):
                render_trace(message["trace"])

    prompt = None
    if not st.session_state.messages:
        selected = st.pills("Try asking:", list(SUGGESTIONS.keys()), label_visibility="collapsed")
        if selected:
            prompt = SUGGESTIONS[selected]

    prompt = st.chat_input("Type a message", submit_mode="disable") or prompt

    if prompt:
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.write(prompt)

        history = [
            {"role": m["role"], "content": m["content"]}
            for m in st.session_state.messages[:-1]
            if m["role"] in ("user", "assistant")
        ]
        request_messages = [{"role": "system", "content": SYSTEM_PROMPT_AGENT}, *history, {"role": "user", "content": prompt}]

        with st.chat_message("assistant"):
            live_log: list[str] = []
            status = st.status(":material/cable: Creating an MCP client session…", state="running", expanded=True)

            def on_step(msg: str) -> None:
                live_log.append(msg)
                status.update(label=msg)
                status.markdown(f"- {msg}")

            try:
                text, trace, discovered = run_async(
                    _run_agent_async(client, model, request_messages, temperature, max_tokens, extra_args, max_steps, on_step=on_step)
                )
                status.update(label=f":material/check_circle: Done · {len(discovered)} tool(s) discovered from the server", state="complete", expanded=True)
                st.write(text)
            except Exception as e:
                status.update(label=":material/error: Failed", state="error", expanded=True)
                st.error(
                    friendly_connection_error(e) if not reachable else
                    f"Request failed: {e}\n\n"
                    "This model may not support function calling — try a Llama 3.1+/Qwen/Gemma instruct model "
                    "in LM Studio, or switch providers."
                )
                st.stop()

            render_trace(trace)

        st.session_state.messages.append({"role": "assistant", "content": text, "trace": trace, "live_log": live_log})
