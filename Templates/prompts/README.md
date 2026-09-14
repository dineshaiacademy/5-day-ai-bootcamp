# 🧩 Prompts

Copy-paste prompts for building a chat app with an AI coding assistant.

- **`01` and `02`** are for the "same prompt, different LLM" exercise — run one
  prompt through Gemini, Claude, and DeepSeek and compare the output. Each fully
  specifies imports, variable names, strings, and structure so a compliant model
  produces the same `app.py` regardless of which LLM writes it.
- **`03`** is different on purpose: a natural-language spec (not exact code) for
  a polished, real-looking chat app, so the AI has room to make design decisions
  — the way you'd actually brief an assistant to build something you'll use, not
  just compare.

## Available prompts

| Prompt | Produces |
|---|---|
| [`01-streamlit-chat-ui-no-llm.md`](01-streamlit-chat-ui-no-llm.md) | A Streamlit chat UI with a fixed placeholder reply — no API calls |
| [`02-streamlit-chat-ui-with-llm.md`](02-streamlit-chat-ui-with-llm.md) | The same UI wired to a real LLM call via the OpenAI SDK |
| [`03-premium-chat-ui-lm-studio.md`](03-premium-chat-ui-lm-studio.md) | A polished, ChatGPT/Claude-style chat app running fully offline against a local model via LM Studio — a natural-language spec, not exact code, so the AI has room to make it look premium |

## How to use

1. Open the `.md` file and copy everything below the `---` line.
2. Paste it as-is into Gemini, Claude, or DeepSeek — don't edit the wording.
3. Save the returned code as `app.py` in your project folder (see [`../streamlit-basic/`](../streamlit-basic) for `requirements.txt` / `.env.example` you can reuse).
4. Compare the files different classmates got from different LLMs — they should be identical.

If two models genuinely produce different code from the same prompt, that's worth
discussing: which instruction was ambiguous enough to allow it?
