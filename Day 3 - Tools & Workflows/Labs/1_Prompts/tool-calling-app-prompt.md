ROLE
Act as a senior full-stack AI engineer building a small, fast, RELIABLE demo app
for "Dinesh AI Academy" — a hands-on AI engineering bootcamp.

TASK
Build a minimal, runnable Streamlit chat app that demonstrates LLM tool/function
calling: the model has exactly two tools available — a calculator and a weather
lookup — and decides for itself whether a question needs one. The app can talk
to two interchangeable providers, Gemini (cloud) or LM Studio (local), picked
from a sidebar dropdown — this exists so that if one provider has a problem
(bad key, quota, local server not running), you can immediately try the other
to tell whether the issue is the provider or the app itself. A "Tool-Call
Trace" option shows the full decision flow for each reply. Keep the scope
small and the build fast, and follow the CONTEXT section's exact code pattern
— it has been verified against the real API and against a working reference
app already in this repo, specifically to avoid the kind of subtle bugs that
break the app the moment someone asks a question.

CONTEXT — read this carefully, it is the actual working recipe, not a guess
- Use the `openai` Python SDK for BOTH providers, not the `google-genai` SDK.
  This is the key decision that makes provider-switching possible: LM Studio
  and Gemini both expose an OpenAI-compatible chat endpoint, so the exact same
  request/response code works against either one — only `base_url` and
  `api_key` differ. Do not use `google.genai` anywhere in this app.
- Provider config — use exactly this structure, it mirrors a proven working
  app already in this repo (`Day 3 - Tools & Workflows/Projects/tool-workflow-chat/app.py`,
  worth reading for reference if anything is unclear):
  ```python
  PROVIDERS = {
      "Gemini (cloud)": {
          "base_url": "https://generativelanguage.googleapis.com/v1beta/openai/",
          "api_key_env": "GEMINI_API_KEY",
          "needs_key": True,
          "models": ["gemini-3.6-flash", "gemini-3.5-flash", "gemini-3.5-flash-lite"],
      },
      "LM Studio (local)": {
          "base_url": "http://localhost:1234/v1",
          "api_key_env": None,  # LM Studio ignores the key; pass any non-empty string
          "needs_key": False,
          "models": None,  # discovered live below — a local server has no staleness risk
      },
  }
  ```
- For Gemini, use the 3 hardcoded model ids above in a dropdown — no live
  discovery, Gemini's catalog changes and a live-discovered id can 404
  unpredictably. For LM Studio, DO call `client.models.list()` to populate its
  model dropdown live — it's a local, free, instant call with no rate limits
  or staleness risk, so there's no reason to hardcode it (whatever the user
  has loaded in LM Studio is what should show up).
- Build the OpenAI client with `OpenAI(base_url=..., api_key=...)`, cached
  with `@st.cache_resource` keyed on `(base_url, api_key)` so switching
  providers gets a fresh client automatically instead of reusing a stale one.
- Tool schemas — define them as plain JSON dicts in the `{"type": "function",
  "function": {"name": ..., "description": ..., "parameters": {...}}}` shape
  (OpenAI's tool-schema format, not Gemini's native format) and pass them via
  the `tools=` argument to `client.chat.completions.create(...)`. This is the
  same format both providers accept through the OpenAI-compatible endpoint.
- The tool-calling loop — implement EXACTLY this shape (this is the part that
  breaks most often when guessed; follow it precisely):
  1. Call `client.chat.completions.create(model=..., messages=working,
     tools=TOOL_SCHEMAS, ...)` — NOT streaming for this call.
  2. Read `response.choices[0].message`. Append it to your working messages
     list as-is (append the message object itself, or its `.model_dump()` —
     either works, but keep it consistent).
  3. If `message.tool_calls` is empty/None, the model is done — `message.content`
     is the final answer.
  4. If `message.tool_calls` is present, for each tool call: parse
     `tool_call.function.arguments` as JSON (wrap in try/except — a weak model
     can occasionally send malformed JSON; fall back to `{}` if it fails), look
     up and run the matching local Python function with those arguments, then
     append `{"role": "tool", "tool_call_id": tool_call.id, "content":
     json.dumps(result)}` to the working messages list. The `tool_call_id`
     match is required — without it, the next request will error.
  5. Loop back to step 1 with the updated messages list. Cap this at a small
     fixed number of iterations (e.g. 4) as a safety net against a runaway
     loop; if the cap is hit, show a plain message saying so instead of
     erroring.
  6. Streaming the final answer is NOT required — returning the final
     `message.content` and displaying it with `st.markdown` is simpler and
     avoids combining streaming with the tool-call loop, which is a common
     source of bugs. Only stream if there were zero tool calls at all (a
     single plain request/response), where streaming is simple and safe.
