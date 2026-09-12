# 🧠 Skills

Reusable prompts for regenerating this project (or similar ones) with any LLM.

## `build-premium-chat-app.md`

A self-contained "master prompt" that instructs an LLM to build a premium, ChatGPT-style Streamlit chat app powered by the Gemini API — with clean architecture, beginner-friendly comments, and secure key handling.

**How to use it:**

1. Open [`build-premium-chat-app.md`](build-premium-chat-app.md).
2. Copy everything under the `---` line.
3. Paste it into any LLM chat (Claude, ChatGPT, Gemini, DeepSeek, a local model in LM Studio — any of them).
4. Save the generated `app.py`, `requirements.txt`, `.env.example`, and `README.md` into this project's root folder (one level up from `skills/`).
5. Copy `.env.example` to `.env` and fill in your `GAISTUDIO_API_KEY`.
6. Run:
   ```bash
   pip install -r requirements.txt
   streamlit run app.py
   ```

The prompt is model-agnostic by design — running it through a different LLM should still produce a working app that meets the same acceptance criteria, even if the exact code differs.
