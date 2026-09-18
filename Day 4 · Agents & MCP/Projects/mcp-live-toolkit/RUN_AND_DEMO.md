# How to Run & Demonstrate — MCP Live Toolkit

**Dinesh AI Academy · Day 4 — Agents & MCP**

A focused, copy-pasteable guide: get it running in two terminals, then a
90-second script for showing someone else exactly how the MCP client
connects to the server and talks to the LLM. (For the full architecture
writeup, tool reference, and troubleshooting table, see
[README.md](README.md) in this same folder.)

## Run it (2 terminals)

**Terminal 1 — start the MCP server, leave it running:**

```bash
cd "Day 4 · Agents & MCP/Projects/mcp-live-toolkit"
python server/mcp_server.py
```

Wait for `Uvicorn running on http://127.0.0.1:8765` — that's the
standalone server, alive on its own, in its own process.

**Terminal 2 — start the chat app, from the repo root:**

```bash
cd "C:\Dinesh AI Academy\git_repos\5_day_ai_bootcamp"
venv\Scripts\streamlit.exe run "Day 4 · Agents & MCP/Projects/mcp-live-toolkit/app.py"
```

This opens the app in your browser (usually `http://localhost:8501`). In
the sidebar, pick a provider:

- **LM Studio (local)** — free, 100% offline. Start LM Studio, load a
  tool-calling-capable chat model, click **Start Server** in its
  Developer tab first.
- **Gemini (Google AI)** — free tier, needs `GEMINI_API_KEY` set in
  `.env` (copy `.env.example` to `.env` first if you haven't).

*(Skipped Terminal 1? The app's sidebar has its own **Launch** button —
it runs the exact same command for you, no terminal needed.)*

## Demonstrate it — a 90-second walkthrough

### 1. Show the two independent processes (30s)

Point at both terminal windows: "This one's the server — a standalone
program. This one's the chat app." In the app's sidebar, point at the
green **Online · running externally** badge — "the app didn't start
that server, it just detected it's alive at that URL."

### 2. Prove there's no magic — call a tool with zero LLM involved (20s)

Open the **Toolkit Explorer** tab → click **Discover server
capabilities** → the Tools / Resources / Prompts columns fill in live
from the server. Pick `get_weather`, type a city, click **Call tool** —
a real result appears, and a matching log line appears in Terminal 1 at
the same instant.

### 3. Show the client talking to BOTH the server and the LLM (30s) — this is the payoff

Switch to the **Chat** tab, click a suggestion pill (e.g. **Weather** or
**Tasks**). Watch the status box fill in live, one line at a time, right
under your message:

```
🔌 Creating an MCP client session…
📡 Client → Server — connected over HTTP to http://127.0.0.1:8765/mcp
🔧 Server → Client — discovered 8 tools: ...
🧠 Client → LLM — sending the conversation + tool schemas, asking it to pick one…
🎯 LLM → Client — selected tool(s): get_weather
📤 Client → Server — session.call_tool("get_weather", {"city": "Paris"})
📥 Server → Client — result: {"temperature_c": 18.2, ...}
```

No clicking required — it's visible immediately and stays expanded
after the answer, so you can literally read it aloud as proof:
*"the client just opened a connection, asked the model which tool to
use, the model picked one, and the client sent that call over HTTP to
the server."*

*(Want the exact raw JSON request/response too? Expand **Raw
request/response JSON** just below it.)*

### 4. Break it on purpose, then fix it live (10s)

Ctrl+C the server in Terminal 1. Ask the chat app anything — it shows a
clear "couldn't reach the server" error. Restart the server (or click
**Launch** in the sidebar) and ask again — it just works, no app
restart needed.

That last step is the strongest close: it proves this is a real,
independently-running client/server pair, not a bundled library call
wearing a costume.

## Quick reference

| Want to... | Do this |
|---|---|
| Stop everything | Ctrl+C in both terminals, or the sidebar **Stop** button if you launched the server from the app |
| Change the server's port | Edit `MCP_SERVER_PORT` in `.env` (keep it in sync between server and app — they read the same file) |
| See the server's own log without a second terminal | Sidebar → **Server log** expander (works whether you launched it via terminal or the in-app button) |
| Try a harder multi-tool question | The **Briefing** pill — it chains `get_current_time` + `get_weather` in one request |
