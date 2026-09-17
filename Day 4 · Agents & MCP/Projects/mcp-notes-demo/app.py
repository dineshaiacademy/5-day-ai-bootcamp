"""
MCP Explorer & Chat — Live Demo (Dinesh AI Academy, Day 4)

What this app teaches — the same story as Learning/1-MCP_Server_Basics.ipynb,
now interactive and running against a REAL, separate MCP server process:

    Host     This Streamlit app — the application a human actually uses.
    Client   client/mcp_client.py — lives inside the host, speaks the MCP
             protocol on its behalf, one dedicated connection to ONE server.
    Server   server/mcp_server.py — a completely separate Python process.
             It has no idea an LLM, Streamlit, or even a human is involved —
             it just answers "what tools do you have?" and "run this one."

Two tabs, both talking to the SAME server, to make one point unmistakable —
                              MCP ≠ an LLM feature:

    1. MCP Explorer   No LLM anywhere. You pick a tool, resource, or prompt
                       from what the server reports it has (live — nothing
                       is hardcoded here), and call it directly. This is
                       exactly what `list_tools()` / `call_tool()` look like
                       to ANY host, LLM-powered or not.
    2. Chat (LLM+MCP)  The Day 4 payoff: an LLM agent loop (same shape as
                       Day 4's agent-workflow-demo) where the decision of
                       *which* tool to call still comes from the model —
                       only now the tool is *executed* over the MCP
                       protocol, on a separate process, instead of as a
                       local Python function call.

Provider is a second, independent choice: LM Studio (100% local, free) or
Gemini (cloud, free tier) — both speak the OpenAI-compatible wire format,
so the same agent-loop code drives either one.
"""

from __future__ import annotations

import asyncio
import json
import os
import sys
from pathlib import Path

import streamlit as st
from dotenv import load_dotenv
from openai import OpenAI

sys.path.insert(0, str(Path(__file__).resolve().parent))
from client.mcp_client import connect_to_server, mcp_tool_to_openai_schema, tool_result_to_value

load_dotenv()

# ── Config ───────────────────────────────────────────────────────────────

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
    "You are a helpful notes assistant. You have tools to save, list, search, and "
    "delete short study notes. Call a tool whenever the user asks you to do one of "
    "these things — never claim to have saved, found, or deleted a note unless you "
    "actually called the matching tool and it succeeded. If a question needs the "
    "result of one tool before you can do the next step, call them one after "
    "another rather than guessing. If no tool is needed, answer directly."
)

TOOL_ICONS = {
    "add_note": ":material/note_add:",
    "list_notes": ":material/list:",
    "search_notes": ":material/search:",
    "delete_note": ":material/delete:",
}

SUGGESTIONS = {
    ":material/note_add: Save one": "Save a note titled 'mcp' with the content: MCP standardizes how AI apps use external tools.",
    ":material/search: Search": "Search my notes for anything about 'protocol'.",
    ":material/list: List all": "What notes do I have saved?",
    ":material/compare_arrows: Chained": "Save a note titled 'todo' with content 'write the MCP README', then list all my notes.",
}

st.set_page_config(page_title="MCP Explorer & Chat", page_icon=":material/lan:", layout="wide")


# ── Async <-> Streamlit bridge ──────────────────────────────────────────────
# The MCP SDK is async (talking to a subprocess is I/O). Streamlit's script
# model is synchronous and re-runs top-to-bottom on every interaction, so
# each user action below opens ONE fresh `asyncio.run(...)` call that does
# everything that action needs, then lets the connection close. Simple over
# clever: a beginner reading this can trace exactly one request at a time.

async def _list_everything_async():
    async with connect_to_server() as session:
        tools = (await session.list_tools()).tools
        resources = (await session.list_resources()).resources
        templates = (await session.list_resource_templates()).resource_templates
        prompts = (await session.list_prompts()).prompts
        return tools, resources, templates, prompts


async def _call_tool_async(name: str, args: dict):
    async with connect_to_server() as session:
        result = await session.call_tool(name, args)
        return tool_result_to_value(result), result.is_error


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


