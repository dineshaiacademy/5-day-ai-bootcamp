# Premium Agent Studio — an independent agent, consumed by a premium chat app

**Dinesh AI Academy · Day 4 — Agents & MCP**

Three programs, each independent, each with its own job:

```text
┌─────────────────────────┐      ┌──────────────────────────┐      ┌───────────────────────────┐
│   server/mcp_server.py  │◄────►│      agent/agent.py        │◄────►│         app.py             │
│                          │ MCP  │                            │import│                            │
│  A standalone process,  │ over │  THE AGENT. No UI code.    │      │  A premium Streamlit chat  │
│  its own lifecycle —    │ HTTP │  Gemini function calling   │      │  UI that CONSUMES the      │
│  exposes tools/resource │      │  + an MCP client. Runs on  │      │  agent — renders every     │
│  over streamable-HTTP   │      │  its own: `python          │      │  AgentEvent it yields.     │
│                          │      │  agent/agent.py`           │      │                            │
└─────────────────────────┘      └──────────────────────────┘      └───────────────────────────┘
```

The point of this project is that middle box. **The agent is not part of
the app** — it's a plain Python module (`agent/agent.py`) with zero
Streamlit import anywhere in it. You can run it, use it, and prove it
works completely on its own, in a terminal, with no web UI at all. The
Streamlit app in `app.py` is just one *host* that happens to consume it;
nothing stops you from importing the same `Agent` class into a CLI tool, a
Slack bot, or another notebook.

## What each piece is

| Piece | What it is | Knows about |
|---|---|---|
| `server/mcp_server.py` | A standalone MCP server (streamable-HTTP) exposing 7 tools + 1 resource | Nothing but its own tools — no LLM, no agent, no app |
| `client/mcp_client.py` | A thin MCP protocol client | The MCP protocol only — no LLM, no Gemini, no Streamlit |
| **`agent/agent.py`** | **The independent agent** — Gemini function calling (native `google-genai` SDK, streamed) wired to the MCP client | Gemini + MCP. **Nothing about Streamlit.** |
| `app.py` | A premium ChatGPT-style Streamlit UI | The agent's public API (`Agent`, `AgentEvent`) only |

## Quickstart

**0. Install dependencies (once):**

```bash
cd "Day 4 · Agents & MCP/Projects/premium-agent-studio"
python -m venv venv
venv\Scripts\activate        REM Windows -- use `source venv/bin/activate` on macOS/Linux
pip install -r requirements.txt
copy .env.example .env       REM Windows -- use `cp .env.example .env` on macOS/Linux
```
*(Skip this if you're using this repo's shared root `venv` — it already has everything.)*

**1. Add your key** — edit `.env` and set `GAISTUDIO_API_KEY` (a free key
from [aistudio.google.com/apikey](https://aistudio.google.com/apikey)).

**2. Launch the MCP server**, in its own terminal:

```bash
python server/mcp_server.py
```

**3. Now run the agent — pick either or both:**

**A. Standalone, zero UI** (proves the agent works completely on its own):

```bash
python agent/agent.py
python agent/agent.py "What's the weather in Tokyo right now?"
```

You'll see the agent stream its answer straight into the terminal, printing
every tool call and result as they happen — no Streamlit, no browser, no
app around it at all.

**B. The premium chat app**, in a *third* terminal:

```bash
streamlit run app.py
```

Open the **Chat** area, click a suggestion pill (weather, world clock,
math, unit conversion, tasks), or type your own request.

## What makes the app "premium"

- Sidebar with live model/temperature/max-tokens/system-prompt controls
  that take effect on the very next message.
- Assistant replies stream in token-by-token as Gemini generates them
  (not dumped all at once), with a visible typing cursor.
- A live, expandable activity log per turn showing every step the agent
  took — status updates, exact tool calls with arguments, and results —
  built entirely from `AgentEvent`s the agent yields, not guessed at.
- A running session token-usage counter, sourced from the real API
  response (`usage_metadata`), never estimated.
- A one-click MCP server launcher/stopper with a live log tail, so the
  whole three-process story is visible and controllable from one screen.
- The repo's house theme (deep indigo/violet on a clean neutral canvas,
  full light/dark support) — not default unstyled Streamlit.
- Friendly, readable error messages — a missing API key or an offline MCP
  server never crashes the app or shows a raw traceback.

## Why the agent is a separate module, not app code

Because an *agent* — something that decides what to do and does it — is a
different concern than a *chat UI* — something that displays what
happened. Keeping them separate means:

- You can test and demo the agent with `python agent/agent.py`, without
  ever starting Streamlit.
- A different host (a script, a bot, a test suite) can reuse the exact
  same `Agent` class and get the exact same behavior.
- `app.py` never has to know *how* Gemini function calling or the MCP
  protocol work — it only has to know how to render five event kinds
  (`status`, `tool_call`, `tool_result`, `token`, `final`/`usage`/`error`).

## The agent loop, in one paragraph

`Agent.run(history)` sends the conversation to Gemini, streamed, along
with the MCP server's tools translated into Gemini function declarations.
If Gemini answers with plain text, that's the final answer — streamed
straight to the caller. If Gemini instead requests one or more tool calls,
the agent executes each one for real over HTTP against the standalone MCP
server (`session.call_tool(...)`), feeds the results back as function
responses, and asks Gemini again. This repeats until Gemini stops asking
for tools, or a `max_steps` safety cap is hit (an agent that keeps
requesting tools forever is a bug, not a feature — the cap exists so a
confused model can't loop indefinitely on your API quota).

## Extend it

Add a new `@mcp.tool()` to `server/mcp_server.py`, save, restart the
server — the agent discovers it automatically on its very next
`list_tools()` call, in both the CLI and the app, with zero code changes
anywhere else.

## Troubleshooting

| Symptom | Fix |
|---|---|
| Sidebar shows **Offline** / CLI prints a connection error | The MCP server isn't running — `python server/mcp_server.py`, or click **Launch** in the app's sidebar. |
| `No Gemini API key found` | Set `GAISTUDIO_API_KEY` in `.env` — see Quickstart step 1. |
| Port conflict with `mcp-live-toolkit` | That sibling project defaults to port 8765; this one defaults to 8770. Change `MCP_SERVER_PORT` in `.env` if you still collide with something else. |
| Model never calls a tool | Try a different model in the sidebar (or `DEFAULT_MODEL` in `agent/agent.py`) — not all Gemini models support function calling equally well. |

## Reference

- Model Context Protocol docs: https://modelcontextprotocol.io
- Gemini API — Function calling: https://ai.google.dev/gemini-api/docs/function-calling
- `google-genai` Python SDK: https://github.com/googleapis/python-genai
