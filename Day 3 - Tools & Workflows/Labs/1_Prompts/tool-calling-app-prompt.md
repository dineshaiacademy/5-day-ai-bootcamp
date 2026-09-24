ROLE
Act as a senior full-stack AI engineer building a small, fast demo app for
"Dinesh AI Academy" — a hands-on AI engineering bootcamp.

TASK
Build a minimal, runnable Streamlit chat app that demonstrates LLM tool/function
calling with Gemini: the model has exactly two tools available (a calculator and
a current-date-time lookup) and decides for itself whether a question needs one.
Every reply shows, in an expander, exactly what happened — which tool (if any)
was called, with what arguments, and what it returned — so the tool-calling loop
is visible, not a black box. Keep the scope small and the build fast.

CONTEXT
- Teaching demo for a "Day 3: Tools & Workflows" workshop.
- The Gemini API key is already in a `.env` file (`GEMINI_API_KEY=...`) — there is
  no UI for entering a key anywhere.
- Stack: Python 3.10+, Streamlit, the official `google-genai` SDK, `python-dotenv`.
- Runs locally via `streamlit run app.py`.
- Before writing any files, create a new folder named `ai_app_<date>`, where
  `<date>` is today's date as `YYYY_MM_DD` (underscores only, e.g.
  `ai_app_2026_09_24`). Put every file inside it, and run every terminal command
  from inside it.
- Model ids — use exactly these, no live discovery, no dropdown built from an
  API call (a small hardcoded list is fine and fast):
  - Chat model picker options, in this order: `gemini-3.6-flash` (default),
    `gemini-3.5-flash`, `gemini-3.5-flash-lite`.
  - Fallback (used only if the selected model's call fails): `gemini-3.5-flash`;
    if the selected model IS `gemini-3.5-flash` already, fall back to
    `gemini-3.5-flash-lite` instead — never retry the same id that just failed.
- Use the `google-genai` SDK's own function-calling/tools support (pass Python
  functions or `types.Tool`/`types.FunctionDeclaration` objects, whichever the
  installed SDK version's docs show — check it rather than guessing the exact
  shape) — do not hand-roll a custom JSON tool-call parser.

REQUIREMENTS — build exactly this, and nothing more:

1. Files (all inside `ai_app_<date>/`)
   - `app.py` — the whole app (UI + logic + the two tool functions). One file
     is fine at this scope.
   - `requirements.txt` — `streamlit`, `google-genai`, `python-dotenv`
   - `.env.example` — `GEMINI_API_KEY=` with a one-line comment on where to get
     one
   - `README.md` — a 3-line quickstart: install requirements, copy
     `.env.example` to `.env` and add the key, run `streamlit run app.py`

2. Branding — minimal, no extra pages or settings
   - Page title: "Dinesh AI Academy · Tool Calling Demo"
   - Header: "Dinesh AI Academy — Tool Calling Demo"
   - Footer: "Made at Dinesh AI Academy · Powered by Google Gemini"

3. The two tools (plain Python functions, keep them tiny and dependency-free)
   - `calculator(expression: str) -> float` — safely evaluates a basic
     arithmetic expression (+, -, *, /, parentheses, decimals). Use Python's
     `ast` module to parse and evaluate only numeric/operator nodes — never
     call `eval()` or `exec()` on the raw string, that's a real security risk
     even in a teaching demo.
   - `get_current_datetime() -> str` — returns the current local date and time
     as a readable string (e.g. `datetime.now().strftime(...)`). No arguments,
     no timezone handling needed at this scope.
   - Give both a clear docstring/description, since that's what the model
     reads to decide when to call them.

4. Sidebar
   - Connection status, checked once per session (cache the result in
     `st.session_state`, do not re-check on every rerun): one cheap
     `client.models.list()` call in a try/except right after creating the
     client. Show 🟢 "Connected to Gemini" or 🔴 "Not connected — &lt;short
     reason&gt;". If not connected, still render the rest of the app — don't
     `st.stop()`.
   - Chat model picker: `st.selectbox` with the 3 hardcoded ids from CONTEXT,
     default to the first. Store the selection in `st.session_state`.
   - "Clear conversation" button: resets `st.session_state.messages = []` and
     reruns.

5. Chat
   - `st.chat_input` + `st.chat_message`, full history in `st.session_state`.
   - On each question, run the standard tool-calling loop: send the message
     (plus history) to Gemini with both tools available; if the model responds
     with a function call, execute the matching Python function locally with
     the arguments the model provided, send the result back to the model, and
     let it produce the final answer — it may call a tool, call nothing, or
     (rarely) call both tools in sequence. Cap this at 3 round-trips total as
     a safety net against a runaway loop, then force a final plain-text
     answer.
   - Stream the final text answer with `st.write_stream`, using the fallback
     model from CONTEXT if the selected model's call fails.
   - Under each assistant reply, an `st.expander("How this reply was
     generated")` showing: "No tool was needed — answered directly" OR, for
     each tool call that happened, the tool name, the arguments the model
     chose, and the value it returned. This is the main teaching feature of
     the app — it must always be accurate to what actually happened that
     turn, not a guess.
   - Wrap each turn in one try/except. On any error, show one friendly
     `st.error` (e.g. "Something went wrong — try again in a moment.") and
     keep the chat history intact — never a raw traceback.

6. Explicitly do NOT build any of this (keep it fast and simple):
   - No LM Studio or other local-model provider support — Gemini only
   - No LangChain, no third-party agent framework — use the `google-genai`
     SDK's native tool support directly
   - No more than the 2 tools specified — no web search, no file access, no
     extra utility tools
   - No multi-tab layout, no PDF upload, no vector database
   - No live model discovery call used to populate the picker — only the one
     connection check uses `models.list()`
   - No temperature slider, no system prompt editor

FORMAT — what "done" looks like:
- Create the `ai_app_<date>` folder first.
- Write the files directly — do NOT paste the full contents of each file into
  the chat as code blocks. Just create them and tell me their paths in one
  short list.
- Run `pip install -r requirements.txt` and `streamlit run app.py` from inside
  that folder.
- Confirm the local URL and tell me to open it in my browser.
- Before declaring done, actually test all three cases yourself if you're able
  to: a question that needs the calculator, a question that needs the
  date/time tool, and a question that needs neither — confirm all three
  complete without an exception and that the "How this reply was generated"
  panel correctly reflects what happened each time.
- If something fails, fix it yourself and re-run — don't stop and just report it.

Do not ask clarifying questions. Build exactly this scope — nothing more, nothing
less — and get it running as fast as possible, with no errors.