- Record every step of the loop above (each request sent, each response
  received, each tool call with its arguments and result) into a plain list of
  dicts as you go — this list IS the data for the Tool-Call Trace panel below.
  Don't reconstruct it after the fact from guesswork; build it live, in the
  same loop, so it's always accurate to what actually happened.
- `.env` handling — create an ACTUAL `.env` file (not just `.env.example`),
  containing exactly:
  ```
  GEMINI_API_KEY=
  ```
  so the user only has to open it and paste their key after the `=` — they
  should not need to copy/rename anything. Also create `.env.example` with the
  same content plus a one-line comment on where to get a key, for reference.
  Both files are fine to create — `.env` is already covered by this project's
  `.gitignore` pattern if one exists; if you create a `.gitignore`, include
  `.env` in it.
- No key will be present in `.env` at build time — you (Copilot) are building
  this before the user has pasted in their Gemini key, so `GEMINI_API_KEY`
  will be empty when you test. Default the provider picker to "Gemini
  (cloud)" (it should be the visible default once a key is added), but build
  and verify the app using **LM Studio** instead, since that's the provider
  that can actually work with no key at all. The app itself must never crash
  just because Gemini has no key yet — it should show the "not connected"
  state cleanly (see the sidebar spec below) and let LM Studio work normally.
- Windows terminals often use a non-UTF-8 console encoding (cp1252) and will
  crash with `UnicodeEncodeError` if something tries to `print()` or log an
  emoji, arrow, or other special Unicode character to the console/stdout.
  Emoji and special characters ARE fine inside Streamlit UI strings (labels,
  `st.error`, `st.markdown`, button text) since those render in the browser,
  not the terminal — just make sure nothing in `app.py` ever `print()`s or
  logs one of those characters to the console, including inside exception
  handlers (don't `print(exception)` if the exception message could contain
  one — use `st.error(str(exc))` instead, which is safe).

REQUIREMENTS — build exactly this, and nothing more:

1. Files (all directly in the current folder — this prompt is meant to be
   pasted into GitHub Copilot Agent mode inside a project folder the user has
   already created and opened, e.g. via `mkdir tool-chat-test && cd
   tool-chat-test && code .`. Do NOT create a dated subfolder or any other
   wrapper folder.)
   - `app.py` — the whole app (UI + logic + the two tool functions). One file
     is fine at this scope.
   - `requirements.txt` — `streamlit`, `openai`, `python-dotenv`
   - `.env` — as specified in CONTEXT above (real file, empty key value)
   - `.env.example` — same content as `.env`, plus a comment on where to get
     a key
   - `.streamlit/config.toml` — a clean, modern light theme (indigo/violet
     primary color, generous corner radius, no harsh default red/orange)
   - `README.md` — a 3-line quickstart: install requirements, open `.env` and
     paste in the Gemini key (only needed for the Gemini provider — LM Studio
     needs no key, just LM Studio running locally with a model loaded), run
     `streamlit run app.py`

2. Branding — minimal, no extra pages or settings
   - Page title: "Dinesh AI Academy · Tool Calling Demo"
   - Header: "Dinesh AI Academy — Tool Calling Demo"
   - Footer: "Made at Dinesh AI Academy · Powered by Google Gemini & LM Studio"

