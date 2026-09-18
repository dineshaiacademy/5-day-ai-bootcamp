# MCP Live Toolkit — a standalone MCP server + a chat app that talks to it

**Dinesh AI Academy · Day 4 — Agents & MCP**

A complete, *real* Model Context Protocol integration, built to be demoed —
by you, or by anyone else on this team, cold, in under two minutes. It's
the network-transport sibling of
[`mcp-notes-demo`](../mcp-notes-demo/README.md): instead of a client
silently spawning the server as a subprocess, **the server here is its own
standalone program** — you launch it yourself, watch it run in its own
window (or its own log panel), and the chat app's MCP client connects to
it over real HTTP, exactly the way it would connect to a server on another
machine entirely.

## What you'll see, in one sentence

> **Two independent programs — a server exposing tools, and a chat app
> with an LLM and an MCP client — that only agree on one thing: a URL.**

Stop the server mid-conversation and the next message fails with a clear
"couldn't reach the server" error. Start it again and the chat app
reconnects on the very next message, with zero code changes anywhere.
*That's* the proof this is a real client/server protocol, not a library
call wearing a costume.

## Architecture

```text
┌──────────────────────────────── HOST ─────────────────────────────────┐
│                      app.py  (this Streamlit app)                      │
│                                                                          │
│   Toolkit Explorer tab                  Chat tab                       │
│   (no LLM — calls the client            (LLM picks a tool name +       │
│    directly, by hand)                    arguments → client executes)  │
│                     │                            │                     │
│                     └────────────┬───────────────┘                     │
│                                  ▼                                     │
│                     client/mcp_client.py    ← the CLIENT               │
└──────────────────────────────────┼─────────────────────────────────────┘
                                    │  MCP protocol, streamable-HTTP
                                    │  over a real TCP connection —
                                    │  http://127.0.0.1:8765/mcp
                                    ▼
                     server/mcp_server.py       ← the SERVER
              a SEPARATE process, its own console, its own
           lifecycle — started before the app, outlives every
                    individual chat request it serves
```

| Role | What it is | In this project |
|---|---|---|
| **Host** | The application a human actually uses | `app.py` (Streamlit) |
| **Client** | Lives inside the host; one connection to one server | `client/mcp_client.py` |
| **Server** | A standalone HTTP process exposing tools/resources/prompts | `server/mcp_server.py` |

## What the server exposes

A small everyday toolkit — real utilities, no mocked data, no API key
required for any of it:

| Primitive | Name(s) | What it means |
|---|---|---|
| **Tool** | `get_current_time` | Current date/time in any IANA timezone |
| **Tool** | `calculate` | Safe arithmetic (AST-evaluated — never uses `eval()`) |
| **Tool** | `get_weather` | **Real** current weather for any city, via the free Open-Meteo API |
| **Tool** | `convert_units` | Length, weight, and temperature conversion |
| **Tool** | `add_task` / `list_tasks` / `complete_task` | A small shared, in-memory task list |
| **Tool** | `roll_dice` | Rolls N dice with M sides — shows randomness + bounded inputs |
| **Resource** | `task://all` | Read-only snapshot of the task list — no LLM decision needed to read it |
| **Prompt** | `daily_briefing(city)` | Asks the model to chain `get_current_time` + `get_weather` itself |

Every tool's input schema is generated automatically from its Python type
hints, and its description comes straight from its docstring — that's the
whole reason MCP servers don't need a separate, hand-maintained schema file.

## Quickstart — 3 steps, ~2 minutes

**0. Install dependencies (once):**

```bash
cd "Day 4 · Agents & MCP/Projects/mcp-live-toolkit"
python -m venv venv
venv\Scripts\activate        REM Windows — use `source venv/bin/activate` on macOS/Linux
pip install -r requirements.txt
copy .env.example .env       REM Windows — use `cp .env.example .env` on macOS/Linux
```
*(Skip this if you're using this repo's shared root `venv` — it already has everything.)*

**1. Launch the MCP server — pick whichever is easiest:**

| Option | Command / action |
|---|---|
| **Terminal (recommended for the first demo)** | `python server/mcp_server.py` — leave this window open, you'll watch it log every tool call live |
| **Double-click launcher** | `start_server.bat` (Windows) / `start_server.sh` (macOS/Linux) |
| **In-app button** | Start step 2 below first, then click **Launch** in the app's sidebar — no terminal needed at all |

You'll see a startup banner and then `Uvicorn running on http://127.0.0.1:8765` —
that's correct, this is a real HTTP server. Leave it running.

**2. Launch the chat app, in a *second* terminal:**

```bash
streamlit run app.py
```
Pick a provider in the sidebar:
- **LM Studio (local)** — free, 100% offline. Load any tool-calling-capable
  chat model (Llama 3.1+, Qwen, Gemma 3/4 instruct family) and click
  **Start Server** in LM Studio's Developer tab first.
- **Gemini (Google AI)** — free tier, needs `GEMINI_API_KEY` in `.env`.

