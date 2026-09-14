# Prompt: Premium ChatGPT-Style Chat App — Local LLM with LM Studio

This one is different from `01` and `02`. Those two ask for *exact* code so every
LLM produces the same file. This prompt is the opposite: it describes *what the
app must do and look like*, in plain simple words, and lets the AI write the best
code it can. Use this one when you want a polished, real-looking chat app — not a
teaching toy — that runs on a model on your own computer through LM Studio.

Paste everything below the line into Claude, Gemini, or any other coding AI, exactly
as written.

---

You are a friendly senior engineer. You are very good at building apps, and very
good at explaining things in simple words. Build me a chat app. Explain it like I
am new to coding.

### What I want

A chat website that looks and feels like ChatGPT or Claude — clean, modern, and
polished. It should not look like a plain gray demo. It should look like a real,
finished product that a company would actually ship.

The app must run **only on my own computer**, using **LM Studio** as the AI brain.
No cloud AI. No API key. No internet needed once LM Studio is running. LM Studio
gives me a local web address that works exactly like OpenAI's API, so use the
`openai` Python package, just pointed at my computer instead of the internet.

- Local server address: `http://localhost:1234/v1`
- No real API key is needed — LM Studio ignores it, so any placeholder text works.

### Tools to use

- **Streamlit** for the whole website (one Python file, `app.py`)
- **openai** Python package, pointed at LM Studio's local address
- **python-dotenv**, so the local address can be changed without editing code

### What the app must be able to do

1. **Find the AI model by itself.** Don't hardcode a model name — ask LM Studio
   which model is loaded (`client.models.list()`) and use that. If more than one
   model is loaded, let me pick from a dropdown list.
2. **Remember the conversation.** Every message I send and every reply the AI
   gives should stay on screen and be resent to the AI so it remembers what we
   talked about earlier. Add a way to explain, in a short code comment, that the
   AI itself has no memory — the app has to resend the whole conversation each time.
3. **Show replies as they are typed**, word by word, like a real chat app — not
   one big block of text appearing all at once.
4. **Have a sidebar** with simple controls:
   - A slider for "creativity" (temperature) — explain in one short line what
     low vs. high does.
   - A slider for maximum reply length.
   - A text box where I can change the AI's personality/instructions
     (the "system prompt").
   - A button that clears the whole conversation and starts fresh.
   - A small counter showing how many tokens have been used this session — read
     the real number from the AI's response, never guess it.
5. **Look premium.** Use:
   - A clear app title and a one-line subtitle explaining what it is.
   - Chat bubbles with icons/avatars so it's obvious who said what.
   - A friendly empty-state message before the first message is sent (e.g. a
     couple of clickable example questions to get started).
   - A calm, consistent layout — nothing cramped or misaligned.
6. **Never crash and never show a scary red error.** If LM Studio isn't running,
   show a friendly message that tells me exactly what to do (open LM Studio, load
   a model, click Start Server) instead of a broken page or a Python error.

### How the code should be written

- Write it so a complete beginner can read it top to bottom and understand it.
- Add short comments that explain **why** something is done, not just what the
  line does. For example, explain *why* we resend the whole conversation every
  time, not just say "send messages."
- Use clear, simple names for variables and functions — no short cryptic names.
- Keep the whole app in one file, organized top to bottom in this order:
  settings → connect to LM Studio → sidebar controls → chat history → handle a
  new message.
- No unused code. No leftover experiments. No fake/placeholder data.

### Files to give me

```
app.py               # the whole app
requirements.txt     # streamlit, openai, python-dotenv
.env.example          # LOCAL_LLM_BASE_URL=http://localhost:1234/v1
```

### How I will know it's done right

- [ ] Running `streamlit run app.py` with LM Studio's server started just works —
      no errors, no manual editing needed.
- [ ] Replies appear typed out, not dumped all at once.
- [ ] I can change the creativity slider, max length, and system prompt, and see
      the AI's answers actually change.
- [ ] The conversation remembers earlier messages until I click "Clear".
- [ ] The token counter goes up after every reply.
- [ ] If LM Studio isn't running, I see a clear, friendly message — not a crash.
- [ ] It genuinely looks premium — like a real product, not a bare demo.

---

## Running it

1. Open **LM Studio**, load any chat model, go to the **Developer** tab, and
   click **Start Server**.
2. Install the packages and run the app:

```bash
pip install -r requirements.txt
streamlit run app.py
```

3. Copy `.env.example` to `.env` if your LM Studio server runs on a different
   address than the default.

## What this teaches

This is the same idea as `02-streamlit-chat-ui-with-llm.md` — a Streamlit UI
calling an LLM through the OpenAI SDK — but with two changes that matter:

- **Cloud → local:** swapping `base_url` from OpenAI's servers to
  `http://localhost:1234/v1` is the *entire* difference between calling a paid
  cloud model and a free model running on your own machine. The rest of the
  `openai` SDK code doesn't change.
- **Toy → product:** `01` and `02` are deliberately bare so two different LLMs
  produce identical files. This prompt asks for the opposite — real UX thinking
  (streaming, empty states, error handling, a sidebar) — because a natural-language
  spec like this is how you'd actually brief an AI coding assistant to build
  something you intend to use, not just study.
