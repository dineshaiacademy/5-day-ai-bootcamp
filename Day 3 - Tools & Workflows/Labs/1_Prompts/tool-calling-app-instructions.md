# Instructions: Tool Calling Demo (Gemini + LM Studio, Streamlit)

This is the prompt referenced by the "🛠️ Hands-On Practice: Build a Tool-Calling
AI Chat App" page on the course LMS — the steps below pick up from that page's
step 6 ("Use the AI Engineering Prompt"). If you haven't done steps 1-5 there yet
(installing Python, getting a Gemini key, installing VS Code + GitHub Copilot),
do those first.

## How to use the prompt
1. Create and open a fresh project folder, exactly as the LMS page describes:
   ```bash
   mkdir tool-chat-test
   cd tool-chat-test
   code .
   ```
2. In VS Code, open GitHub Copilot Chat and switch it to **Agent mode**. Make
   sure you're working inside the `tool-chat-test` folder.
3. Open [`tool-calling-app-prompt.md`](tool-calling-app-prompt.md), copy the
   entire file contents as-is, and paste it into Copilot Chat.
4. Let Copilot create the files directly in `tool-chat-test/` (no extra
   subfolder — the prompt is written to do this), install dependencies, and
   run the app.

## Expected files
```text
tool-chat-test/
│
├── app.py
├── requirements.txt
├── .env
├── .env.example
├── README.md
│
└── .streamlit/
    └── config.toml
```

## Before you start
- Get a free Gemini API key at https://aistudio.google.com/apikey.
- Copilot creates a real `.env` file for you with `GEMINI_API_KEY=` already in
  it — just open it and paste your key after the `=`. No copying or renaming
  needed. (LM Studio doesn't need a key at all — just have LM Studio running
  locally with a model loaded.)

## Two providers, on purpose
This app can talk to **Gemini (cloud)** or **LM Studio (local)**, switchable
from a sidebar dropdown. That's not just a nice-to-have — it's a debugging
tool. If something goes wrong (a bad/expired key, hitting a rate limit, a
model id that's been retired), switch providers and try the same question
again:
- Still broken on LM Studio too → the bug is in the app itself.
- Works fine on LM Studio but not Gemini → the problem is on the Gemini side
  specifically (key, quota, model availability), not your code.

## What this app is showing
The core mechanic behind every "AI agent" or "tool calling" demo:
```text
User → LLM → Tool Selection → Tool Execution → LLM → Final Response
```
The model gets told what tools it *could* use (a calculator and a weather
lookup here), decides for itself whether a question needs one, and your own
code runs the tool and hands the result back. Turn on the **Tool-Call Trace**
option in the sidebar to see the full flow for each reply: whether a tool was
needed, which one, what arguments were generated, what it returned, and how
that fed into the final answer.

Remember: **the LLM never actually runs the tool itself.** It decides "I need
this tool," your application executes it, and the result goes back to the LLM
to generate the final response. That's the whole architecture.

## Try it with
These are the exact three examples from the LMS practice page:

- **Example 1 — Calculator tool:** "What's 47 times 89?" → the trace should
  show `calculate` was called, and the final answer should be **4,183**.
- **Example 2 — Weather tool:** "What's the weather in Delhi?" → the trace
  should show `get_weather` was called with `"Delhi"` (this app's weather data
  is simulated, not live — that's expected, the point is watching the tool
  get selected and called).
- **Example 3 — No tool required:** "Explain what an AI tool is." → the trace
  should show no tool was called — the model answers directly.

For a fuller demo script with more examples, see
[`../4_Testing/test-questions-and-answers.md`](../4_Testing/test-questions-and-answers.md).

## 🏆 Practice challenge
Once the guided app is working, try adding one more tool yourself and see if
the model automatically decides when to use it — for example
`get_current_time()`, `convert_currency()`, or `get_stock_price()`. This isn't
part of the base build on purpose: working out how to add a tool yourself (a
new function + its schema + wiring it into the same loop) is the point of the
exercise.

## If you want the fuller version
This lab is intentionally minimal — two tools, two providers, no LangChain. A
more complete version of the same idea (four tools, a "Plain Chat vs Tools +
Workflow" toggle, the full request/response JSON shown per step) already
exists in this repo at
[`../../Projects/tool-workflow-chat`](../../Projects/tool-workflow-chat) — this
lab's provider-switching and tool-loop pattern is deliberately modeled on that
working app, so it's worth comparing once this minimal build is working, to
see how the same mechanic scales up.
