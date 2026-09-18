"""
Premium Agent Studio — Chat App (Dinesh AI Academy, Day 4 · Agents & MCP)

This app does NOT contain the agent. It CONSUMES it. Every line that
decides which tool to call, talks to Gemini, or talks to the MCP server
lives in agent/agent.py — a plain Python module with no Streamlit import
anywhere in it, independently runnable on its own (`python agent/agent.py`).
This file's only job is to be a nice place to *use* that agent: a chat UI
that turns each `AgentEvent` the agent yields into something on screen.

    user types  ->  app.py appends to st.session_state.messages
                 ->  app.py calls Agent.run(history)
                 ->  agent.py streams AgentEvents: status / tool_call /
                     tool_result / token / usage / final / error
                 ->  app.py renders each event live, then stores the
                     finished turn back into session_state

Layers, in the order they appear below:
    1. Configuration & secrets
    2. Agent client layer (thin bridge: async generator -> sync generator)
    3. State management
    4. UI helpers (rendering one AgentEvent, one chat turn)
    5. Sidebar
    6. Orchestration (the chat loop itself)
"""

from __future__ import annotations

import asyncio
import os
import queue
import subprocess
import sys
import threading
from datetime import datetime
from pathlib import Path

import streamlit as st
from dotenv import load_dotenv

sys.path.insert(0, str(Path(__file__).resolve().parent))
from agent.agent import Agent, AgentEvent, DEFAULT_MODEL, DEFAULT_SYSTEM_PROMPT
from client.mcp_client import MCP_SERVER_URL, is_server_reachable

load_dotenv()


# ── 1. Configuration & secrets ──────────────────────────────────────────

PROJECT_ROOT = Path(__file__).resolve().parent
REPO_ROOT = PROJECT_ROOT.parents[2]  # .../Projects/premium-agent-studio -> .../Day 4 .../ -> repo root
PROJECT_REL_PATH = PROJECT_ROOT.relative_to(REPO_ROOT).as_posix()
SERVER_SCRIPT = PROJECT_ROOT / "server" / "mcp_server.py"
SERVER_LOG = PROJECT_ROOT / "server" / ".server.log"

API_KEY = os.getenv("GAISTUDIO_API_KEY") or os.getenv("GEMINI_API_KEY")

CANDIDATE_MODELS = ["gemini-3.5-flash-lite", "gemini-3.5-flash", "gemini-3.6-flash", "gemini-3.5-pro"]

TOOL_ICONS = {
    "get_current_time": ":material/schedule:",
    "calculate": ":material/calculate:",
    "get_weather": ":material/partly_cloudy_day:",
    "convert_units": ":material/swap_horiz:",
    "add_task": ":material/add_task:",
    "list_tasks": ":material/checklist:",
    "complete_task": ":material/task_alt:",
}

SUGGESTIONS = {
    ":material/partly_cloudy_day: Weather": "What's the weather in Paris right now?",
    ":material/schedule: World clock": "What time is it in Tokyo and in New York right now?",
    ":material/calculate: Math": "What's 18% of 245.50?",
    ":material/swap_horiz: Convert": "Convert 5 miles to kilometers, and 30°C to °F.",
    ":material/add_task: Tasks": "Add a task 'Prepare demo slides' with high priority, then show my open tasks.",
}

st.set_page_config(page_title="Premium Agent Studio", page_icon=":material/auto_awesome:", layout="wide")


# ── 2. Agent client layer ───────────────────────────────────────────────
# The agent's public API (`Agent.run`) is an ASYNC generator — the natural
# shape for something that streams tokens while awaiting network I/O
# (Gemini, the MCP server). Streamlit's script model is synchronous and
# re-runs top to bottom, so this bridges the two: a background thread runs
# the asyncio event loop and pushes every AgentEvent into a thread-safe
# queue; the main Streamlit thread just pulls from that queue like any
# ordinary (synchronous) generator, so the UI can render events as they
# arrive instead of waiting for the whole reply to finish first.