**3. Try the demo:** open the **Chat** tab and click one of the suggestion
pills (weather, world clock, math, unit conversion, tasks, dice, or the
chained "daily briefing"), or type your own request.

## A 60-second demo script

If you're showing this to someone else, this sequence makes every moving
part visible in order:

1. **Point at the two terminals** — "this one is the server, this one is
   the chat app. Two separate programs."
2. Open the **Toolkit Explorer** tab, click **Discover server capabilities**
   — "the app didn't hardcode this list, it just asked the server."
3. Pick `get_weather`, type a city, click **Call tool** — watch the result
   appear here *and* a new log line appear in the server's terminal at the
   same instant.
4. Switch to the **Chat** tab, ask *"What's the weather in Tokyo, and
   what's 15% of $84.50?"* — expand **How this was generated** and walk
   through the trace: the LLM call that requested the tools, then each
   `session.call_tool(...)` that actually ran them.
5. **Stop the server** (Ctrl+C in its terminal). Ask the chat app anything
   — show the friendly "couldn't reach the server" error.
6. **Restart it** (or click the sidebar's **Launch** button instead this
   time) and ask again — it just works, no app restart needed.

## Try it yourself, outside Streamlit

**Talk to the running server from plain Python**, exactly like `app.py`
does internally:

```python
import asyncio
from client.mcp_client import connect_to_server

async def main():
    async with connect_to_server() as session:
        tools = await session.list_tools()
        print([t.name for t in tools.tools])

        result = await session.call_tool("get_weather", {"city": "Mumbai"})
        print(result.structured_content)

asyncio.run(main())
```

**Poke at it with the MCP Inspector** (a zero-code web UI for MCP servers)
— with the server already running, launch the Inspector separately and
connect it to `http://127.0.0.1:8765/mcp` with transport **Streamable
HTTP**:

```bash
npx @modelcontextprotocol/inspector
```

## Why a `client/` module at all?

Because a client's job is narrow and reusable: open a connection, discover
what the server can do, execute a call, hand back the result. It knows
nothing about Streamlit, Gemini, or LM Studio, and — unlike a stdio
client — it doesn't even know how to *start* the server; it only knows a
URL. That's exactly why `app.py` can use the same
`mcp_tool_to_openai_schema()` helper whether the model behind it is local
or cloud, and why the server can run on a completely different machine
with a one-line `.env` change (`MCP_SERVER_HOST` / `MCP_SERVER_PORT`).

## Extend it

Add a new `@mcp.tool()` (or `@mcp.resource()` / `@mcp.prompt()`) to
`server/mcp_server.py`, save, and restart the server (Ctrl+C, then run it
again — or click **Stop** then **Launch** in the sidebar). Reload the
Streamlit app and click **Discover server capabilities**, or just start
chatting: the new tool shows up automatically because both tabs *discover*
the server's capabilities live via `list_tools()` rather than having them
hardcoded.

## Troubleshooting

| Symptom | Fix |
|---|---|
| Sidebar shows **Offline** | The server isn't running. Click **Launch**, or run `python server/mcp_server.py` in a terminal. |
| `Couldn't reach the MCP server at http://127.0.0.1:8765/mcp` | Same as above — also check nothing else is using port 8765 (`MCP_SERVER_PORT` in `.env` to change it; keep server and app in sync). |
| Weather tool fails with a network error | `get_weather` calls the free public Open-Meteo API — it needs outbound internet access from wherever the *server* process runs. |
| `ExceptionGroup: unhandled errors in a TaskGroup` | The MCP client manages its HTTP connection with an `anyio` task group, so any exception while a session is open surfaces wrapped. `run_async()` in `app.py` unwraps it to the real error before it reaches `st.error(...)` — if you see a raw one while extending this project, go one level deeper (`exc.exceptions[0]`). |
| Model never calls a tool | Some small/local models don't reliably support function calling — try a Llama 3.1+/Qwen/Gemma instruct model in LM Studio, or switch to Gemini. |

## When MCP is (and isn't) worth it

| Reach for MCP when... | Stick with plain tool calling when... |
|---|---|
| The same tool needs to be reused across multiple apps (this app, Claude Desktop, a teammate's CLI agent) — or across multiple *machines* | It's one tool, used by one app, never reused elsewhere |
| You're exposing a real backend/service behind one governed, testable network boundary | You need the lowest possible latency (a network hop is slower than a direct function call) |
| You want a tool that's swappable — point any MCP host at a different server without touching the host | You're prototyping fast and don't yet know if this needs to be shared |
| You want to offer resources or prompts too, not just function calls | The "tool" is trivial (string formatting, basic math) — wrapping it in a server adds ceremony, not value |

## Reference

- Model Context Protocol docs: https://modelcontextprotocol.io
- MCP Python SDK (GitHub): https://github.com/modelcontextprotocol/python-sdk
- MCP Inspector: https://github.com/modelcontextprotocol/inspector
- Open-Meteo (free weather API, no key required): https://open-meteo.com
