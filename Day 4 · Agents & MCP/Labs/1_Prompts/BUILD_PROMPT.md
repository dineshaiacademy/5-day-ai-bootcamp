# Day 4 Labs — Build Prompt (MCP Server + MCP Client AI App)

Copy everything inside the fenced block below into Claude Code (opened at the repo root
`5-day-ai-bootcamp-instructor`) and run it.

````text
ROLE
You are a senior Python engineer building a teaching lab for "Dinesh AI Academy · Day 4 — Agents & MCP".
Build a complete, runnable, verified lab: a standalone MCP SERVER that exposes tools, and a Streamlit AI
application that contains an MCP CLIENT connecting to that server over streamable HTTP and letting an LLM
choose and call those tools. The user picks the LLM provider AND the model in the UI: Google Gemini is the
default provider, LM Studio (local) is the one-click / automatic fallback when Gemini fails, and the .env file
is created automatically on first run.

BEFORE WRITING ANY CODE — READ THESE REFERENCE FILES AND MATCH THEIR STYLE EXACTLY
1. "Day 4 · Agents & MCP/Projects/mcp-live-toolkit/server/mcp_server.py"   (server pattern, MCPServer import, mcp.run)
2. "Day 4 · Agents & MCP/Projects/mcp-live-toolkit/client/mcp_client.py"   (streamable_http_client, ClientSession, field(), MCP→OpenAI schema)
3. "Day 4 · Agents & MCP/Projects/mcp-live-toolkit/app.py"                 (PROVIDERS dict, agent loop, Streamlit layout)
4. "Day 4 · Agents & MCP/Workshop/Projects/agent-mcp-explorer/"            (Workshop folder layout: app.py, client/, server/, src/)
5. "Day 3 - Tools & Workflows/Projects/tool-workflow-chat/.streamlit/config.toml"  (copy this theme verbatim)
6. "Day 2 - Knowledge with RAG/Workshop/Learning/1-Hour Session Plan.md" and
   "Day 3 - Tools & Workflows/Workshop/Learning/1-Hour Session Plan.md"   (lab-guide tone/format)
Do not modify any existing file outside the new Labs folder.

ENVIRONMENT FACTS (verified — do not guess other versions)
- Windows 10, Python 3.12, repo venv at ./venv
- Installed in ./venv: mcp==2.2.0, openai==3.16.2, streamlit==1.64.0
- mcp 2.x API:  server → `from mcp.server import MCPServer`  (FastMCP was renamed; keep a comment noting
  that on mcp 1.x the equivalent is `from mcp.server.fastmcp import FastMCP`)
  client → `from mcp import ClientSession`, `from mcp.client.streamable_http import streamable_http_client`,
  `from mcp.types import CallToolResult, Tool as MCPTool`
- `streamable_http_client(url)` may yield 2 or 3 values — index `streams[0], streams[1]`, never tuple-unpack.
- Tool attributes differ across versions (`input_schema` vs `inputSchema`, `is_error` vs `isError`,
  `structured_content` vs `structuredContent`) — use a `field(obj, *names, default=None)` helper like the reference.
- Both LLM providers are called with the `openai` SDK via OpenAI-compatible endpoints:
    LM Studio : base_url = LOCAL_LLM_BASE_URL (default http://localhost:1234/v1), api_key = "lm-studio"
    Gemini    : base_url = https://generativelanguage.googleapis.com/v1beta/openai/ , api_key = GEMINI_API_KEY
- .env is already git-ignored in the repo root .gitignore.

TARGET FOLDER STRUCTURE (create exactly this; mirrors the Day 2/Day 3 "Learning + Projects" layout)
Day 4 · Agents & MCP/Labs/
├── Learning/
│   └── 1-Hour Lab Guide.md
└── Projects/
    └── mcp-expense-lab/
        ├── .streamlit/config.toml          ← copied verbatim from Day 3 tool-workflow-chat
        ├── server/
        │   ├── __init__.py
        │   └── mcp_server.py               ← the MCP SERVER (standalone process)
        ├── client/
        │   ├── __init__.py
        │   └── mcp_client.py               ← the MCP CLIENT (used by the app)
        ├── src/
        │   ├── __init__.py
        │   ├── env_setup.py                ← auto-creates .env on first run (never overwrites)
        │   └── llm.py                      ← provider config + model listing + fallback + agent loop
        ├── app.py                          ← Streamlit HOST app
        ├── requirements.txt
        ├── .env.example
        ├── .env
        ├── start_server.bat
        ├── start_server.sh
        └── README.md

LAB THEME: "Smart Expense Tracker" — an in-memory expense book an AI assistant manages through MCP tools.
No external API keys are needed by any tool.

1) server/mcp_server.py — MCP SERVER
- First call `ensure_env_file()` from src/env_setup.py (add the project dir to sys.path so it imports when the
  server is run as `python server/mcp_server.py`), THEN load_dotenv(); read MCP_SERVER_HOST (default 127.0.0.1), MCP_SERVER_PORT (default 8766), PATH = "/mcp".
