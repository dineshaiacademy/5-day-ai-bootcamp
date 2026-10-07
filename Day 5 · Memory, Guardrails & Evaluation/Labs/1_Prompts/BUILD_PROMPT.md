ROLE
Act as a senior full-stack AI engineer building a polished, production-quality
"safe chat" demo app for "Dinesh AI Academy" — a hands-on AI engineering
bootcamp. This is the capstone exercise for the final day.

TASK
Build a complete, runnable Streamlit chat application that has REAL memory
management and REAL input/output guardrails — not just a plain chatbot. When
you're done, install the dependencies and run the app so it opens in my browser.

CONTEXT
- This is a teaching artifact for a "Day 5: Memory, Guardrails & Evaluation"
  workshop — it must look professional and premium, not like a rough prototype.
- I have (or will get) a free Gemini API key from https://aistudio.google.com/apikey.
- Target stack: Python 3.10+, Streamlit, the official `google-genai` Python SDK.
- The app must run entirely locally with `streamlit run app.py`.

REQUIREMENTS — build exactly this:

1. Project files
   - `app.py` — the full Streamlit application (see spec below)
   - `requirements.txt` — pinned to at least `streamlit`, `google-genai`,
     `python-dotenv`
   - `.env.example` — documents `GEMINI_API_KEY=` with a one-line comment on where
     to get one
   - `.streamlit/config.toml` — a clean, modern light theme (indigo/violet primary
     color, generous corner radius, no harsh default red/orange)
   - `README.md` — a 5-line quickstart: create a venv, install requirements, copy
     `.env.example` to `.env` and add the key, run `streamlit run app.py`

2. Branding
   - Browser tab title: "Dinesh AI Academy · Safe Chat Studio"
   - App header: "Dinesh AI Academy — Safe Chat Studio" with a one-line subtitle:
     "Built live in a hands-on session — Day 5: Memory, Guardrails & Evaluation"
   - Footer caption: "Made at Dinesh AI Academy · Powered by Google Gemini"

3. Sidebar (settings only, not main content)
   - Read `GEMINI_API_KEY` from `.env` via `python-dotenv`; if missing, show a
     clear error with a link to get one, plus a text input to paste a key for this
     session only (never persisted to disk)
   - A "Memory window" slider (2-10 recent exchanges kept, default 6)
   - A small connected/not-connected status indicator

4. Main chat area
   - Use `st.chat_message` and `st.chat_input` — never a custom-built chat UI
   - Keep the full conversation history in `st.session_state`, but only resend the
     last N exchanges (per the memory-window slider) to the model — a real
     sliding-window strategy, exactly like today's Memory Strategies tab
   - INPUT GUARDRAIL: before calling the model, check the user's message against
     a small hardcoded blocklist of clearly disallowed phrases; if it matches,
     show a clear "blocked" message instead of calling the model at all
   - OUTPUT GUARDRAIL: after generating a reply, run it through a simple regex-based
     PII redactor (emails and phone numbers at minimum) before displaying it, and
     show the user how many items were redacted (if any)
   - Show a friendly welcome message before the first user message
   - Handle API errors gracefully (invalid key, rate limit, network) with a clear
     `st.error` — never a raw traceback

5. Polish
   - `layout="wide"`, with a fitting icon in `st.set_page_config`
   - Sentence-case labels everywhere — no ALL CAPS or Title Case shouting
   - No lorem-ipsum placeholder text anywhere — every string must be final, real copy

FORMAT — what "done" looks like:
- Show me the full contents of every file you create, in code blocks, before running
  anything.
- Then run `pip install -r requirements.txt` and `streamlit run app.py` in the
  terminal.
- Confirm the local URL it's running on and tell me to open it in my browser.
- If anything fails (missing key, import error), fix it yourself and re-run — don't
  just report the error and stop.

Do not ask me clarifying questions — make reasonable choices for anything not
specified above and build the complete, working app now.