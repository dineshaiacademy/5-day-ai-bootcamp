"""
Premium local chat app — a ChatGPT-style UI powered entirely by a model
running on your own computer through LM Studio. No API key, no cloud,
no internet required once LM Studio's local server is running.
"""

import os

import streamlit as st
from dotenv import load_dotenv
from openai import OpenAI

# ═══════════════════════════════════════════════════════════════════════
# 1. CONFIGURATION & SECRETS
# ═══════════════════════════════════════════════════════════════════════
# LM Studio speaks the same protocol as OpenAI's API, so the `openai`
# SDK works unmodified — we just point `base_url` at our own machine
# instead of OpenAI's servers. This one setting is the entire difference
# between "cloud AI" and "local AI" as far as the code is concerned.
load_dotenv()
BASE_URL = os.getenv("LOCAL_LLM_BASE_URL", "http://localhost:1234/v1")

DEFAULT_SYSTEM_PROMPT = (
    "You are a friendly, knowledgeable assistant. Answer clearly and "
    "concisely, and say when you're not sure about something."
)

# Shown as clickable chips before the first message is sent, so a new
# user isn't staring at a blank box wondering what to type.
EXAMPLE_PROMPTS = {
    ":material/travel_explore: Explain simply": "Explain what a Large Language Model is, like I'm new to tech.",
    ":material/code: Write some code": "Write a Python function that checks if a string is a palindrome.",
    ":material/lightbulb: Brainstorm ideas": "Give me 3 creative names for a neighborhood coffee shop.",
}

st.set_page_config(
    page_title="Local AI Chat",
    page_icon=":material/smart_toy:",
    layout="wide",
)

# A little custom CSS so the page reads as a designed product rather
# than the default Streamlit look — wider chat bubbles, breathing room,
# and one consistent accent color used throughout.
st.markdown(
    """
    <style>
        .block-container { max-width: 820px; padding-top: 2.5rem; }
        [data-testid="stChatMessage"] { padding: 0.9rem 1.1rem; border-radius: 14px; }
        h1 { font-weight: 700; letter-spacing: -0.02em; }
        [data-testid="stMetricValue"] { color: #6C5CE7; }
        .stButton button { border-radius: 10px; }
    </style>
    """,
    unsafe_allow_html=True,
)


# ═══════════════════════════════════════════════════════════════════════
# 2. LLM CLIENT LAYER — every call to the local model lives here.
# ═══════════════════════════════════════════════════════════════════════
# The request/response flow for every turn of this app:
#   1. The user types a message → it's appended to `st.session_state.messages`.
#   2. We send the *entire* conversation so far to LM Studio, because the
#      model itself has no memory — it only ever sees what's in the request.
#      Re-sending history is how a stateless model "remembers" a chat.
#   3. LM Studio streams the reply back one small piece at a time.
#   4. We render each piece as it arrives (the typing effect) and, once
#      done, save the full reply into history for the next turn.


@st.cache_resource
def get_client(base_url: str) -> OpenAI:
    # LM Studio doesn't check the API key at all, so any placeholder
    # text satisfies the SDK, which requires one to be present.
    return OpenAI(base_url=base_url, api_key="lm-studio")


@st.cache_data(ttl=30)
def list_available_models(base_url: str) -> list[str]:
    # We never hardcode a model name — whatever is loaded in LM Studio
    # right now is what we offer, so switching models there needs no
    # code change here. Embedding models are filtered out since they
    # can't hold a chat conversation.
    client = get_client(base_url)
    models = client.models.list()
    return sorted(m.id for m in models.data if "embed" not in m.id.lower())


def stream_reply(model: str, messages: list[dict], temperature: float, max_tokens: int):
    """Ask the local model for a reply and yield it piece by piece, tracking
    token usage as it comes in (LM Studio reports real usage on the final
    streamed chunk — we never estimate it ourselves)."""
    stream = get_client(BASE_URL).chat.completions.create(
        model=model,
        messages=messages,
        temperature=temperature,
        max_tokens=max_tokens,
        stream=True,
        stream_options={"include_usage": True},
    )
    for chunk in stream:
        if chunk.usage:
            st.session_state.total_tokens += chunk.usage.total_tokens
        if chunk.choices and chunk.choices[0].delta.content:
            yield chunk.choices[0].delta.content


