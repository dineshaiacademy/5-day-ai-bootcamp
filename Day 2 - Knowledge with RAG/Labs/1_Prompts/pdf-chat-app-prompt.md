ROLE
Act as a senior full-stack AI engineer building a polished, production-quality demo
app for "Dinesh AI Academy" — a hands-on AI engineering bootcamp.

TASK
Build a complete, runnable Streamlit chat application that lets a user upload a PDF
and ask questions about its contents, answered by Google's Gemini API. When you're
done, install the dependencies and run the app so it opens in my browser.

CONTEXT
- This is a teaching artifact for a "Day 2: RAG & Document Q&A" workshop — it must
  look professional and premium, not like a rough prototype.
- I have (or will get) a free Gemini API key from https://aistudio.google.com/apikey.
- Target stack: Python 3.10+, Streamlit, the official `google-genai` Python SDK,
  `pypdf` for text extraction.
- The app must run entirely locally with `streamlit run app.py`.
- Before creating any files, create a new folder named `ai_app_<date>`, where
  `<date>` is today's date in `YYYY_MM_DD` format (a filesystem-safe name, e.g.
  `ai_app_2026_09_22` — no spaces, slashes, colons, or hyphens; underscores only).
  Create every file listed
  below inside that folder, not in the current directory. All terminal commands
  (`pip install`, `streamlit run`, etc.) must also be run from inside that folder.
- Keep retrieval simple and dependency-light: no vector database required — chunk
  the PDF text and either (a) stuff relevant chunks into the prompt using a
  lightweight keyword/embedding similarity search, or (b) for smaller PDFs, pass
  the full extracted text as context. Use Gemini's embedding model
  (`text-embedding-004` or current equivalent) for chunk retrieval if you implement
  similarity search — check the SDK/docs for the exact current model id.

REQUIREMENTS — build exactly this:

1. Project files — all inside the `ai_app_<date>` folder described above
   - `ai_app_<date>/app.py` — the full Streamlit application (see spec below)
   - `ai_app_<date>/pdf_utils.py` — PDF text extraction, chunking, and retrieval
     helper functions (keep `app.py` focused on UI/orchestration)
   - `ai_app_<date>/requirements.txt` — pinned to at least `streamlit`,
     `google-genai`, `pypdf`, `python-dotenv`, `numpy`
   - `ai_app_<date>/.env.example` — documents `GEMINI_API_KEY=` with a one-line
     comment on where to get one
   - `ai_app_<date>/.streamlit/config.toml` — a clean, modern light theme
     (indigo/violet primary color, generous corner radius, no harsh default red/
     orange)
   - `ai_app_<date>/README.md` — a 5-line quickstart: create a venv, install
     requirements, copy `.env.example` to `.env` and add the key, run
     `streamlit run app.py`

2. Branding
   - Browser tab title: "Dinesh AI Academy · PDF Chat"
   - App header: "Dinesh AI Academy — Chat With Your PDF" with a one-line subtitle:
     "Built live in a hands-on session — Day 2: RAG & Document Q&A"
   - Footer caption: "Made at Dinesh AI Academy · Powered by Google Gemini"

3. Sidebar (settings + upload, not main content)
   - API key handling (this must work correctly — be precise, do not just show a
     disabled/read-only field):
     - On startup, try to read `GEMINI_API_KEY` from `.env` via `python-dotenv`.
     - If found, store it in `st.session_state["api_key"]` and show a green
       "Connected via .env" status. Do NOT show the paste-a-key input in this case
       (or show it collapsed/optional for overriding).
     - If NOT found, show a clear message with the exact next steps, not just
       "no key found" — e.g. "No API key found. 1) Get a free key at
       https://aistudio.google.com/apikey  2) Paste it below to use it for this
       session, or add it to `.env` as `GEMINI_API_KEY=...` and restart the
       app." Then show an `st.text_input(..., type="password")` for the user
       to paste a key. This input must remain fully editable and enabled at
       all times — never set `disabled=True` on it, and never gate it behind
       any other condition.
     - As soon as the user pastes a key and presses Enter/leaves the field, save it
       to `st.session_state["api_key"]` (not to disk, not to `.env`) and
       immediately re-initialize the Gemini client with it — do not require a page
       reload or a separate "connect" button unless you also wire that button up
       correctly to actually update the client.
     - The status indicator (connected/not connected) must be derived from whether
       `st.session_state["api_key"]` is set and valid — not from whether `.env` had
       a key. Test this path explicitly: env var missing → paste key in UI → chat
       becomes usable in the same session without restarting the app.
     - Do not use a `st.form` for this unless every widget inside it is also wired
       to a submit button — a lone `text_input` inside an unsubmitted form is a
       common bug that makes the field appear to do nothing.
   - PDF uploader (`st.file_uploader`, type=["pdf"], single file at a time)
   - After upload: show file name, page count, and a short "Processing…" spinner
     while the PDF is extracted and chunked; then a green "Ready to chat" confirmation
   - Model picker: a dropdown that discovers models live once a key is available,
     rather than trusting a model id baked into this prompt that will go stale as
     Google ships new versions. Specifically:
     - Keep a small hardcoded fallback list of well-known flash model ids (2-3
       entries) for the case where no key is connected yet — model discovery
       needs a valid key to call, so before that, show the dropdown populated
       from this fallback list (clearly usable, not disabled — the user may
       already know which id they want).
     - As soon as a valid key is connected (from `.env` or pasted), call the
       `google-genai` SDK's model-listing method (e.g. `client.models.list()`)
       exactly once, filter the results to flash-tier models (id contains
       "flash"), and cache that list in `st.session_state` so it isn't
       re-fetched on every rerun.
     - Once the live list is cached, use it to populate the dropdown instead of
       the fallback list.
     - If the live listing call fails (network error, permissions), keep using
       the fallback list, but show a clear, actionable `st.warning` right next
       to the model picker explaining what happened and exactly what to do
       next — for example: "Couldn't load the live model list, showing common
       defaults instead. This usually means the API key doesn't have
       permission to list models, or there's a network issue — try again in a
       moment, or pick a model from this list and continue." Never a raw
       traceback, and never a silent failure the user has to notice on their
       own.
   - Temperature slider (0.0-2.0, default 0.3 — lower default since this is a
     grounded Q&A task, not creative chat)
   - "Clear document & conversation" button that resets everything (uploaded file,
     extracted text, chat history)
   - A connection status indicator with three distinct states, each with its own
     icon/color and a one-line next step so the user is never left guessing:
     - "Connected" (green) — key is set and the first API call succeeded.
     - "Not connected — no key yet" (yellow/grey) — shown when no key is set.
       Message: "Paste your API key above, or add it to `.env` and restart."
     - "Not connected — key rejected" (red) — shown when a key is set but a
       call failed with an auth error. Message: "That key wasn't accepted.
       Double-check you copied it fully with no extra spaces, or get a new one
       at https://aistudio.google.com/apikey."