async def _run_agent_async(client, model, messages, temperature, max_tokens, extra_args, max_steps):
    """
    The MCP-backed agent loop — same shape as Day 4's plain agent loop, with
    exactly one thing swapped out: step 3 below calls `session.call_tool(...)`
    over the MCP protocol instead of looking a function up in a local dict.

      1. Open ONE MCP session and ask the server what it can do right now —
         `list_tools()`. This is live discovery: no tool list is hardcoded
         anywhere in this file.
      2. Translate those MCP tool schemas into OpenAI's `tools=[...]` format
         and send them + the conversation to the model.
      3. If the model requests a tool call, execute it ON THE SERVER via
         `session.call_tool(name, args)` and feed the (JSON) result back.
      4. Repeat until the model answers in plain text, or `max_steps` is hit.
    """
    trace = []
    working = list(messages)

    async with connect_to_server() as session:
        tools_result = await session.list_tools()
        mcp_tools = tools_result.tools
        openai_tools = [mcp_tool_to_openai_schema(t) for t in mcp_tools]
        trace.append({
            "kind": "mcp_call", "op": "list_tools",
            "request": {}, "response": [t.name for t in mcp_tools],
        })

        for _ in range(max_steps):
            request = {
                "model": model,
                "messages": [_plain(m) for m in working],
                "tools": [t["function"]["name"] for t in openai_tools],
                "temperature": temperature, "max_tokens": max_tokens, **extra_args,
            }
            response = client.chat.completions.create(
                model=model, messages=working, tools=openai_tools,
                temperature=temperature, max_tokens=max_tokens, **extra_args,
            )
            message = response.choices[0].message
            trace.append({"kind": "llm_call", "request": request, "response": _plain(message)})
            working.append(message)

            if not message.tool_calls:
                return message.content or "", trace, [t.name for t in mcp_tools]

            for tool_call in message.tool_calls:
                name = tool_call.function.name
                try:
                    args = json.loads(tool_call.function.arguments or "{}")
                except json.JSONDecodeError:
                    args = {}
                result = await session.call_tool(name, args)
                value = tool_result_to_value(result)
                trace.append({
                    "kind": "mcp_call", "op": "call_tool", "tool_name": name,
                    "arguments": args, "response": value, "is_error": result.is_error,
                })
                working.append({"role": "tool", "tool_call_id": tool_call.id, "content": json.dumps(value)})

        return f"Hit the {max_steps}-step safety cap for this demo — try rephrasing your question.", trace, [t.name for t in mcp_tools]


def run_async(coro):
    """
    `asyncio.run(...)` plus one polish pass: the MCP client manages its
    subprocess connection with an anyio task group, so ANY exception raised
    while a session is open (a bad tool argument, a provider's rate limit,
    a network blip) surfaces as an opaque `ExceptionGroup` wrapping it,
    not the original error. Unwrap down to the real, useful message before
    it ever reaches an `st.error(...)`.
    """
    try:
        return asyncio.run(coro)
    except BaseExceptionGroup as eg:
        leaf = eg
        while isinstance(leaf, BaseExceptionGroup) and leaf.exceptions:
            leaf = leaf.exceptions[0]
        raise leaf from eg


# ── LLM client (identical pattern to agent-workflow-demo) ─────────────────

@st.cache_resource
def get_client(base_url: str, api_key: str) -> OpenAI:
    return OpenAI(base_url=base_url, api_key=api_key)


@st.cache_data(ttl=30)
def list_models(base_url: str, api_key: str) -> list[str]:
    client = get_client(base_url, api_key)
    return sorted(m.id.removeprefix("models/") for m in client.models.list().data)


# ── Dynamic form: render input widgets straight from an MCP JSON schema ────
# The point: this app never hand-writes "title: text input, content: text
# input" anywhere. Every field below comes from tool.input_schema, which the
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
        widget_key = f"{key_prefix}_{name}"
        if ptype == "integer":
            values[name] = st.number_input(label, value=0, step=1, help=help_text, key=widget_key)
        elif ptype == "number":
            values[name] = st.number_input(label, value=0.0, help=help_text, key=widget_key)
        elif ptype == "boolean":
            values[name] = st.checkbox(label, help=help_text, key=widget_key)
        else:
            values[name] = st.text_input(label, help=help_text, key=widget_key)
    return values


# ── Trace renderer ──────────────────────────────────────────────────────────

def render_trace(trace, title="How this was generated"):
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
                st.markdown(f"**Step {i + 1} · :material/lan: MCP protocol** — `session.list_tools()` (discovers the tool menu live)")
                st.code(json.dumps(step["response"], indent=2), language="json")
            else:  # call_tool
                icon = TOOL_ICONS.get(step["tool_name"], ":material/build:")
                st.markdown(f"**Step {i + 1} · {icon} MCP protocol** — `session.call_tool(\"{step['tool_name']}\", ...)` on the SERVER process")
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
    st.caption("Day 4 · Agents & MCP — MCP server + client, live")
    st.space("small")

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
        st.markdown("**:material/lan: MCP architecture**")
        st.caption("This Streamlit app is the **Host**.")
        st.markdown(
            "```text\n"
            "HOST (this app)\n"
            "  └─ CLIENT  (client/mcp_client.py)\n"
            "       │  MCP protocol, stdio transport\n"
            "       ▼\n"
            "     SERVER  (server/mcp_server.py)\n"
            "       — a separate Python process —\n"
            "```"
        )
        st.caption("The server is launched fresh for each action below — watch the trace panels to see exactly when.")

    st.space("small")
    if st.button("Clear conversation", icon=":material/mop:", width="stretch"):
        st.session_state.messages = []
        st.rerun()


