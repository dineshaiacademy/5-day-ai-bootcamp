# Instructions: PDF Chat App (Gemini + Streamlit) — minimal build

## How to use the prompt
1. Open [`pdf-chat-app-prompt.md`](pdf-chat-app-prompt.md).
2. Copy the entire file contents as-is — don't edit the wording.
3. Paste it into GitHub Copilot Chat and send it.
4. Copilot will create a new dated folder (e.g. `ai_app_2026_09_22`) containing
   the full app, install dependencies, and run it for you. This version is
   intentionally scoped down to just the core pipeline, so it should build in
   well under 2 minutes.

## Where the app ends up
Each run creates a fresh, self-contained folder named `ai_app_<date>` (underscore
date format, e.g. `ai_app_2026_09_22`) so re-running the prompt on a different day
never overwrites a previous build.

## Before you start
- Get a free Gemini API key at https://aistudio.google.com/apikey.
- Put it in the app's `.env` file **before** you run it (copy `.env.example` to
  `.env` inside the generated `ai_app_<date>` folder, then set
  `GEMINI_API_KEY=...`). There's no way to enter a key from the browser — if
  it's missing, the fix is to edit `.env` and restart the app.

## What this build does — and doesn't do
The core RAG pipeline, plus a few small usability pieces: a connection status
indicator, a chat model picker, and a "Clear conversation" button. Everything
heavier from earlier versions (multi-tab layout, an Architecture & Flow view, a
Demo Questions view, live model discovery via an API call, vector-store stats,
retrieved-chunk expanders) was deliberately cut to keep the build fast and the
app simple. If you want any of those back later, they can be added on top of
this once the core pipeline is confirmed working.

## Two chat modes — try both, to prove both work
- **No PDF uploaded** — ask anything and Gemini answers directly from its own
  knowledge (no retrieval). The answer is labeled "💬 Answered from general
  knowledge — no PDF uploaded". This proves the API connection itself works,
  independent of the PDF pipeline.
- **PDF uploaded** — ask about the document and the answer is grounded in the
  top-3 retrieved chunks. The answer is labeled "📄 Answered using your PDF".

Try asking something with no PDF uploaded first (e.g. "What is a token in an
LLM?"), then upload the sample PDF and ask a document-specific question — you
should see the label under each answer change accordingly.

## Try it with
Once the app is running, upload `../2_Docs/Dinesh_AI_Academy_Policies.pdf` and ask
questions like:

- "What's the attendance policy?"
- "If I cancel 3 days before the bootcamp starts, do I get a refund?"
- "Do I need a GPU for this bootcamp?"
- "How do I get a certificate?"
- "What's your policy on pets in the classroom?" (should say this isn't covered)

For a fuller demo script with expected answers, see
[`../4_Testing/test-questions-and-answers.md`](../4_Testing/test-questions-and-answers.md).

## Re-uploading a PDF
This build clears and rebuilds the Chroma collection on every upload (no
reuse/caching), so re-uploading the same file re-embeds it from scratch each
time — that's expected at this scope, not a bug.