- `mcp = MCPServer("ExpenseLabServer", instructions="...")`.
- In-memory store: `EXPENSES: list[dict]` pre-seeded with 5 realistic sample expenses
  (fields: id:int, date:"YYYY-MM-DD", category, description, amount:float, currency:"INR").
- Allowed categories constant: food, travel, shopping, bills, entertainment, health, other.
- Expose these TOOLS with full type hints and one-line docstrings (docstring = description the LLM sees):
  a. add_expense(amount: float, category: str, description: str, date: str | None = None) -> dict
     validate amount > 0, category in allowed list (lower-case it), date defaults to today; return the saved record.
  b. list_expenses(category: str = "all", limit: int = 20) -> list[dict]   (newest first)
  c. delete_expense(expense_id: int) -> str   (safe if id missing — return a clear message, never raise)
  d. get_spending_summary(category: str = "all") -> dict  → total, count, average, per-category breakdown
  e. convert_currency(amount: float, from_currency: str, to_currency: str) -> dict
     use a fixed static rates table (INR, USD, EUR, GBP, AED, JPY) relative to USD; say "static demo rates" in output.
  f. calculate(expression: str) -> dict  — SAFE arithmetic via `ast` (NO eval), supports + - * / // % ** parentheses.
  g. get_current_date() -> dict  — today's date, weekday, ISO timestamp.
- One RESOURCE: `@mcp.resource("expenses://all")` returning JSON of all expenses.
- One PROMPT: `@mcp.prompt() monthly_report(month: str)` asking the model to call get_spending_summary and
  list_expenses itself, then write a short report.
- Tools return errors as data ({"error": "..."}) instead of raising, so the LLM can recover.
- Log every tool call with logging (INFO, timestamped).
- `if __name__ == "__main__":` print a startup banner (name, URL http://HOST:PORT/mcp, transport, tool list) then
  `mcp.run(transport="streamable-http", host=HOST, port=PORT, streamable_http_path=PATH)`.

2) client/mcp_client.py — MCP CLIENT
- MCP_SERVER_URL built from the same env vars.
- `field()` helper (version-tolerant attribute access).
- `@asynccontextmanager async def open_session()` → streamable_http_client + ClientSession + initialize().
- async functions: `list_tools()`, `call_tool(name, arguments) -> dict` (returns {"ok", "text", "structured"}),
  `list_resources()`, `read_resource(uri)`, `list_prompts()`, `get_prompt(name, args)`, `ping() -> bool`.
- `mcp_tool_to_openai_schema(tool) -> dict` converting MCP tool → OpenAI `{"type":"function","function":{...}}`.
- Sync wrappers for Streamlit: `run_sync(coro)` using `asyncio.run` (create a fresh loop each call; safe in Streamlit).
- A clear custom exception `MCPServerUnavailable` raised with a friendly message when the server is not reachable
  (catch httpx.ConnectError / ExceptionGroup wrapping it).