# ── Session state ────────────────────────────────────────────────────────
if "messages" not in st.session_state:
    st.session_state.messages = []


# ── Header ───────────────────────────────────────────────────────────────
st.title(":material/lan: MCP Explorer & Chat")
st.caption(f"A real MCP client talking to a real, separate MCP server process. Provider: {provider_name} · `{model}`")

with st.expander(":material/menu_book: Host, Client, Server — what am I looking at?"):
    st.markdown(
        "| | What it is | In this app |\n"
        "|---|---|---|\n"
        "| **Host** | The application a human actually uses | This Streamlit app |\n"
        "| **Client** | Lives in the host, one dedicated connection to one server | `client/mcp_client.py` |\n"
        "| **Server** | A standalone process exposing tools/resources/prompts | `server/mcp_server.py` |\n\n"
        "**The test that proves it's a real protocol, not a shortcut:** the *MCP Explorer* tab below calls the "
        "server directly — **no LLM involved at all.** Only the *Chat* tab adds an LLM, and even then, the LLM "
        "only ever *decides* which tool to call; the MCP client is still what actually calls it."
    )

tab_explorer, tab_chat = st.tabs([":material/lan: MCP Explorer (no LLM)", ":material/smart_toy: Chat (LLM + MCP)"])


# ── Tab 1: MCP Explorer — raw protocol, zero LLM ────────────────────────
with tab_explorer:
    st.caption(
        "Everything below is discovered LIVE from the server via `list_tools()` / `list_resources()` / "
        "`list_prompts()` — nothing is hardcoded in this app. Call anything directly and watch the raw result."
    )

    if st.button(":material/refresh: Discover server capabilities", type="primary"):
        try:
            with st.spinner("Connecting to the MCP server…"):
                tools, resources, templates, prompts = run_async(_list_everything_async())
            st.session_state.mcp_tools = tools
            st.session_state.mcp_resources = resources
            st.session_state.mcp_templates = templates
            st.session_state.mcp_prompts = prompts
        except Exception as e:
            st.error(f"Couldn't connect to the MCP server: {e}")

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
            args = render_dynamic_form(tool.input_schema, f"tool_{picked}")
            if st.button("Call tool", icon=":material/play_arrow:", key="call_tool_btn"):
                try:
                    with st.spinner(f"session.call_tool('{picked}', ...)"):
                        value, is_error = run_async(_call_tool_async(picked, args))
                    (st.error if is_error else st.success)(f"Result from `{picked}`:")
                    st.code(json.dumps(value, indent=2, default=str, ensure_ascii=False), language="json")
                except Exception as e:
                    st.error(f"Tool call failed: {e}")

        with col_resources:
            st.markdown("**:material/description: Resources**")
            st.caption("Read-only data, fetched by URI — no 'action', no side effects.")
            static_uris = [r.uri for r in st.session_state.mcp_resources]
            template_uris = [t.uri_template for t in st.session_state.mcp_templates]
            st.caption("Static: " + (", ".join(f"`{u}`" for u in static_uris) or "none"))
            st.caption("Template: " + (", ".join(f"`{u}`" for u in template_uris) or "none"))
            resource_uri = st.text_input("URI to read", value="note://all", key="explorer_resource_uri")
            if st.button("Read resource", icon=":material/download:", key="read_resource_btn"):
                try:
                    with st.spinner(f"session.read_resource('{resource_uri}')"):
                        text = run_async(_read_resource_async(resource_uri))
                    st.text_area("Content", text, height=140, key="resource_result")
                except Exception as e:
                    st.error(f"Reading resource failed: {e}")

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
                        st.error(f"Getting prompt failed: {e}")
            else:
                st.caption("No prompts exposed by this server.")


# ── Tab 2: Chat — LLM decides, MCP client executes ──────────────────────
with tab_chat:
    st.caption(
        "Same agent loop as Day 4's `agent-workflow-demo` — the model still only *decides* which tool to call. "
        "The difference: execution now happens over the MCP protocol, on a separate server process."
    )

    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.write(message["content"])
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
            try:
                with st.status("Connecting to the MCP server and running the agent loop…", type="step") as status:
                    text, trace, discovered = run_async(
                        _run_agent_async(client, model, request_messages, temperature, max_tokens, extra_args, max_steps)
                    )
                    status.update(label=f"Done · {len(discovered)} tool(s) discovered from the server", state="complete")
                st.write(text)
            except Exception as e:
                st.error(
                    f"Request failed: {e}\n\n"
                    "This model may not support function calling — try a Llama 3.1+/Qwen/Gemma instruct model "
                    "in LM Studio, or switch providers."
                )
                st.stop()

            render_trace(trace)

        st.session_state.messages.append({"role": "assistant", "content": text, "trace": trace})
