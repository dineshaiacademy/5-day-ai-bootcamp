# Instructions: PDF Chat App (Gemini + Streamlit)

## How to use the prompt
1. Open [`pdf-chat-app-prompt.md`](pdf-chat-app-prompt.md).
2. Copy the entire file contents as-is — don't edit the wording.
3. Paste it into GitHub Copilot Chat and send it.
4. Copilot will create a new dated folder (e.g. `ai_app_2026_09_22`) containing
   the full app, install dependencies, and run it for you.

## Where the app ends up
Each run creates a fresh, self-contained folder named `ai_app_<date>` (underscore
date format, e.g. `ai_app_2026_09_22`) so re-running the prompt on a different day
never overwrites a previous build.

## Before you start
- Get a free Gemini API key at https://aistudio.google.com/apikey.
- Have it ready to paste into the app's `.env` file (copy `.env.example` to `.env`
  inside the generated `ai_app_<date>` folder, then set `GEMINI_API_KEY=...`).

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
