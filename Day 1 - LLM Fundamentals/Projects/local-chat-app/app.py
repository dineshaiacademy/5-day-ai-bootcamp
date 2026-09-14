import os

import streamlit as st
from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()

# ── Config ────────────────────────────────────────────────────────────────
BASE_URL = os.getenv("LOCAL_LLM_BASE_URL", "http://localhost:1234/v1")

DEFAULT_SYSTEM_PROMPT = (
    "You are a helpful, concise assistant. If you don't know the answer, "
    "say so instead of guessing."
)

SUGGESTIONS = {
    ":material/travel_explore: Explain a concept": "Explain what a Large Language Model is, in two sentences.",
    ":material/code: Help with code": "Write a Python function that checks if a string is a palindrome.",
    ":material/lightbulb: Brainstorm": "Give me 3 creative names for a coffee shop.",
}

st.set_page_config(page_title="Local Chat", page_icon=":material/chat:")


# ── LLM client ───────────────────────────────────────────────────────────
@st.cache_resource
def get_client(base_url: str) -> OpenAI:
    # api_key is required by the SDK but ignored by local OpenAI-compatible servers.
    return OpenAI(base_url=base_url, api_key="local")


@st.cache_data(ttl=30)
def list_chat_models(base_url: str) -> list[str]:
    client = get_client(base_url)
    models = client.models.list()
    return sorted(m.id for m in models.data if "embed" not in m.id.lower())


client = get_client(BASE_URL)

try:
    chat_models = list_chat_models(BASE_URL)
except Exception:
    chat_models = []

if not chat_models:
    st.error(
        f"Can't reach a local LLM server at `{BASE_URL}`.\n\n"
        "Start LM Studio, load a chat model in the **Developer** tab, and click "
        "**Start Server** — then reload this page."
    )
    st.stop()


# ── Sidebar settings ─────────────────────────────────────────────────────
with st.sidebar:
    st.header("Settings")
    model = st.selectbox("Model", chat_models, help="Models currently loaded in your local server.")
    temperature = st.slider("Temperature", 0.0, 1.5, 0.7, 0.1)
    max_tokens = st.slider("Max tokens", 50, 1000, 400, 50)
    system_prompt = st.text_area("System prompt", DEFAULT_SYSTEM_PROMPT, height=100)

    st.divider()
    if "total_tokens" in st.session_state and st.session_state.total_tokens:
        st.metric("Tokens used this session", st.session_state.total_tokens)

    if st.button("Clear conversation", icon=":material/delete:", width="stretch"):
        st.session_state.messages = []
        st.session_state.total_tokens = 0
        st.rerun()


# ── Session state ────────────────────────────────────────────────────────
if "messages" not in st.session_state:
    st.session_state.messages = []
if "total_tokens" not in st.session_state:
    st.session_state.total_tokens = 0


# ── Header ───────────────────────────────────────────────────────────────
st.title(":material/chat: Local Chat")
st.caption(f"Running fully on your machine via `{BASE_URL}` — no API key, no cost, no internet.")


# ── Chat history ─────────────────────────────────────────────────────────
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.write(message["content"])


# ── Suggestion chips (only before the first message) ────────────────────
prompt = None
if not st.session_state.messages:
    selected = st.pills("Try asking:", list(SUGGESTIONS.keys()), label_visibility="collapsed")
    if selected:
        prompt = SUGGESTIONS[selected]

prompt = st.chat_input("Type a message", submit_mode="disable") or prompt


# ── Handle a new turn ─────────────────────────────────────────────────────
if prompt:
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.write(prompt)

    request_messages = [{"role": "system", "content": system_prompt}, *st.session_state.messages]

    with st.chat_message("assistant"):
        stream = client.chat.completions.create(
            model=model,
            messages=request_messages,
            temperature=temperature,
            max_tokens=max_tokens,
            stream=True,
            stream_options={"include_usage": True},
        )

        usage_holder = {}

        def collect_stream():
            for chunk in stream:
                if chunk.usage:
                    usage_holder["usage"] = chunk.usage
                if chunk.choices and chunk.choices[0].delta.content:
                    yield chunk.choices[0].delta.content

        response = st.write_stream(collect_stream())

    st.session_state.messages.append({"role": "assistant", "content": response})
    if usage_holder.get("usage"):
        st.session_state.total_tokens += usage_holder["usage"].total_tokens
        st.rerun()