# ═══════════════════════════════════════════════════════════════════════
# 3. STATE MANAGEMENT
# ═══════════════════════════════════════════════════════════════════════
if "messages" not in st.session_state:
    st.session_state.messages = []
if "total_tokens" not in st.session_state:
    st.session_state.total_tokens = 0

# Check the local server *before* drawing the rest of the UI, so a
# down/unstarted LM Studio produces one friendly message instead of a
# half-built page followed by a crash.
try:
    available_models = list_available_models(BASE_URL)
except Exception:
    available_models = []

if not available_models:
    st.title(":material/smart_toy: Local AI Chat")
    st.error(
        f"**Can't reach a local model at `{BASE_URL}`.**\n\n"
        "To fix this:\n"
        "1. Open **LM Studio**.\n"
        "2. Load any chat model.\n"
        "3. Go to the **Developer** tab and click **Start Server**.\n\n"
        "Then reload this page — no other setup needed."
    )
    st.stop()


# ═══════════════════════════════════════════════════════════════════════
# 4. UI LAYER — sidebar controls
# ═══════════════════════════════════════════════════════════════════════
with st.sidebar:
    st.header("Settings")

    selected_model = st.selectbox(
        "Model",
        available_models,
        help="Every chat model currently loaded in your LM Studio server.",
    )

    temperature = st.slider(
        "Creativity", 0.0, 1.5, 0.7, 0.1,
        help="Low = focused, predictable answers. High = more varied, surprising answers.",
    )

    max_tokens = st.slider(
        "Max reply length", 50, 2000, 500, 50,
        help="The most tokens (word-pieces) the model is allowed to write in one reply.",
    )

    system_prompt = st.text_area(
        "System prompt (the AI's personality/instructions)",
        DEFAULT_SYSTEM_PROMPT,
        height=110,
    )

    st.divider()
    st.metric("Tokens used this session", st.session_state.total_tokens)

    if st.button("Clear conversation", icon=":material/delete:", width="stretch"):
        st.session_state.messages = []
        st.session_state.total_tokens = 0
        st.rerun()


# ═══════════════════════════════════════════════════════════════════════
# 4b. UI LAYER — header and chat history
# ═══════════════════════════════════════════════════════════════════════
st.title(":material/smart_toy: Local AI Chat")
st.caption(
    f"Running fully on your machine via `{BASE_URL}` · model **{selected_model}** "
    "· no API key, no cost, no internet required."
)

for message in st.session_state.messages:
    avatar = ":material/person:" if message["role"] == "user" else ":material/smart_toy:"
    with st.chat_message(message["role"], avatar=avatar):
        st.write(message["content"])

# Friendly empty state: only shown before the first message exists.
new_prompt = None
if not st.session_state.messages:
    st.info("Ask me anything to get started — or try one of these:")
    clicked = st.pills("Examples", list(EXAMPLE_PROMPTS.keys()), label_visibility="collapsed")
    if clicked:
        new_prompt = EXAMPLE_PROMPTS[clicked]

typed_prompt = st.chat_input("Message the local model...")
new_prompt = typed_prompt or new_prompt


# ═══════════════════════════════════════════════════════════════════════
# 5. ORCHESTRATION — wire user input to the LLM client and back to the UI
# ═══════════════════════════════════════════════════════════════════════
if new_prompt:
    st.session_state.messages.append({"role": "user", "content": new_prompt})
    with st.chat_message("user", avatar=":material/person:"):
        st.write(new_prompt)

    # The system prompt is prepended fresh each turn (not stored in
    # history) so editing it in the sidebar takes effect immediately.
    request_messages = [{"role": "system", "content": system_prompt}, *st.session_state.messages]

    with st.chat_message("assistant", avatar=":material/smart_toy:"):
        try:
            reply = st.write_stream(
                stream_reply(selected_model, request_messages, temperature, max_tokens)
            )
        except Exception:
            st.error(
                "Something went wrong talking to the local model. Make sure LM Studio's "
                "server is still running, then try sending your message again."
            )
            st.stop()

    st.session_state.messages.append({"role": "assistant", "content": reply})
    st.rerun()  # refresh so the sidebar's token counter reflects this turn
