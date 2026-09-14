# Prompt: Streamlit Chat UI — No LLM Integration

Paste everything below the line into Gemini, Claude, or DeepSeek exactly as written.
The instructions are written to remove every decision the model could make differently,
so the same prompt run on different LLMs should produce the same file.

---

You are generating exactly one file: `app.py`, a Streamlit chat interface with no LLM
call — it only echoes a fixed placeholder reply. Follow this specification exactly.
Do not rename any variable, string, or key. Do not add comments, docstrings, type
hints, error handling, styling, blank lines, or any code not listed below. Do not
change the order of statements. Output nothing except a single fenced ```python code
block containing the exact code — no explanation before or after it.

Exact code to output:

```python
import streamlit as st

st.title("Simple Chat")

if "messages" not in st.session_state:
    st.session_state.messages = []

for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.write(message["content"])

user_input = st.chat_input("Type a message")

if user_input:
    st.session_state.messages.append({"role": "user", "content": user_input})
    with st.chat_message("user"):
        st.write(user_input)

    reply = "This is a placeholder response. Connect an LLM to make me smart."
    st.session_state.messages.append({"role": "assistant", "content": reply})
    with st.chat_message("assistant"):
        st.write(reply)
```

---

## Running it

```bash
pip install streamlit
streamlit run app.py
```

## What this teaches

`st.session_state.messages` is the chat history; `st.chat_message` / `st.chat_input`
are Streamlit's built-in chat widgets. The `reply` line is where Day 2's prompt
(`02-streamlit-chat-ui-with-llm.md`) plugs in a real model call instead of a fixed string.
