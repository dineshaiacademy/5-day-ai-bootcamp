# Instructions: Gemini Chat Studio (Day 1)

## How to use the prompt
1. Open [`gemini-chat-app-prompt.md`](gemini-chat-app-prompt.md).
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
- You can either:
  - put it in a `.env` file inside the generated `ai_app_<date>` folder
    (`GEMINI_API_KEY=your-key-here`), or
  - paste it directly into the sidebar once the app is running — it's kept for
    that session only and never saved to disk.

## Try it with
Once the app is running and connected, ask it questions from today's session —
this is a general-purpose teaching assistant, not grounded on a specific document,
so it answers from what it already knows.

- "What is a token in the context of large language models?"
- "What does the temperature setting control when chatting with an LLM?"
- "What's the difference between a system prompt and a user message?"
- "What's today's weather in Mumbai right now?" (should admit it can't access
  real-time data, rather than guessing)
- "Who won yesterday's cricket match?" (should admit it has no access to live or
  post-training-cutoff information)

For a fuller demo script with expected answers, see
[`../4_Testing/test-questions-and-answers.md`](../4_Testing/test-questions-and-answers.md).
