import os

import streamlit as st
from dotenv import load_dotenv
from openai import OpenAI

# Reads variables from a local .env file (if one exists) into the environment,
# e.g. LOCAL_LLM_BASE_URL. Safe to call even if .env is missing.
load_dotenv()

# Where our local LLM server lives. LM Studio's OpenAI-compatible server defaults
# to this address. Override it by setting LOCAL_LLM_BASE_URL in a .env file
# (see .env.example) if your server runs on a different host/port.
BASE_URL = os.getenv("LOCAL_LLM_BASE_URL", "http://localhost:1234/v1")

# The `openai` SDK works with ANY server that speaks the OpenAI API shape —
# not just OpenAI's own cloud. Pointing base_url at localhost makes every call
# below hit your own machine instead of the internet.
# api_key is required by the SDK's constructor, but LM Studio ignores it —
# any non-empty string works since there's no real authentication locally.
client = OpenAI(base_url=BASE_URL, api_key="lm-studio")

st.title("Simple Chat")
st.caption(f"Running locally via {BASE_URL} — no API key needed.")

# Ask the local server which models are currently loaded, instead of hardcoding
# a model name (unlike a cloud provider, a local model's ID depends entirely on
# what you downloaded in LM Studio). Embedding models are filtered out since
# they can't hold a chat conversation.
try:
    chat_models = [m.id for m in client.models.list().data if "embed" not in m.id.lower()]
except Exception:
    # LM Studio isn't running, or its server hasn't been started yet.
    chat_models = []

if not chat_models:
    st.error(
        f"Can't reach a local LLM server at `{BASE_URL}`.\n\n"
        "Start LM Studio, load a chat model in the **Developer** tab, and click "
        "**Start Server** — then reload this page."
    )
    st.stop()  # halts the script here so the code below never runs without a model

# Just use whichever chat model is loaded first.
MODEL = chat_models[0]

# st.session_state persists data between reruns (Streamlit reruns the whole
# script top-to-bottom on every interaction, e.g. every new chat message).
# Without this, the conversation history would reset after each message.
if "messages" not in st.session_state:
    st.session_state.messages = []

# Redraw every past message so the conversation is visible after each rerun.
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.write(message["content"])

# Renders a chat-style input box at the bottom of the page. Returns the typed
# text once the user submits, or None while waiting.
user_input = st.chat_input("Type a message")

if user_input:
    # Save the user's message and show it immediately.
    st.session_state.messages.append({"role": "user", "content": user_input})
    with st.chat_message("user"):
        st.write(user_input)

    # The model has no memory of its own — sending the full message history
    # (not just the latest message) is what makes this feel like a continuous
    # conversation instead of a series of one-off questions.
    response = client.chat.completions.create(
        model=MODEL,
        messages=st.session_state.messages,
    )
    reply = response.choices[0].message.content

    # Save the assistant's reply too, so it's part of history for the next turn
    # and so it survives the next rerun.
    st.session_state.messages.append({"role": "assistant", "content": reply})
    with st.chat_message("assistant"):
        st.write(reply)
