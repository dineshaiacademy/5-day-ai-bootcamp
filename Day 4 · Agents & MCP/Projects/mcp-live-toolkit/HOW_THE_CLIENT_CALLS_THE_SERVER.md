# How the Client Calls the MCP Server

**Dinesh AI Academy · Day 4 — Agents & MCP · MCP Live Toolkit**

A focused walkthrough of the actual mechanics: what happens, in what
order, when this app talks to the MCP server. (For run instructions see
[RUN_AND_DEMO.md](RUN_AND_DEMO.md); for architecture and the tool
reference see [README.md](README.md).)

## 1. The client is just a Python function — `connect_to_server()`

In [client/mcp_client.py](client/mcp_client.py), there's no persistent
"client object" sitting around. Every single action (list tools, call a
tool, read a resource) opens a **brand new connection**, does one thing,
and closes it again:

```python
@asynccontextmanager
async def connect_to_server():
    async with streamable_http_client(MCP_SERVER_URL) as streams:
        read_stream, write_stream = streams[0], streams[1]
        async with ClientSession(read_stream, write_stream) as session:
            await session.initialize()
            yield session
```

Three things happen here, in order:

| Step | Code | What it actually does |
|---|---|---|
| 1. Open the pipe | `streamable_http_client(MCP_SERVER_URL)` | Opens a real HTTP connection to `http://127.0.0.1:8765/mcp` — this is the literal network call. If the server isn't running, it fails **here**, immediately. |
| 2. Wrap it in the protocol | `ClientSession(read_stream, write_stream)` | Wraps that raw connection with MCP's message format — JSON-RPC requests/responses, request IDs, etc. This is "speaking MCP," not just HTTP. |
| 3. Handshake | `session.initialize()` | Client and server exchange protocol versions and capabilities. Nothing else is allowed until this completes. |

`yield session` hands that live, initialized session back to whoever
called `connect_to_server()` — and when their `async with` block ends,
the connection closes automatically.

## 2. What a "call" looks like — `session.call_tool(...)`

Once you have a `session`, calling a tool is one line:

```python
result = await session.call_tool("get_weather", {"city": "Paris"})
```

Under the hood, `ClientSession` turns that into a JSON-RPC request that
looks roughly like this, and sends it over the HTTP connection from
step 1:

```json
{"jsonrpc": "2.0", "id": 3, "method": "tools/call",
 "params": {"name": "get_weather", "arguments": {"city": "Paris"}}}
```

The server (a completely separate process —
[server/mcp_server.py](server/mcp_server.py)) receives that HTTP
request, runs the matching Python function, and sends back a JSON-RPC
response. `session.call_tool(...)` waits for that response and hands it
back to you as a `CallToolResult` object.

`session.list_tools()` works identically, just with `method:
"tools/list"` and no arguments — the server introspects every
`@mcp.tool()` it has registered and reports their names, descriptions,
and input schemas.

## 3. Who actually calls `connect_to_server()` — two different callers

**A. No LLM at all — the Toolkit Explorer tab.** In [app.py](app.py):

```python
async def _call_tool_async(name: str, args: dict):
    async with connect_to_server() as session:
        result = await session.call_tool(name, args)
        return tool_result_to_value(result), tool_call_is_error(result)
```

You pick a tool and arguments by hand in the UI; this fires directly.
Proves the client/server link works with zero AI involved.

**B. Through the LLM — the Chat tab's agent loop.** `_run_agent_async`
in [app.py](app.py) opens **one** session and reuses it for a whole
conversation turn:

```python
async with connect_to_server() as session:
    tools = (await session.list_tools()).tools          # ask server what it can do
    ...
    response = client.chat.completions.create(...)       # ask the LLM which tool to use
    ...
    result = await session.call_tool(name, args)          # execute whatever the LLM picked
```

The LLM never talks to the server directly — it only ever returns
*"call `get_weather` with `{"city": "Paris"}`"* as text. The
`session.call_tool(...)` line is the only place that request actually
leaves the process and hits the server over HTTP.

## 4. The order of operations for one chat message

```
You type: "What's the weather in Paris?"
  |
app.py opens a session -> HTTP connect to :8765 -> handshake         [connect_to_server]
  |
session.list_tools()  -> HTTP request -> server replies with 8 tools  [discovery]
  |
LLM gets the conversation + those 8 tool schemas, picks one           [goes to Gemini/LM Studio, NOT to the MCP server]
  |
session.call_tool("get_weather", {"city": "Paris"}) -> HTTP request -> server runs get_weather() -> HTTP response
  |
Result fed back to the LLM -> LLM writes the final sentence
  |
Session closes
```

That's exactly what the live activity log in the Chat tab prints in
real time — each line (🔌 creating the session, 📡 connecting, 🔧
discovering tools, 🧠 asking the LLM, 🎯 tool selected, 📤 calling the
server, 📥 getting the result back) corresponds to one of the steps
above, so you can watch this sequence happen instead of just reading
about it. See [RUN_AND_DEMO.md](RUN_AND_DEMO.md) for how to trigger and
read that log live.

## 5. Why a fresh session per call, instead of one long-lived connection?

Because it makes the failure mode obvious and the code trivially simple:
every action is self-contained (open → do one thing → close), so there's
no shared connection state to leak between unrelated requests, and no
special handling needed if the server restarts between one chat message
and the next — the very next action just opens a new connection and
either succeeds or fails cleanly. The cost is a small amount of
per-request overhead (a fresh HTTP handshake each time), which is a
non-issue at this scale and is the same tradeoff the sibling
[`mcp-notes-demo`](../mcp-notes-demo/README.md) project makes with its
stdio transport.
