# Where and How the Client Is Used in the Streamlit App

**Dinesh AI Academy · Day 4 — Agents & MCP · MCP Live Toolkit**

This is the companion piece to
[HOW_THE_CLIENT_CALLS_THE_SERVER.md](HOW_THE_CLIENT_CALLS_THE_SERVER.md)
(which explains the mechanics of one call) — this one maps every place
`client/mcp_client.py` actually gets touched inside [app.py](app.py),
in order of how the app is structured.

## 1. The import — app.py, top of file

```python
from client.mcp_client import (
    MCP_SERVER_URL, connect_to_server, field,
    is_server_reachable, mcp_tool_to_openai_schema,
    tool_call_is_error, tool_result_to_value,
)
```

Everything the app knows about MCP comes through these seven names.
`app.py` never imports anything from `server/` — it only knows the
client module.

## 2. Four thin async wrappers — one per MCP operation

These are the actual call sites. Each one is a tiny async function whose
whole body is `connect_to_server()` + one session method:

| Function | What it does | Triggered by |
|---|---|---|
| `_list_everything_async()` | `list_tools()`, `list_resources()`, `list_resource_templates()`, `list_prompts()` | **Discover server capabilities** button, Toolkit Explorer tab |
| `_call_tool_async(name, args)` | `call_tool(name, args)` | **Call tool** button, Toolkit Explorer tab |
| `_read_resource_async(uri)` | `read_resource(uri)` | **Read resource** button, Toolkit Explorer tab |
| `_get_prompt_async(name, args)` | `get_prompt(name, args)` | **Get prompt** button, Toolkit Explorer tab |

Plus the big one, `_run_agent_async(...)` — the Chat tab's agent loop,
which opens **one** `connect_to_server()` session and reuses it for
`list_tools()` plus every `call_tool()` the LLM asks for during that
turn, instead of reconnecting per call like the four above do.

## 3. The sync <-> async bridge — `run_async()`

Streamlit runs your script top-to-bottom synchronously; the MCP client
is `async`. Every button handler in the UI calls one of the functions
above wrapped in `run_async(...)`, e.g.:

```python
tools, resources, templates, prompts = run_async(_list_everything_async())
```

`run_async` is just `asyncio.run(coro)` with one extra step: it unwraps
the `ExceptionGroup` that `anyio` (the async library MCP uses under the
hood) wraps every error in, so `st.error(...)` shows the real message
instead of an opaque group.

## 4. `is_server_reachable()` — the lightweight one

```python
reachable = owned or is_server_reachable()
```

This is the **only** client-module call that isn't a real MCP session —
it's just a raw TCP socket probe (no handshake, no protocol). It's what
powers the green/red **Online**/**Offline** badge in the sidebar, and
it's called on *every single Streamlit rerun* (so it has to be cheap —
a full `connect_to_server()` would be too slow to run that often).

## 5. `field()`, `mcp_tool_to_openai_schema()`, `tool_result_to_value()`, `tool_call_is_error()` — data shaping, not calls

These don't talk to the server themselves — they translate whatever a
session call already returned into a shape the rest of the app wants:

- `mcp_tool_to_openai_schema()` — turns an MCP `Tool` into the
  `tools=[...]` format the LLM API expects.
- `tool_result_to_value()` / `tool_call_is_error()` — unwrap a
  `CallToolResult` into plain JSON + a bool.
- `field()` — the version-tolerant attribute lookup used for fields
  like `resource_templates` / `input_schema` that have changed casing
  between `mcp` package releases.

## The whole chain, end to end

```
UI event (button click / chat_input)
   |
run_async(...)                          <- sync/async bridge
   |
one of the four wrappers, or _run_agent_async
   |
connect_to_server()                     <- the actual client, from client/mcp_client.py
   |
session.list_tools() / call_tool() / read_resource() / get_prompt()
   |
result shaped by tool_result_to_value() / field() / etc.
   |
st.session_state / rendered back into the UI
```

The Toolkit Explorer tab and the Chat tab are just two different
**callers** of the exact same client — that's the whole point of
splitting `client/mcp_client.py` out as its own module rather than
writing MCP calls inline in each tab.
