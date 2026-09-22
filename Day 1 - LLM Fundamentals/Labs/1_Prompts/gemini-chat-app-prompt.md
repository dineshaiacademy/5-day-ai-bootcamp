ROLE
Act as a senior full-stack AI engineer building a polished, production-quality demo
app for "Dinesh AI Academy" — a hands-on AI engineering bootcamp.

TASK
Build a complete, runnable Streamlit chat application that talks to Google's Gemini
API. When you're done, install the dependencies and run the app so it opens in my
browser.

CONTEXT
- This is a teaching artifact for a "Day 1: LLM Fundamentals" workshop — it must
  look professional and premium, not like a rough prototype.
- I have (or will get) a free Gemini API key from https://aistudio.google.com/apikey.
- Target stack: Python 3.10+, Streamlit, the official `google-genai` Python SDK.
- The app must run entirely locally with `streamlit run app.py`.
- Before creating any files, create a new folder named `ai_app_<date>`, where
  `<date>` is today's date in `YYYY_MM_DD` format (a filesystem-safe name, e.g.
  `ai_app_2026_09_22` — no spaces, slashes, colons, or hyphens; underscores only).
  Create every file listed below inside that folder, not in the current directory.
  All terminal commands (`pip install`, `streamlit run`, etc.) must also be run
  from inside that folder.

REQUIREMENTS — build exactly this:

1. Project files — all inside the `ai_app_<date>` folder described above
   - `ai_app_<date>/app.py` — the full Streamlit application (see spec below)
   - `ai_app_<date>/requirements.txt` — pinned to at least `streamlit`,
     `google-genai`, `python-dotenv`
   - `ai_app_<date>/.env.example` — documents `GEMINI_API_KEY=` with a one-line
     comment on where to get one
   - `ai_app_<date>/.streamlit/config.toml` — a clean, modern light theme
     (indigo/violet primary color, generous corner radius, no harsh default red/
     orange)
   - `ai_app_<date>/README.md` — a 5-line quickstart: create a venv, install
     requirements, copy `.env.example` to `.env` and add the key, run
     `streamlit run app.py`

2. Branding
   - Browser tab title: "Dinesh AI Academy · Gemini Chat"
   - App header: "Dinesh AI Academy — Gemini Chat Studio" with a one-line subtitle:
     "Built live in a hands-on session — Day 1: LLM Fundamentals"
   - Footer caption: "Made at Dinesh AI Academy · Powered by Google Gemini"

3. Sidebar (settings only, not main content)
   - API key handling (this must work correctly — be precise, do not just show a
     disabled/read-only field):
     - On startup, try to read `GEMINI_API_KEY` from `.env` via `python-dotenv`.
     - If found, store it in `st.session_state["api_key"]` and show a green
       "Connected via .env" status. Do NOT show the paste-a-key input in this case
       (or show it collapsed/optional for overriding).
     - If NOT found, show a clear error with a link to
       https://aistudio.google.com/apikey, plus an `st.text_input(..., type="password")`
       for the user to paste a key for this session only (never persisted to disk).
       This input must remain fully editable and enabled at all times — never set
       `disabled=True` on it, and never gate it behind any other condition.
     - As soon as the user pastes a key and presses Enter/leaves the field, save it
       to `st.session_state["api_key"]` and immediately re-initialize the Gemini
       client with it — do not require a page reload or a separate "connect"
       button unless you also wire that button up correctly to actually update
       the client.
     - The status indicator (connected/not connected) must be derived from whether
       `st.session_state["api_key"]` is set and valid — not from whether `.env`
       had a key. Test this path explicitly: env var missing → paste key in UI →
       chat becomes usable in the same session without restarting the app.
     - Do not use a `st.form` for this unless every widget inside it is also wired
       to a submit button — a lone `text_input` inside an unsubmitted form is a
       common bug that makes the field appear to do nothing.
   - Model picker: a dropdown of current Gemini flash-tier models (check the
     `google-genai` SDK/docs for the exact current model ids — e.g. `gemini-3.5-flash`
     and `gemini-3.5-flash-lite`, or newer if available)
   - Temperature slider (0.0-2.0, default 0.7)
   - System prompt text area (editable, default: "You are a friendly, knowledgeable
     teaching assistant for Dinesh AI Academy. Answer clearly and concisely.")
   - "Clear conversation" button that resets chat history
   - A small connected/not-connected status indicator

4. Main chat area
   - Use `st.chat_message` and `st.chat_input` — never a custom-built chat UI
   - Keep the full conversation history in `st.session_state`
   - Stream the model's response token-by-token with `st.write_stream`, using
     Gemini's real streaming API — not a fake typewriter effect
   - Show a friendly welcome message before the first user message ("Hi! Ask me
     anything about what we covered today.")
   - Handle API errors gracefully (invalid key, rate limit, network) with a clear
     `st.error` — never a raw traceback

5. Polish
   - `layout="wide"`, with a fitting icon in `st.set_page_config`
   - Sentence-case labels everywhere — no ALL CAPS or Title Case shouting
   - No lorem-ipsum placeholder text anywhere — every string must be final, real copy

FORMAT — what "done" looks like:
- Create the `ai_app_<date>` folder first, before writing any files.
- Show me the full contents of every file you create, in code blocks, before running
  anything, with each file's path prefixed by `ai_app_<date>/`.
- Then, from inside the `ai_app_<date>` folder, run `pip install -r requirements.txt`
  and `streamlit run app.py` in the terminal.
- Confirm the local URL it's running on and tell me to open it in my browser.
- If anything fails (missing key, import error), fix it yourself and re-run — don't
  just report the error and stop.

Do not ask me clarifying questions — make reasonable choices for anything not
specified above and build the complete, working app now.