3) src/env_setup.py — AUTO-CREATE .env
- `ENV_PATH = <project dir>/.env`, `EXAMPLE_PATH = <project dir>/.env.example`.
- `DEFAULT_ENV_TEXT`: the exact .env content from section 7 below, as a string constant.
- `ensure_env_file() -> bool`: if .env already exists → do nothing, return False (NEVER overwrite a user's .env).
  Else copy .env.example → .env if the example exists, otherwise write DEFAULT_ENV_TEXT; also recreate
  .env.example from DEFAULT_ENV_TEXT if it is missing. Write UTF-8. Log/print "Created .env at <path>". Return True.
- `save_env_value(key: str, value: str)`: persist a value into .env with `dotenv.set_key(ENV_PATH, key, value,
  quote_mode="never")` and also set `os.environ[key] = value` so the running app picks it up immediately.

4) src/llm.py — PROVIDERS + MODEL SELECTION + FALLBACK + AGENT LOOP
- PROVIDERS is an ordered dict with EXACTLY two entries, Gemini FIRST (it is the default provider):
    "Gemini (Google AI)": base_url "https://generativelanguage.googleapis.com/v1beta/openai/",
                         api_key read from os.environ["GEMINI_API_KEY"] AT CALL TIME (not import time, so a key
                         saved from the sidebar works without restart), needs_key True,
                         default_model from GEMINI_MODEL env (fallback "gemini-3.6-flash")
    "LM Studio (local)": base_url from LOCAL_LLM_BASE_URL, api_key "lm-studio", needs_key False,
                         default_model from LMSTUDIO_MODEL env (fallback "qwen2.5-7b-instruct")
- DEFAULT_PROVIDER from env DEFAULT_PROVIDER ("gemini" → Gemini, "lmstudio" → LM Studio; default "gemini").
- FALLBACK_PROVIDER = "LM Studio (local)".
- `make_client(provider) -> OpenAI` with timeout=60 and max_retries=1.
- `list_models(provider) -> list[str]`: call client.models.list();
    Gemini   → strip "models/" prefix, keep only ids containing "gemini", drop non-chat models
               (image, audio, tts, live, embedding, veo, imagen, aqa, learnlm), sort newest-first;
    LM Studio → return the ids of the models LM Studio reports (exclude ids containing "embed").
  Always make sure the provider's default_model is in the list (insert at index 0 if missing).
  On any error return [default_model] — never raise.
- `check_provider(provider) -> tuple[bool, str]`: quick health check (Gemini: key present + models.list succeeds;
  LM Studio: models.list on the local server succeeds and at least one model is loaded). Returns (ok, message).
- `class ProviderError(Exception)` carrying `provider` and a friendly `reason`. Classify openai exceptions:
  AuthenticationError/PermissionDeniedError → "invalid or missing API key", RateLimitError → "quota / rate limit hit",
  NotFoundError → "model not found — pick another model", APIConnectionError/APITimeoutError → "provider unreachable",
  BadRequestError mentioning tools → "this model does not support tool calling". MCPServerUnavailable is NOT a
  ProviderError (switching LLM will not fix a stopped MCP server) — let it propagate separately.
- `run_agent(provider, model, user_message, history, max_steps=5) -> dict`:
    fetch MCP tools → convert to OpenAI schema → chat.completions.create(model=model, tools=..., tool_choice="auto")
    → for each tool_call: json.loads arguments (tolerate bad JSON → {}), call MCP tool via client, append
      {"role":"tool","tool_call_id":...,"content":...} → loop until no tool_calls or max_steps.
    Wrap LLM errors in ProviderError. Return {"text", "trace", "provider", "model"}; trace = list of steps
    (tool name, args, result, duration ms).
- `run_agent_with_fallback(provider, model, user_message, history, max_steps, auto_fallback: bool,
   fallback_model: str) -> dict`: call run_agent; if it raises ProviderError AND provider is Gemini AND
   auto_fallback is True → retry the SAME message once with LM Studio + fallback_model, and add
   {"fell_back": True, "fallback_reason": <reason>} to the result. If LM Studio also fails, raise a ProviderError
   whose message names both failures. Never fall back in a loop.
- SYSTEM_PROMPT: assistant manages expenses; must call tools instead of guessing numbers; amounts are INR unless stated.

5) app.py — STREAMLIT HOST APP (use st.set_page_config(page_title="MCP Expense Lab", page_icon="💸", layout="wide"))
- Add project dir to sys.path; call `ensure_env_file()` BEFORE `load_dotenv(override=False)`; if it created the file,
  show a one-time st.toast("Created .env — add your GEMINI_API_KEY in the sidebar").
