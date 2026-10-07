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