4. Main chat area
   - Before a key is connected: disable `st.chat_input` and the PDF uploader,
     and show the same connection status message from the sidebar in the main
     area too — the user should see what to do next no matter where they're
     looking.
   - Once connected but before any PDF is uploaded: show a friendly empty state
     ("Upload a PDF in the sidebar to get started — I'll answer questions about
     it.") and keep `st.chat_input` disabled
   - Once a PDF is processed: use `st.chat_message` and `st.chat_input` — never a
     custom-built chat UI
   - Keep the full conversation history in `st.session_state`, scoped per-uploaded-
     document (clear history if a new PDF is uploaded)
   - On each question: retrieve the most relevant chunk(s) from the PDF, inject them
     into a system/context prompt instructing Gemini to answer only from the
     provided document content, and stream the response token-by-token with
     `st.write_stream` using Gemini's real streaming API — not a fake typewriter
     effect
   - If the answer isn't found in the document, the model should say so plainly
     rather than guessing — encode this in the system prompt
   - Show which page(s) the answer was likely drawn from as a small caption under
     the response, when determinable from chunk metadata
   - This error handling applies at every turn of the conversation, not just the
     first question — a failure on question 5 must be caught exactly the same
     way as a failure on question 1. Wrap the streaming call in a try/except
     and catch errors that occur mid-stream too, not just on the initial
     request.
   - When any error happens: keep the existing conversation history intact (do
     not clear `st.session_state` messages), show the error as its own
     `st.chat_message("assistant")` entry (not a stray banner disconnected from
     the conversation) with a clear explanation and exactly what to do next,
     and leave `st.chat_input` enabled so the user can immediately retry —
     never a raw traceback, and never a bare "an error occurred":
     - Invalid/rejected key: "Your API key wasn't accepted — check it in the
       sidebar, or get a new one at https://aistudio.google.com/apikey."
     - Rate limit: "You've hit Gemini's rate limit — wait a few seconds and
       send your question again."
     - Network error: "Couldn't reach Gemini — check your internet connection
       and try again."
     - Model unavailable / not found / decommissioned (e.g. the selected model
       id no longer exists or is temporarily overloaded): "The model
       '<model id>' isn't available right now — pick a different model from
       the sidebar dropdown and try again, or refresh the page to reload the
       current model list."
     - Corrupt/unreadable PDF: "Couldn't read that PDF — try re-exporting it
       or uploading a different file."
     - Scanned/image-only PDF with no extractable text: "This PDF looks like
       scanned images with no selectable text, so there's nothing to search —
       try a text-based PDF instead."
     - Anything else: a plain-language summary of what went wrong plus "try
       again, and if it keeps happening, check the Gemini API status page."

5. Polish
   - `layout="wide"`, with a fitting icon in `st.set_page_config`
   - Sentence-case labels everywhere — no ALL CAPS or Title Case shouting
   - No lorem-ipsum placeholder text anywhere — every string must be final, real copy
   - Show a subtle progress indicator during PDF chunking for larger files

FORMAT — what "done" looks like:
- Create the `ai_app_<date>` folder first, before writing any files.
- Show me the full contents of every file you create, in code blocks, before running
  anything, with each file's path prefixed by `ai_app_<date>/`.
- Then, from inside the `ai_app_<date>` folder, run `pip install -r requirements.txt`
  and `streamlit run app.py` in the terminal.
- Confirm the local URL it's running on and tell me to open it in my browser.
- If anything fails (missing key, import error, PDF parsing issue), fix it yourself
  and re-run — don't just report the error and stop.

Do not ask me clarifying questions — make reasonable choices for anything not
specified above and build the complete, working app now.