def stream_agent_turn(agent: Agent, history: list[dict]):
    event_queue: queue.Queue = queue.Queue()
    _DONE = object()

    def worker() -> None:
        async def consume() -> None:
            async for event in agent.run(history):
                event_queue.put(event)

        try:
            asyncio.run(consume())
        except Exception as e:  # a bug in the bridge itself, not the agent
            event_queue.put(AgentEvent("error", str(e)))
        finally:
            event_queue.put(_DONE)

    threading.Thread(target=worker, daemon=True).start()

    while True:
        item = event_queue.get()
        if item is _DONE:
            return
        yield item


@st.cache_resource(show_spinner=False)
def get_agent(model: str, temperature: float, max_output_tokens: int, system_prompt: str, max_steps: int) -> Agent:
    # Cached on its exact settings tuple, so changing any sidebar slider
    # transparently builds a fresh Agent instead of reusing a stale one.
    return Agent(
        model=model,
        temperature=temperature,
        max_output_tokens=max_output_tokens,
        system_prompt=system_prompt,
        max_steps=max_steps,
        api_key=API_KEY,
    )


# ── MCP server process control (sidebar "Launch" button) ───────────────
# Runs the exact same command the README tells you to type in a terminal —
# just from inside this app, with output redirected to a log file.

def _server_owned_by_this_app() -> bool:
    proc = st.session_state.get("server_proc")
    return proc is not None and proc.poll() is None


def launch_server_in_background() -> None:
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


def stop_owned_server() -> None:
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


# ── 3. State management ─────────────────────────────────────────────────

if "messages" not in st.session_state:
    st.session_state.messages = []
if "total_tokens" not in st.session_state:
    st.session_state.total_tokens = {"prompt": 0, "completion": 0, "total": 0}


# ── 4. UI helpers ────────────────────────────────────────────────────────

def render_activity_log(lines: list[str], state: str = "complete"):
    label = lines[-1] if lines else "Agent activity"
    with st.status(label, state=state, expanded=False):
        for line in lines:
            st.markdown(f"- {line}")


def friendly_error(message: str) -> str:
    if "mcp" in message.lower() or "connect" in message.lower() or "refused" in message.lower():
        return (
            f"Couldn't reach the MCP tool server at `{MCP_SERVER_URL}`.\n\n"
            f"**Start it first** — click **Launch** in the sidebar, or run this in a terminal:\n"
            f"```\ncd \"{PROJECT_REL_PATH}\"\npython server/mcp_server.py\n```\n\n"
            f"Underlying error: `{message}`"
        )
    return f"The agent hit an error: `{message}`"


# ── 5. Sidebar ───────────────────────────────────────────────────────────

with st.sidebar:
    st.markdown("### :material/auto_awesome: Dinesh AI Academy")
    st.caption("Day 4 · Agents & MCP — an independent agent, consumed by this app")
    st.space("small")

    with st.container(border=True):
        st.markdown("**:material/dns: MCP tool server**")
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

    if not API_KEY:
        st.error(
            "No Gemini API key found. Add `GAISTUDIO_API_KEY=...` to your `.env` file "
            "(get a free key at aistudio.google.com/apikey), then reload."
        )
        st.stop()

    with st.container(border=True):
        st.markdown("**:material/psychology: Agent settings**")
        model = st.selectbox("Model", CANDIDATE_MODELS, index=0)
        temperature = st.slider("Temperature", 0.0, 1.5, 0.4, 0.1)
        max_tokens = st.slider("Max output tokens", 128, 4096, 1024, 128)
        max_steps = st.slider("Max agent steps (safety cap)", 2, 10, 6, 1)
        system_prompt = st.text_area("System prompt", value=DEFAULT_SYSTEM_PROMPT, height=140)

    with st.container(border=True):
        st.markdown("**:material/monitoring: Session token usage**")
        usage = st.session_state.total_tokens
        c1, c2, c3 = st.columns(3)
        c1.metric("Prompt", usage["prompt"])
        c2.metric("Completion", usage["completion"])
        c3.metric("Total", usage["total"])

    with st.container(border=True):
        st.markdown("**:material/lan: Architecture**")
        st.markdown(
            "```text\n"
            "app.py (HOST — this Streamlit app)\n"
            "  └─ agent/agent.py   (the INDEPENDENT AGENT)\n"
            "       │  Gemini function calling, streamed\n"
            "       ▼\n"
            "     client/mcp_client.py  (MCP protocol client)\n"
            "       │  streamable-HTTP\n"
            "       ▼\n"
            f"     server/mcp_server.py   (its OWN process, port {MCP_SERVER_URL.split(':')[-1].split('/')[0]})\n"
            "```"
        )
        st.caption("Run the agent with zero UI at all: `python agent/agent.py` in a terminal.")

    st.space("small")
    if st.button("Clear conversation", icon=":material/mop:", width="stretch"):
        st.session_state.messages = []
        st.session_state.total_tokens = {"prompt": 0, "completion": 0, "total": 0}
        st.rerun()


