# Prompt: Streamlit Chat UI — With LLM Integration

Paste everything below the line into Gemini, Claude, or DeepSeek exactly as written.
The instructions are written to remove every decision the model could make differently,
so the same prompt run on different LLMs should produce the same file.

---

You are generating exactly one file: `app.py`, a Streamlit chat interface that calls
an LLM through the OpenAI Python SDK. Follow this specification exactly. Do not rename
any variable, string, or key. Do not add comments, docstrings, type hints, error
handling, styling, blank lines, or any code not listed below. Do not change the order
of statements. Do not swap the OpenAI SDK for any other library. Do not change the
model name. Output nothing except a single fenced ```python code block containing the
exact code — no explanation before or after it.

Exact code to output:

```python
import os

import streamlit as st
from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

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

    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=st.session_state.messages,
    )
    reply = response.choices[0].message.content

    st.session_state.messages.append({"role": "assistant", "content": reply})
    with st.chat_message("assistant"):
        st.write(reply)
```

---

## Running it

```bash
pip install streamlit python-dotenv openai
```

Create a `.env` file next to `app.py`:

```
OPENAI_API_KEY=your-key-here
```

```bash
streamlit run app.py
```

## What this teaches

The whole chat history in `st.session_state.messages` is passed to
`client.chat.completions.create` on every turn, which is how the model "remembers"
the conversation — Streamlit itself has no memory between reruns. This builds directly
on `01-streamlit-chat-ui-no-llm.md`: the fixed `reply` string is replaced by
`response.choices[0].message.content`.
