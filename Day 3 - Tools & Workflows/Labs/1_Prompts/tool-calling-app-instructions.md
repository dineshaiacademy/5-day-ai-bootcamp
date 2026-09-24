# Instructions: Tool Calling Demo (Gemini + Streamlit)

## How to use the prompt
1. Open [`tool-calling-app-prompt.md`](tool-calling-app-prompt.md).
2. Copy the entire file contents as-is — don't edit the wording.
3. Paste it into GitHub Copilot Chat and send it.
4. Copilot will create a new dated folder (e.g. `ai_app_2026_09_24`) containing
   the full app, install dependencies, and run it for you.

## Where the app ends up
Each run creates a fresh, self-contained folder named `ai_app_<date>` (underscore
date format, e.g. `ai_app_2026_09_24`) so re-running the prompt on a different day
never overwrites a previous build.

## Before you start
- Get a free Gemini API key at https://aistudio.google.com/apikey.
- Put it in the app's `.env` file **before** you run it (copy `.env.example` to
  `.env` inside the generated `ai_app_<date>` folder, then set
  `GEMINI_API_KEY=...`). There's no way to enter a key from the browser — if
  it's missing, the fix is to edit `.env` and restart the app.

## What this app is showing
The core mechanic behind every "AI agent" or "tool calling" demo: the model gets
told what tools it *could* use, decides for itself whether a question needs one,
and your own code runs the tool and hands the result back. There are exactly two
tools — a calculator and a current-date-time lookup — kept deliberately simple so
the mechanism stays visible instead of getting lost in a big toolset. The "How
this reply was generated" panel under each answer shows exactly what happened:
which tool was called (if any), with what arguments, and what it returned.

## Try it with
Ask these three kinds of questions and check the panel under each answer:

- **Needs the calculator:** "What is 4562 multiplied by 8917?" → the panel
  should show `calculator` was called with that expression, and the answer
  should match the correct product (40,679,354).
- **Needs the date/time tool:** "What's today's date and the exact time right
  now?" → the panel should show `get_current_datetime` was called, and the
  answer should match the real current time.
- **Needs no tool at all:** "What's the capital of France?" or "Explain what a
  system prompt is." → the panel should say no tool was needed — the model
  answered directly from its own knowledge.

For a fuller demo script with expected answers, see
[`../4_Testing/test-questions-and-answers.md`](../4_Testing/test-questions-and-answers.md).

## If you want the fuller version
This lab is intentionally minimal — two tools, Gemini only, no LangChain. A
much more complete version of this same idea (multiple providers including a
local LM Studio option, a "Plain Chat vs Tools + Workflow" toggle, full
request/response JSON shown per step) already exists in this repo at
[`../../Projects/tool-workflow-chat`](../../Projects/tool-workflow-chat) — worth
comparing once this minimal build is working, to see how the same mechanic
scales up.
