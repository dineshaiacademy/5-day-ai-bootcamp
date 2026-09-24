"""Streamlit host for the MCP Expense Lab."""
from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

import pandas as pd
import streamlit as st
from dotenv import load_dotenv

PROJECT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(PROJECT_DIR))
from src.env_setup import ensure_env_file, save_env_value  # noqa: E402

created_env = ensure_env_file()
load_dotenv(PROJECT_DIR / ".env", override=False)

from client.mcp_client import (  # noqa: E402
    MCPServerUnavailable,
    MCP_SERVER_URL,
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
from src.llm import (  # noqa: E402
    DEFAULT_PROVIDER,
    FALLBACK_PROVIDER,
    GEMINI_NAME,
    LMSTUDIO_NAME,
    PROVIDERS,
    ProviderError,
    check_provider,
    list_models,
    run_agent_with_fallback,
)

st.set_page_config(page_title="MCP Expense Lab", page_icon="💸", layout="wide")

if created_env and not st.session_state.get("env_toast_shown"):
    st.toast("Created .env — add your GEMINI_API_KEY in the sidebar")
    st.session_state.env_toast_shown = True

for key, value in {
    "provider": DEFAULT_PROVIDER,
    "model_gemini": PROVIDERS[GEMINI_NAME]["default_model"],
    "model_lmstudio": PROVIDERS[LMSTUDIO_NAME]["default_model"],
    "auto_fallback": True,
    "messages": [],
}.items():
    st.session_state.setdefault(key, value)

@st.cache_data(ttl=300)
def cached_models(provider: str) -> list[str]:
    return list_models(provider)

@st.cache_data(ttl=30)
def cached_provider_status(provider: str) -> tuple[bool, str]:
    return check_provider(provider)

@st.cache_data(ttl=10)
def cached_mcp_ping() -> bool:
    return run_sync(ping())


def mcp_help() -> str:
    return (
        f"Couldn't reach the MCP server at `{MCP_SERVER_URL}`. Start it first with:\n\n"
        f"```text\ncd \"{PROJECT_DIR}\"\npython server/mcp_server.py\n```"
    )


def render_schema_form(schema: dict[str, Any] | None, prefix: str) -> dict[str, Any]:
    """Build widgets directly from an MCP JSON schema."""
    schema = schema or {}
    properties = schema.get("properties", {}) or {}
    required = set(schema.get("required", []) or [])
    values: dict[str, Any] = {}
    if not properties:
        st.caption("This tool takes no arguments.")
        return values
    for name, spec in properties.items():
        spec = spec or {}
        label = f"{name}{' *' if name in required else ''}"
        help_text = spec.get("description", "")
        widget_key = f"{prefix}_{name}"
        ptype = spec.get("type", "string")
        default = spec.get("default")
        if ptype == "integer":
            values[name] = st.number_input(label, value=int(default or 0), step=1, help=help_text, key=widget_key)
        elif ptype == "number":
            values[name] = st.number_input(label, value=float(default or 0.0), help=help_text, key=widget_key)
        elif ptype == "boolean":
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

with st.sidebar:
    st.markdown("### 💸 Smart Expense Tracker")
    st.caption("Day 4 · Agents & MCP — Host + Client + Server")
    st.markdown("### 🤖 LLM Provider")
    provider = st.radio("Provider", list(PROVIDERS), index=list(PROVIDERS).index(st.session_state.provider), horizontal=True)
    st.session_state.provider = provider
    ready, status = cached_provider_status(provider)
    st.caption(("✅ ready · " if ready else "❌ ") + status)

    models = cached_models(provider)
    model_key = "model_gemini" if provider == GEMINI_NAME else "model_lmstudio"
    remembered = st.session_state.get(model_key, models[0] if models else "")
    if remembered not in models and models:
        remembered = models[0]
        st.session_state[model_key] = remembered
    selected_model = st.selectbox("Model", models or [remembered], index=(models.index(remembered) if remembered in models else 0), key=f"select_{model_key}")
    st.session_state[model_key] = selected_model
    custom_model = st.text_input("…or type a custom model name", key=f"custom_{model_key}", placeholder="Optional")
    active_model = custom_model.strip() or selected_model
    st.markdown(f"**Using:** {provider} · `{active_model}`")
    if st.button("🔄 Refresh models", use_container_width=True):
        cached_models.clear()
        st.rerun()

    if provider == GEMINI_NAME:
        key_value = st.text_input("Gemini API key", type="password", placeholder="set" if __import__("os").getenv("GEMINI_API_KEY") else "not set", key="gemini_key_input")
        if st.button("💾 Save key to .env", use_container_width=True):
            if key_value.strip():
                save_env_value("GEMINI_API_KEY", key_value.strip())
                cached_models.clear()
                cached_provider_status.clear()
                st.rerun()
        if not __import__("os").getenv("GEMINI_API_KEY"):
            st.warning("Gemini needs an API key. Get one at [aistudio.google.com/apikey](https://aistudio.google.com/apikey).")
            if st.button("Switch to LM Studio", use_container_width=True):
                st.session_state.provider = LMSTUDIO_NAME
                st.rerun()
    st.session_state.auto_fallback = st.toggle("Auto-fallback to LM Studio if Gemini fails", value=st.session_state.auto_fallback)
    fallback_models = cached_models(LMSTUDIO_NAME)
    fallback_model = st.selectbox("Fallback LM Studio model", fallback_models, index=0, key="fallback_model")

    st.markdown("### 🔌 MCP Server")
    server_ok = cached_mcp_ping()
    st.markdown(("✅ Online" if server_ok else "❌ Offline") + f"  · `{MCP_SERVER_URL}`")
    if not server_ok:
        st.caption("Start the standalone server before using tools or chat.")
    st.markdown("---")
    max_steps = st.slider("Max agent steps", 1, 8, 5)
    if st.button("Clear chat", use_container_width=True):
        st.session_state.messages = []
        st.rerun()

st.title("💸 MCP Expense Lab")
st.caption(f"Smart Expense Tracker · Using {provider} · `{active_model}`")
tab_chat, tab_tools, tab_resources, tab_how = st.tabs(["💬 Agent Chat", "🧰 Tool Explorer", "📚 Resources & Prompts", "🏗️ How it works"])

with tab_chat:
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.write(message["content"])
            if message["role"] == "assistant":
                st.caption(f"answered by {message.get('provider', provider)} · {message.get('model', active_model)}")
                render_trace(message.get("trace", []))
    examples = ["Add 450 rupees for lunch today", "How much did I spend on travel?", "Convert my total spending to USD", "Delete expense 2 and show the new summary"]
    if not st.session_state.messages:
        st.markdown("**Try an example:**")
        cols = st.columns(2)
        for index, example in enumerate(examples):
            if cols[index % 2].button(example, use_container_width=True, key=f"example_{index}"):
                st.session_state.pending_prompt = example
    prompt = st.chat_input("Ask the expense assistant…") or st.session_state.pop("pending_prompt", None)
    if prompt:
        history = [{"role": item["role"], "content": item["content"]} for item in st.session_state.messages if item["role"] in ("user", "assistant")]
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.write(prompt)
        with st.chat_message("assistant"):
            try:
                result = run_agent_with_fallback(provider, active_model, prompt, history, max_steps=max_steps, auto_fallback=st.session_state.auto_fallback, fallback_model=fallback_model)
                st.write(result["text"])
                st.caption(f"answered by {result['provider']} · {result['model']}")
                render_trace(result.get("trace", []))
                if result.get("fell_back"):
                    st.warning(f"Gemini failed ({result['fallback_reason']}) — answered with LM Studio instead.")
                    if st.button("Stay on LM Studio", key="stay_lmstudio"):
                        st.session_state.provider = LMSTUDIO_NAME
                        st.rerun()
                st.session_state.messages.append({"role": "assistant", "content": result["text"], "trace": result.get("trace", []), "provider": result["provider"], "model": result["model"]})
            except MCPServerUnavailable:
                st.error(mcp_help())
            except ProviderError as exc:
                st.error(exc.reason)
                if not st.session_state.auto_fallback:
                    col1, col2 = st.columns(2)
                    if col1.button("🔁 Switch to LM Studio and retry", key="retry_lm"):
                        st.session_state.provider = LMSTUDIO_NAME
                        st.session_state.pending_prompt = prompt
                        st.rerun()
                    col2.button("Pick another model", key="pick_model")

with tab_tools:
    st.write("Discover and call MCP tools directly — no LLM is involved.")
    if st.button("Discover server tools", key="discover_tools") or "mcp_tools" not in st.session_state:
        discover()
    tools = st.session_state.get("mcp_tools", [])
    if tools:
        names = [tool.name for tool in tools]
        picked_name = st.selectbox("Pick a tool", names, key="picked_tool")
        picked = next(tool for tool in tools if tool.name == picked_name)
        st.write(field(picked, "description", default="") or "No description")
        schema = field(picked, "input_schema", "inputSchema", default={})
        with st.expander("Input schema"):
            st.json(schema)
        args = render_schema_form(schema, f"explorer_{picked_name}")
        if st.button("Call tool", type="primary", key="call_selected_tool"):
            try:
                result = run_sync(call_tool(picked_name, args))
                (st.success if result["ok"] else st.error)(result["text"])
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
            content = run_sync(read_resource(resource_uri))
            records = json.loads(content)
            st.dataframe(pd.DataFrame(records), use_container_width=True)
        except (MCPServerUnavailable, json.JSONDecodeError) as exc:
            st.error(mcp_help() if isinstance(exc, MCPServerUnavailable) else str(exc))
    else:
        st.info("Start the server and refresh to discover resources.")
    st.subheader("Prompts")
    if prompts:
        prompt_obj = prompts[0]
        prompt_args = {argument.name: st.text_input(argument.name, key=f"prompt_arg_{argument.name}") for argument in (getattr(prompt_obj, "arguments", None) or [])}
        if st.button("Render monthly report prompt", key="render_prompt"):
            try:
                st.code(run_sync(get_prompt(prompt_obj.name, prompt_args)))
            except MCPServerUnavailable:
                st.error(mcp_help())
    else:
        st.info("No prompts discovered yet.")

with tab_how:
    st.subheader("Host → Client → Server")
    st.code("HOST (Streamlit app)\n  │  LLM chooses a function\n  ▼\nCLIENT (client/mcp_client.py) ── streamable HTTP ──► SERVER (server/mcp_server.py)\n  │                                                   │\n  └──────────── tool result over MCP ◄───────────────┘", language="text")
    st.markdown("| Layer | Responsibility | File |\n|---|---|---|\n| **Host** | Chat UI, provider/model choice, history | `app.py` |\n| **Client** | MCP handshake, discovery, calls, schema conversion | `client/mcp_client.py` |\n| **Server** | In-memory expense tools, resource, prompt | `server/mcp_server.py` |")
    st.info("The LLM decides which tool to call; the MCP client executes it on the independent server process.")