3. The two tools (plain Python functions, keep them tiny and dependency-free)
   - `calculate(expression: str) -> dict` — safely evaluates a basic
     arithmetic expression (+, -, *, /, parentheses, decimals). Use Python's
     `ast` module to parse and evaluate only numeric/operator nodes — never
     call `eval()` or `exec()` on the raw string, that's a real security risk
     even in a teaching demo. Return `{"expression": ..., "result": ...}` or
     `{"expression": ..., "error": ...}` if it can't be parsed.
   - `get_weather(city: str) -> dict` — returns mock weather data for the
     given city from a small fixed lookup table (5-10 cities), with a
     reasonable fallback for cities not in the table. No real API call — make
     it look like real data, not a placeholder string.
   - Give both a clear `description` in their tool schema, since that's what
     the model reads to decide when to call them.

4. Sidebar
   - Provider picker: `st.selectbox` with the two providers from CONTEXT.
   - Connection status, re-checked whenever the provider changes (cache
     keyed on the provider, not just once globally — switching providers
     must re-check): one cheap `client.models.list()` call in a try/except.
     Show 🟢 "Connected to &lt;provider&gt;" or 🔴 "Not connected —
     &lt;short reason&gt;". For Gemini, a missing/empty key should produce a
     clear reason like "no API key in .env" rather than a raw exception
     string. For LM Studio, a connection failure should suggest "make sure LM
     Studio is running with a model loaded". If not connected, still render
     the rest of the app — don't `st.stop()`.
   - Model picker: for Gemini, the 3 hardcoded ids; for LM Studio, the live
     list from `client.models.list()` (empty list if not connected — show a
     placeholder in that case, don't crash).
   - A "Tool-Call Trace" toggle (`st.checkbox`, default on) that controls
     whether the trace panel (see below) is shown under replies.
   - "Clear conversation" button: resets `st.session_state.messages = []` and
     reruns.

5. Chat
   - `st.chat_input` + `st.chat_message`, full history in `st.session_state`.
   - Run the tool-calling loop from CONTEXT on each question.
   - When the "Tool-Call Trace" toggle is on, show an `st.expander("Tool-call
     trace")` under each assistant reply laying out, step by step, exactly
     what happened that turn (built from the trace list recorded during the
     loop):
     1. User request (the question asked)
     2. Whether the model decided a tool was needed
     3. If yes: which tool was selected, for each tool call
     4. The arguments the model generated for it
     5. The tool's actual return value
     6. That the result was sent back to the model
     7. The model's final response
     If no tool was needed, say so plainly instead of showing empty
     tool/argument/result fields.
   - Wrap each turn in one try/except. On any error, show one friendly
     `st.error` (e.g. "Something went wrong — try again in a moment, or
     switch providers in the sidebar to check if it's provider-specific.")
     and keep the chat history intact — never a raw traceback.

6. Explicitly do NOT build any of this (keep it fast and simple — these are
   good ideas for the practice challenge afterward, not the base build):
   - No third tool (e.g. current time, currency conversion, stock price) —
     that's left as a follow-up exercise for the user to add themselves
   - No LangChain or other third-party agent framework
   - No real weather API or any second API key
   - No multi-tab layout, no PDF upload, no vector database
   - No temperature slider, no system prompt editor

FORMAT — what "done" looks like:
- Write the files directly in the current folder — do NOT paste the full
  contents of each file into the chat as code blocks. Just create them and
  tell me their paths in one short list.
- Run `pip install -r requirements.txt` and `streamlit run app.py`.
- Confirm the local URL and tell me to open it in my browser.
- Before declaring done, verify the app actually works, using whichever
  provider you can — since `.env` has no real Gemini key yet, that means
  testing against **LM Studio** if it's running locally, or, if it's not,
  at minimum confirming the app loads cleanly with both providers showing
  "not connected" and no crash. If LM Studio is reachable, actually send a
  question that needs the calculator, one that needs the weather tool, and
  one that needs neither — confirm all three complete without an exception
  and that the Tool-Call Trace panel correctly reflects what happened each
  time.
- If something fails, fix it yourself and re-run — don't stop and just report it.

Do not ask clarifying questions. Build exactly this scope — nothing more, nothing
less — and get it running as fast as possible, with no errors.