- Keep all LLM choices in st.session_state so they survive reruns and switching tabs:
  `provider`, `model_gemini`, `model_lmstudio`, `auto_fallback` (default True), `messages`.
- SIDEBAR section "🤖 LLM Provider":
  • st.radio "Provider" with options [Gemini (Google AI), LM Studio (local)], default = DEFAULT_PROVIDER (Gemini),
    horizontal. Switching provider must NOT clear the chat history — the conversation continues with the new LLM.
  • Under it a status line from check_provider (cached st.cache_data ttl=30): ✅ ready / ❌ reason.
  • "Model" st.selectbox populated by list_models(selected provider) (cached st.cache_data ttl=300), preselecting the
    remembered model for that provider (each provider remembers its OWN last-selected model).
  • "🔄 Refresh models" button → clears the list_models cache and reruns.
  • st.text_input "…or type a custom model name" (optional) — if filled, it overrides the selectbox.
  • Show the active choice clearly: "Using: <provider> · <model>".
  • If Gemini is selected: st.text_input "Gemini API key" (type="password", prefilled empty, placeholder shows
    "set" / "not set") + "💾 Save key to .env" button → save_env_value("GEMINI_API_KEY", key), clear caches, st.rerun().
    If no key is set, show st.warning with the link https://aistudio.google.com/apikey and a
    "Switch to LM Studio" button.
  • st.toggle "Auto-fallback to LM Studio if Gemini fails" (default ON) + a selectbox "Fallback LM Studio model"
    (from list_models("LM Studio (local)")).
- SIDEBAR section "🔌 MCP Server": status badge (ping) with the URL.
- SIDEBAR bottom: max-steps slider (1–8), "Clear chat" button.
- Call the agent ONLY through run_agent_with_fallback. Handling:
  • Success → render the reply; add a small caption under every assistant message: "answered by <provider> · <model>".
  • If result["fell_back"] → st.warning("Gemini failed (<reason>) — answered with LM Studio instead.") and a button
    "Stay on LM Studio" that sets session_state.provider = LM Studio.
  • ProviderError with auto-fallback OFF → st.error(reason) + two buttons: "🔁 Switch to LM Studio and retry"
    (switch provider, resend the last user message) and "Pick another model".
  • MCPServerUnavailable → st.error with the exact command to start the server (no provider switch offered).
  • Never show a raw traceback.
- TAB 1 "💬 Agent Chat": st.chat_message history in st.session_state; for each assistant reply show an
  st.expander "🔧 Tool calls" listing every step from the trace (tool, args JSON, result JSON, ms).
  Show 4 example prompt buttons, e.g. "Add 450 rupees for lunch today", "How much did I spend on travel?",
  "Convert my total spending to USD", "Delete expense 2 and show the new summary".
- TAB 2 "🧰 Tool Explorer" (NO LLM): list tools from the server with description + input schema; pick a tool,
  auto-generate input widgets from its JSON schema (number/integer/string/boolean), "Call tool" button, show result.
- TAB 3 "📚 Resources & Prompts": read `expenses://all` as a dataframe; list prompts, render `monthly_report`.
- TAB 4 "🏗️ How it works": architecture diagram (text/ASCII) Host → Client → Server, and a table Host/Client/Server.
- If LM Studio is unreachable, show a friendly message telling the user to start the LM Studio local server
  (Developer tab → Start Server) and load a model with tool-calling support.

6) requirements.txt
streamlit
openai
python-dotenv
mcp[cli]
httpx
pandas
tzdata

7) .env.example  AND  .env
- Create BOTH files now with the content below (identical), AND make sure src/env_setup.py can recreate .env
  automatically on first run of the app or the server if it is ever missing.
- Leave GEMINI_API_KEY empty — never invent or hard-code a key. If a .env already exists, do NOT overwrite it.
# ── Which LLM the app starts with: gemini | lmstudio ─────────
DEFAULT_PROVIDER=gemini

# ── LLM: Google Gemini (get a free key at https://aistudio.google.com/apikey) ──
GEMINI_API_KEY=
GEMINI_MODEL=gemini-3.6-flash

# ── LLM: LM Studio (local, no key — fallback when Gemini fails) ──
LOCAL_LLM_BASE_URL=http://localhost:1234/v1
LMSTUDIO_MODEL=qwen2.5-7b-instruct

