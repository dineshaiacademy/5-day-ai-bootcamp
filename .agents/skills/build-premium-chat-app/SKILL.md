---
name: build-premium-chat-app
description: Use when the user asks to build, create, scaffold, or generate a ChatGPT-style chat application, an AI chatbot UI, or a polished/premium LLM-powered chat interface — especially one using Streamlit and the Gemini API. Triggers: "build a chat app", "chatgpt clone", "gemini chat app", "streamlit chatbot", "premium chat UI", "ai chat interface", "chat application".
---

# Build a Premium ChatGPT-Style Chat App

Read `references/spec.md` for the full build specification (architecture, UI/UX requirements, code quality bar, security rules, and acceptance criteria) before writing any code, then generate the app exactly to that spec.

## Quick Summary

- **Stack:** Streamlit + `google-genai` (Gemini API) + `python-dotenv` reading `GAISTUDIO_API_KEY`
- **Deliverables:** `app.py`, `requirements.txt`, `.env.example`, `README.md`
- **Non-negotiables:** streaming responses, a layered architecture with visible section comments (config → LLM client → state → UI → orchestration), live sidebar settings (temperature, max tokens, system prompt), real token usage read from the API response, no hardcoded or logged secrets

## Where to Save the Output

Save the generated files into a **new project folder** under the relevant day's `Projects/` directory (e.g. `Day 1 - LLM Fundamentals/Projects/<project-name>/`) — never inside this skill folder.

## Verify Before Reporting Done

Check the generated app against every item in `references/spec.md`'s Acceptance Criteria section. If a real `GAISTUDIO_API_KEY` is available in the project's `.env`, actually run `streamlit run app.py` and exercise the chat, the sidebar settings, and the clear-conversation button rather than assuming the code works.
