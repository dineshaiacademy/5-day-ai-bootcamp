# Build Specification — Premium ChatGPT-Style App with Gemini

This spec is written to be followed directly by an LLM (this one, or any other — it's plain text and portable). It is the authoritative detail behind the summary in `SKILL.md`.

## Role

You are a senior full-stack engineer and UI/UX designer who specializes in building polished, production-quality LLM-powered applications, and who writes code specifically to teach beginners. Every design and code decision you make should be intentional and explainable.

## Objective

Build a **premium, ChatGPT-style chat application** using **Streamlit** as the frontend and the **Gemini API** (via the `google-genai` Python SDK) as the LLM backend. The app must look and feel like a real, modern AI chat product — not a bare-bones demo — while remaining simple enough that a complete beginner can read the code and understand exactly how a chat app talks to an LLM API.

## Tech Stack (non-negotiable)

- **Frontend/UI:** Streamlit (`streamlit`)
- **LLM:** Google Gemini, via the `google-genai` SDK (`from google import genai`)
- **Secrets:** `python-dotenv`, reading a `GAISTUDIO_API_KEY` environment variable — no hardcoded keys, ever
- **Language:** Python 3.10+

## Architecture & Code Organization

Separate the app into clearly distinct layers, each in its own section (or file) with a comment banner marking where it starts:

1. **Configuration & secrets layer** — loads the API key, sets constants (model name, page config).
2. **LLM client layer** — a small wrapper function/class around the Gemini client. All Gemini-specific API calls live here and nowhere else.
3. **State management layer** — Streamlit `session_state` handling: chat history, settings (temperature, system prompt), etc.
4. **UI layer** — everything the user sees: sidebar, chat bubbles, input box.
5. **Orchestration layer** — the glue that reads user input, calls the LLM client layer, updates state, and re-renders the UI.

This separation must be visible in the code itself (clear section comments), not just in your explanation — a beginner reading top to bottom should be able to point at the exact line where "the UI ends and the API call begins."

## UI/UX Requirements (premium feel)

- **Page config:** wide layout, a custom page title and favicon/icon, a clear app title and one-line subtitle.
- **Sidebar** containing:
  - A model/settings panel: temperature slider, max output tokens slider, an editable system prompt text area.
  - A **"Clear conversation"** button that resets chat history.
  - A live token-usage counter (running total for the session).
- **Chat area:**
  - User and assistant messages rendered as distinct chat bubbles using `st.chat_message` with appropriate avatars/icons.
  - Assistant responses **stream in token-by-token** (visible typing effect), not dumped all at once.
  - A persistent input box pinned at the bottom using `st.chat_input`.
  - A subtle loading indicator while waiting for the first token.
- **Polish details:** consistent spacing, a coherent color accent, empty-state messaging when the chat is new (e.g. "Ask me anything to get started"), and graceful error messages (never a raw Python traceback) if the API call fails.
- The app must look intentionally designed — not the default unstyled Streamlit look.

## Backend / LLM Integration Requirements

- Load `GAISTUDIO_API_KEY` from environment variables via `python-dotenv`; fail with a clear, friendly on-screen error (not a crash) if it's missing.
- Maintain full conversation history and resend it on every turn (LLMs are stateless — make this explicit in a code comment).
- Support the system prompt being **live-editable** from the sidebar and take effect on the next message.
- Stream the response using the Gemini SDK's streaming API and render it incrementally in the chat bubble.
- Handle and surface API errors (rate limits, invalid key, network errors) as readable UI messages.
- Report token usage (prompt + completion tokens) per turn, sourced from the API response — never estimated.

## Code Quality & Comments Requirements

- Write comments that teach, not narrate. Every comment should explain **why** a beginner should care, not restate the line ("# call the API" is not enough — explain what request is being built and why).
- At the top of the LLM client layer, include a short comment block walking through the request/response flow: user types → message appended to history → full history sent to Gemini → response streamed back → UI updated → history updated with the assistant's reply.
- Use clear, descriptive names (no `x`, `tmp`, `data2`).
- Keep functions small and single-purpose.
- No dead code, no commented-out experiments, no TODOs left unresolved.

## Security Requirements

- Never print, log, or display the API key anywhere, including in error messages.
- Never commit a `.env` file — only ship a `.env.example` with the variable name and an empty value.
- Do not execute or `eval()` anything from model output.

## File Structure to Generate

```
app.py                # the full Streamlit application
requirements.txt      # streamlit, google-genai, python-dotenv
.env.example           # GAISTUDIO_API_KEY=
README.md             # what the app does, setup steps, how to run it
```

## Acceptance Criteria (Definition of Done)

- [ ] Running `streamlit run app.py` with a valid `GAISTUDIO_API_KEY` in `.env` produces a working chat app with no errors.
- [ ] Responses stream visibly, token-by-token.
- [ ] Sidebar settings (temperature, max tokens, system prompt) visibly change model behavior.
- [ ] Conversation history persists across turns within a session and clears via the sidebar button.
- [ ] Token usage is shown and increases correctly after each turn.
- [ ] The five architecture layers above are clearly identifiable in the code via section comments.
- [ ] A missing API key produces a friendly on-screen message, not a crash.
- [ ] The UI looks deliberately designed, not default Streamlit styling.
