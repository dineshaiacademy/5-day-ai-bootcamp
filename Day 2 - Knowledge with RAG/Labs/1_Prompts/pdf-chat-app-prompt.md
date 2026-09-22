ROLE
Act as a senior full-stack AI engineer building a small, fast demo app for
"Dinesh AI Academy" — a hands-on AI engineering bootcamp.

TASK
Build a minimal, runnable Streamlit app that chats with Gemini, optionally
grounded in an uploaded PDF using a ChromaDB vector store. The app must work in
two provable modes: with no PDF uploaded (plain Gemini chat, proving the API
connection works on its own) and with a PDF uploaded (retrieval-grounded
answers, proving the RAG pipeline works). Keep the scope small and the build
fast — this has broken before from over-complexity and from silently-stale
hardcoded model ids, so follow the CONTEXT notes below exactly.

CONTEXT
- Teaching demo for a "Day 2: RAG & Document Q&A" workshop.
- The Gemini API key is already in a `.env` file (`GEMINI_API_KEY=...`) — there is
  no UI for entering a key anywhere.
- Stack: Python 3.10+, Streamlit, the `google-genai` SDK, `pypdf`, `chromadb`.
- Runs locally via `streamlit run app.py`.
- Before writing any files, create a new folder named `ai_app_<date>`, where
  `<date>` is today's date as `YYYY_MM_DD` (underscores only, e.g.
  `ai_app_2026_09_22`). Put every file inside it, and run every terminal command
  from inside it.
- Model ids — use exactly these, no live discovery, no dropdown built from an
  API call (that has caused failures before; a small hardcoded list is fine and
  fast):
  - Chat model picker options, in this order: `gemini-3.6-flash` (default),
    `gemini-3.5-flash`, `gemini-3.5-flash-lite`.
  - Chat fallback (used only if the currently-selected model's call fails):
    `gemini-3.5-flash`. If the selected model IS `gemini-3.5-flash` already,
    fall back to `gemini-3.5-flash-lite` instead — never retry the same model
    id that just failed.
  - Embedding model (no picker needed, just one id): `gemini-embedding-001`.
- Chroma collection clearing — check
  `[c.name for c in chroma_client.list_collections()]` first and only call
  `delete_collection` if the name is actually in that list. Do NOT wrap
  `delete_collection` in a bare `try/except ValueError` — recent `chromadb`
  versions raise `chromadb.errors.NotFoundError` instead, which a narrow
  `except ValueError` won't catch, crashing the first-ever upload.

REQUIREMENTS — build exactly this, and nothing more:

1. Files (all inside `ai_app_<date>/`)
   - `app.py` — the whole app (UI + logic). One file is fine at this scope;
     only split out a `pdf_utils.py` if it keeps `app.py` meaningfully cleaner.
   - `requirements.txt` — `streamlit`, `google-genai`, `pypdf`, `python-dotenv`,
     `chromadb`
   - `.env.example` — `GEMINI_API_KEY=` with a one-line comment on where to get
     one
   - `README.md` — a 3-line quickstart: install requirements, copy
     `.env.example` to `.env` and add the key, run `streamlit run app.py`

2. Branding — minimal, no extra pages or settings
   - Page title: "Dinesh AI Academy · PDF Chat"
   - Header: "Dinesh AI Academy — Chat With Your PDF"
   - Footer: "Made at Dinesh AI Academy · Powered by Google Gemini"

3. Sidebar
   - Connection status, checked once per session (cache the result in
     `st.session_state`, do not re-check on every rerun): make one cheap call
     — `client.models.list()` is fine, it doesn't generate content — inside a
     try/except right after creating the client. Show:
     - 🟢 "Connected to Gemini" if it succeeds.
     - 🔴 "Not connected — &lt;short reason from the exception&gt;" if it fails.
     If not connected, still let the rest of the app render (don't `st.stop()`)
     — the chat itself will show a clear error if someone tries to send a
     message while disconnected.
   - Chat model picker: `st.selectbox` with the 3 hardcoded ids from CONTEXT
     above, default to the first one. Store the selection in
     `st.session_state` and use it for every chat call.
   - PDF uploader (`st.file_uploader`, type=["pdf"], one file at a time).
   - After upload: a spinner while extracting/chunking/embedding/storing, then
     "Ready to chat with your PDF."
   - "Clear conversation" button: resets only the chat history
     (`st.session_state.messages = []`) and reruns. It does NOT clear the
     uploaded PDF or the Chroma collection — those stay loaded until a new PDF
     is uploaded.

4. Chat — must work in both modes, and it must be obvious to the user which
   mode answered each message
   - `st.chat_input` is enabled as soon as the app loads — it does NOT require
     a PDF to be uploaded first. The only thing that should block sending a
     message is having no working Gemini connection.
   - Keep the full conversation history in `st.session_state`, rendered with
     `st.chat_message`.
   - When a question comes in:
     - If a PDF has been uploaded and indexed (a Chroma collection exists in
       session state): embed the question, query the collection for the top 3
       chunks, inject them into a prompt instructing Gemini to answer only
       from that content (and say so plainly if the answer isn't in it), get
       the streamed answer, and show a small `st.caption("📄 Answered using
       your PDF")` right under the response.
     - If no PDF has been uploaded yet: send the question straight to Gemini
       with no retrieval step, as a normal helpful-assistant chat message, and
       show `st.caption("💬 Answered from general knowledge — no PDF
       uploaded")` right under the response. This path must work correctly on
       its own, with no PDF ever uploaded during the session — it's how the
       API connection gets proven independently of the RAG pipeline.
   - Stream every answer with `st.write_stream`, using the fallback logic from
     CONTEXT above if the selected model's call fails.
   - Wrap each turn in one try/except. On any error, show one friendly
     `st.error` (e.g. "Something went wrong — try again in a moment.") and
     keep the chat history intact — never a raw traceback.

5. Explicitly do NOT build any of this (keep it fast and simple):
   - No multi-tab layout, no Architecture/Flow view, no Demo Questions view
   - No live model discovery/listing call used to populate the picker — the 3
     ids are hardcoded, only the connection check uses `models.list()`
   - No temperature slider, no system prompt editor
   - No vector-store stats display, no "see retrieved chunks" expander, no
     page-number citations
   - No collection reuse/caching logic — just clear and rebuild on each upload

FORMAT — what "done" looks like:
- Create the `ai_app_<date>` folder first.
- Write the files directly — do NOT paste the full contents of each file into
  the chat as code blocks. Just create them and tell me their paths in one
  short list.
- Run `pip install -r requirements.txt` and `streamlit run app.py` from inside
  that folder.
- Confirm the local URL and tell me to open it in my browser.
- Before declaring done, actually test both chat modes yourself if you're able
  to: send a question with no PDF uploaded, and separately upload a PDF and
  send a question about it — confirm both complete without an exception, not
  just that the server started without crashing.
- If something fails, fix it yourself and re-run — don't stop and just report it.

Do not ask clarifying questions. Build exactly this scope — nothing more, nothing
less — and get it running as fast as possible, with no errors in either chat mode.