# ── Header ───────────────────────────────────────────────────────────────

st.title(":material/auto_awesome: Premium Agent Studio")
st.caption(f"A Streamlit app consuming an independent, MCP-tool-using Gemini agent · `{model}`")

with st.expander(":material/menu_book: What am I looking at?"):
    st.markdown(
        "This app never decides which tool to call, and never talks to Gemini directly — "
        "**`agent/agent.py`** does both, and it works with or without this app: try "
        "`python agent/agent.py` in a terminal for the exact same agent with a plain-text "
        "interface. This page is just a nicer way to *use* it — every step you see below "
        "(thinking, tool calls, tool results, the streamed answer) is one `AgentEvent` the "
        "agent yielded, rendered live."
    )


# ── 6. Orchestration ────────────────────────────────────────────────────

for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])
        if message.get("activity_log"):
            render_activity_log(message["activity_log"])

prompt = None
if not st.session_state.messages:
    st.info("Ask me anything to get started — I can check the time, weather, do math, convert units, and track tasks.", icon=":material/info:")
    selected = st.pills("Try asking:", list(SUGGESTIONS.keys()), label_visibility="collapsed")
    if selected:
        prompt = SUGGESTIONS[selected]

prompt = st.chat_input("Type a message", submit_mode="disable") or prompt

if prompt:
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    # LLMs are stateless — every turn re-sends the FULL conversation so far.
    history = [{"role": m["role"], "content": m["content"]} for m in st.session_state.messages]

    with st.chat_message("assistant"):
        text_placeholder = st.empty()
        text_placeholder.markdown(":material/hourglass_top: Thinking…")
        status_box = st.status("Starting agent…", state="running", expanded=True)

        agent = get_agent(model, temperature, max_tokens, system_prompt, max_steps)

        activity_log: list[str] = []
        accumulated_text = ""
        final_text = None
        error_message = None

        def log_line(line: str) -> None:
            activity_log.append(line)
            status_box.update(label=line)
            status_box.markdown(f"- {line}")

        for event in stream_agent_turn(agent, history):
            if event.kind == "status":
                log_line(event.data)
            elif event.kind == "tool_call":
                icon = TOOL_ICONS.get(event.data["name"], ":material/build:")
                log_line(f"{icon} Calling `{event.data['name']}` with `{event.data['args']}`")
            elif event.kind == "tool_result":
                icon = ":material/error:" if event.data["is_error"] else ":material/check_circle:"
                log_line(f"{icon} Result from `{event.data['name']}`: `{event.data['result']}`")
            elif event.kind == "token":
                accumulated_text += event.data
                text_placeholder.markdown(accumulated_text + "▌")
            elif event.kind == "final":
                final_text = event.data
            elif event.kind == "usage":
                st.session_state.total_tokens["prompt"] += event.data["prompt_tokens"]
                st.session_state.total_tokens["completion"] += event.data["completion_tokens"]
                st.session_state.total_tokens["total"] += event.data["total_tokens"]
            elif event.kind == "error":
                error_message = event.data

        display_text = accumulated_text or final_text or ""

        if error_message:
            status_box.update(label=":material/error: Failed", state="error", expanded=True)
            text_placeholder.empty()
            st.error(friendly_error(error_message))
            st.stop()

        status_box.update(label=":material/check_circle: Done", state="complete", expanded=False)
        text_placeholder.markdown(display_text or "_(no response)_")

    st.session_state.messages.append({"role": "assistant", "content": display_text, "activity_log": activity_log})
