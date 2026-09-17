# MCP Notes Demo — a real MCP server + client, wired into an LLM

**Dinesh AI Academy · Day 4 — Agents & MCP**

A small, complete, *working* Model Context Protocol (MCP) integration —
not a mock, not hand-waved. It's the natural next step after
[`Learning/1-MCP_Server_Basics.ipynb`](../../Learning/1-MCP_Server_Basics.ipynb):
the same "Notes" server, now as a real reusable project with a Streamlit
front end that shows MCP working in two different ways side by side.

## What you'll see, in one sentence

> **The LLM only ever decides *which* tool to call — an MCP client is what
> actually calls it, over a protocol, on a completely separate process.**

Run the app and you'll see that split enforced twice: once with no LLM at
all (the **MCP Explorer** tab), and once with one (the **Chat** tab).

## Architecture

```text
┌─────────────────────────────── HOST ───────────────────────────────┐
│                     app.py  (this Streamlit app)                    │
│                                                                       │
│   MCP Explorer tab                    Chat tab                       │
│   (no LLM — calls the client          (LLM picks a tool name +       │
│    directly, by hand)                  arguments → client executes)  │
│                     │                          │                     │
│                     └──────────┬───────────────┘                     │
│                                ▼                                     │
│                     client/mcp_client.py   ← the CLIENT              │
└────────────────────────────────┼──────────────────────────────────┘
                                  │  MCP protocol, stdio transport
                                  │  (client spawns the server as a
                                  │   subprocess and talks over
                                  │   stdin/stdout)
                                  ▼
                     server/mcp_server.py     ← the SERVER
                     (a separate Python process — has no idea
                      an LLM or a human is even involved)
```

| Role | What it is | In this project |
|---|---|---|
| **Host** | The application a human actually uses | `app.py` (Streamlit) |
| **Client** | Lives inside the host; one connection to one server | `client/mcp_client.py` |
| **Server** | A standalone process exposing tools/resources/prompts | `server/mcp_server.py` |

## What the server exposes

`server/mcp_server.py` is a tiny "study notes" service, using all three MCP
primitives so you can see how each one differs:

| Primitive | Name(s) | What it means |
|---|---|---|
| **Tool** | `add_note`, `list_notes`, `search_notes`, `delete_note` | An *action* — the LLM asks the server to **do** something |
| **Resource** | `note://all`, `note://{title}` | *Read-only data*, fetched by URI — no LLM decision needed to read it |
| **Prompt** | `summarize_note(title)` | A reusable, parameterized prompt template the server owns |

Every tool's input schema is generated automatically from its Python type
hints, and its description comes straight from its docstring — that's the
whole reason MCP servers don't need a separate, hand-maintained schema file.

## Why a `client/` module at all?

Because a client's job is narrow and reusable: open a connection, discover
what the server can do, execute a call, hand back the result. It knows
nothing about Streamlit, Gemini, or LM Studio — which is exactly why
`app.py` can use the *same* `mcp_tool_to_openai_schema()` helper whether
the model behind it is local or cloud. Try swapping providers in the
sidebar; the client code doesn't change at all.

## Run it

```bash
cd "Day 4 · Agents & MCP/Projects/mcp-notes-demo"
python -m venv venv
venv\Scripts\activate        # Windows
pip install -r requirements.txt
cp .env.example .env         # then fill in GEMINI_API_KEY if you'll use Gemini
streamlit run app.py
```

Pick a provider in the sidebar:
- **LM Studio (local)** — free, 100% offline. Load any tool-calling-capable
  chat model (Llama 3.1+, Qwen, Gemma 3/4 instruct family) and click
  **Start Server** in LM Studio's Developer tab first.
- **Gemini (Google AI)** — free tier, needs `GEMINI_API_KEY` in `.env`.

## Try it yourself, outside Streamlit

**1. Run the server alone** (it won't print anything — that's correct; it's
waiting for a client to speak MCP to it over stdin/stdout):

```bash
python server/mcp_server.py
```
Press `Ctrl+C` to stop it.

**2. Poke at it with the MCP Inspector** (a zero-code web UI for MCP
servers — the fastest way to sanity-check one while you're building it):

```bash
mcp dev server/mcp_server.py
```

**3. Talk to it from plain Python**, exactly like `app.py` does internally:

```python
import asyncio
from client.mcp_client import connect_to_server

async def main():
    async with connect_to_server() as session:
        tools = await session.list_tools()
        print([t.name for t in tools.tools])

        result = await session.call_tool("add_note", {"title": "hi", "content": "MCP works!"})
        print(result.structured_content)

asyncio.run(main())
```

## Extend it

Add a new `@mcp.tool()` (or `@mcp.resource()` / `@mcp.prompt()`) to
`server/mcp_server.py`, save, and reload the Streamlit app — no changes
needed anywhere else. Click **Discover server capabilities** in the MCP
Explorer tab, or just start chatting: the new tool shows up automatically
because both tabs *discover* the server's capabilities live via
`list_tools()` rather than having them hardcoded. That auto-discovery — a
tool built once, reusable by any host without touching client code — is
the entire value proposition of MCP over Day 3's plain, hand-wired tool
calling.

## A real gotcha you'll hit

The stdio client manages its subprocess connection with an `anyio` task
group. That means **any** exception raised while a session is open — a bad
tool argument, a provider rate limit, a dropped connection — surfaces as an
opaque `ExceptionGroup: unhandled errors in a TaskGroup`, not the actual
error underneath. `run_async()` in `app.py` unwraps it down to the real
exception before it ever reaches `st.error(...)`. If you see a raw
`ExceptionGroup` traceback anywhere while extending this project, that's
why — go one level deeper (`exc.exceptions[0]`) to find the real cause.

## When MCP is (and isn't) worth it

| Reach for MCP when... | Stick with plain tool calling when... |
|---|---|
| The same tool needs to be reused across multiple apps (this app, Claude Desktop, a teammate's CLI agent) | It's one tool, used by one app, never reused elsewhere |
| You're exposing a real backend/database/service behind one governed, testable boundary | You need the lowest possible latency (a subprocess/HTTP hop is slower than a direct function call) |
| You want a tool that's swappable — point any MCP host at a different server without touching the host | You're prototyping fast and don't yet know if this needs to be shared |
| You want to offer resources or prompts too, not just function calls | The "tool" is trivial (string formatting, basic math) — wrapping it in a server adds ceremony, not value |

## Reference

- Model Context Protocol docs: https://modelcontextprotocol.io
- MCP Python SDK (GitHub): https://github.com/modelcontextprotocol/python-sdk
- MCP Inspector: https://github.com/modelcontextprotocol/inspector