# ── MCP server (server and client must agree on these) ──────
MCP_SERVER_HOST=127.0.0.1
MCP_SERVER_PORT=8766

8) start_server.bat / start_server.sh — cd to script dir, activate repo venv if present
   (..\..\..\..\venv\Scripts\activate on Windows, ../../../../venv/bin/activate on bash), run `python server/mcp_server.py`.

9) README.md — title, one-sentence summary, ASCII architecture, table of tools/resource/prompt, Quickstart:
   (0) pip install -r requirements.txt  (1) start server in terminal 1 (.env is auto-created on first run)
   (2) streamlit run app.py in terminal 2  (3) Gemini is selected by default — paste the key in the sidebar and
   click "Save key to .env"; pick any model from the Model dropdown. Include sections: "Choosing provider & model",
   "Gemini not working? Switch to LM Studio" (manual switch + auto-fallback toggle explained), "LM Studio setup"
   (Developer tab → Start Server, load a tool-capable model like Qwen2.5-7B-Instruct), "Try these prompts",
   "Exercise: add your own tool" (e.g. set_budget / check_budget), and Troubleshooting (port in use, server not
   running, invalid Gemini key, Gemini quota hit, model not found, model doesn't call tools).

10) Learning/1-Hour Lab Guide.md — same format as the Day 2/3 session plans: learning objectives, timeline
   (0–10 MCP concepts, 10–25 build/walk the server, 25–40 client + agent loop, 40–55 hands-on exercises,
   55–60 recap), 3 graded exercises with expected results, and a quiz of 5 questions with answers.

CODING RULES
- Match the reference files' comment density and docstring style; teaching-quality comments, no dead code.
- No `eval`/`exec`. No hard-coded secrets. All config from .env via python-dotenv.
- Every tool: complete type hints + docstring (these become the MCP schema automatically).
- Windows-safe paths; UTF-8 file writes.

VERIFICATION (mandatory — do not report done until all pass)
1. `venv\Scripts\python.exe -m py_compile` on every .py file.
2. Start the server in the background; confirm it listens on 127.0.0.1:8766.
3. Run a Python smoke test using client/mcp_client.py: list_tools returns all 7 tools; call add_expense,
   list_expenses, get_spending_summary, convert_currency, calculate("(120+80)*3"), delete_expense(999)
   (returns message, no crash); read resource expenses://all; get prompt monthly_report.
4. Convert all tools with mcp_tool_to_openai_schema and assert each has type=function and a parameters object.
5. .env auto-create test: in a TEMP copy of the project folder (never touch the real .env), delete .env, run
   ensure_env_file() → .env exists with DEFAULT_PROVIDER=gemini; run it again → returns False and the file is
   unchanged; write a custom value first → confirm it is NOT overwritten.
6. Provider/model test: list_models() for both providers returns a non-empty list containing the default model
   (even when the provider is unreachable); check_provider() never raises.
7. Fallback test: with GEMINI_API_KEY forced to an invalid value in-process, run_agent_with_fallback(auto_fallback=True)
   → if LM Studio is running, returns fell_back=True and an answer from LM Studio; if LM Studio is not running,
   raises one ProviderError naming both failures. With auto_fallback=False → raises ProviderError without retrying.
8. Launch `streamlit run app.py --server.headless true` and open it in the browser preview: confirm Gemini is
   preselected, the Model dropdown and custom-model input are present, switching to LM Studio keeps the chat
   history and changes the model list, the auto-fallback toggle is ON, and all 4 tabs render with no exceptions.
9. If LM Studio is running, run one end-to-end agent turn; otherwise state clearly that the LLM step was not
   tested live. Do not claim Gemini was tested unless a real GEMINI_API_KEY is set.
10. Stop the background server and Streamlit when done; delete the temp test folder.
Finally print the created file tree and the exact run commands.
````

## Run commands (after the prompt finishes)

```bash
cd "Day 4 · Agents & MCP/Labs/Projects/mcp-expense-lab"
python server/mcp_server.py
```

```bash
cd "Day 4 · Agents & MCP/Labs/Projects/mcp-expense-lab"
streamlit run app.py
```
