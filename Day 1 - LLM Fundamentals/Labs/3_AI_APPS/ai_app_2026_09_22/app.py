from __future__ import annotations

import os
from typing import Iterator

import streamlit as st
from dotenv import load_dotenv
from google import genai
from google.genai import types

st.set_page_config(
    page_title="Dinesh AI Academy · Gemini Chat",
    page_icon="💬",
    layout="wide",
    initial_sidebar_state="expanded",
)
load_dotenv()

DEFAULT_SYSTEM_PROMPT = (
    "You are a friendly, knowledgeable teaching assistant for Dinesh AI Academy. "
    "Answer clearly and concisely."
)
FALLBACK_MODELS = [
    ("Gemini 2.5 Flash", "gemini-2.5-flash"),
    ("Gemini 2.5 Flash-Lite", "gemini-2.5-flash-lite"),
    ("Gemini 2.0 Flash", "gemini-2.0-flash"),
]


def initialise_state() -> None:
    defaults = {
        "api_key": os.getenv("GEMINI_API_KEY", "").strip(),
        "gemini_client": None,
        "client_api_key": None,
        "models": FALLBACK_MODELS,
        "models_live": False,
        "models_error": None,
        "connection_status": "no_key",
        "messages": [],
        "system_prompt": DEFAULT_SYSTEM_PROMPT,
        "temperature": 0.7,
    }
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value


def is_auth_error(error: Exception) -> bool:
    text = str(error).lower()
    return any(
        marker in text
        for marker in ("401", "403", "unauthorized", "permission", "api key", "authentication")
    )


def discover_models() -> None:
    client = st.session_state.gemini_client
    if client is None or st.session_state.models_live:
        return
    try:
        discovered: dict[str, tuple[str, str]] = {}
        for model in client.models.list():
            model_id = (getattr(model, "name", "") or "").removeprefix("models/")
            lowered = model_id.lower()
            if "flash" in lowered and not any(
                term in lowered for term in ("image", "live", "tts")
            ):
                label = getattr(model, "display_name", None) or model_id
                discovered[model_id] = (label, model_id)
        if not discovered:
            raise RuntimeError("No flash-tier text models were returned.")
        st.session_state.models = sorted(discovered.values())
        st.session_state.models_live = True
        st.session_state.models_error = None
        st.session_state.connection_status = "connected"
    except Exception as error:
        st.session_state.models = FALLBACK_MODELS
        st.session_state.models_live = False
        st.session_state.models_error = str(error)
        st.session_state.connection_status = "rejected" if is_auth_error(error) else "connected"


def refresh_client() -> None:
    key = st.session_state.api_key.strip()
    if not key:
        st.session_state.gemini_client = None
        st.session_state.client_api_key = None
        st.session_state.models_live = False
        st.session_state.models = FALLBACK_MODELS
        st.session_state.connection_status = "no_key"
        return
    if st.session_state.client_api_key != key:
        st.session_state.gemini_client = genai.Client(api_key=key)
        st.session_state.client_api_key = key
        st.session_state.models_live = False
        discover_models()


def sync_pasted_key() -> None:
    st.session_state.api_key = st.session_state.api_key_input.strip()
    refresh_client()


def get_client() -> genai.Client | None:
    if st.session_state.client_api_key != st.session_state.api_key.strip():
        refresh_client()
    return st.session_state.gemini_client


def render_connection_status() -> None:
    status = st.session_state.connection_status
    if status == "connected":
        st.success("Connected")
    elif status == "rejected":
        st.error(
            "Not connected — key rejected. That key wasn't accepted. "
            "Double-check it or get a new one at https://aistudio.google.com/apikey."
        )
    else:
        st.warning("Not connected — no key yet. Paste your API key above, or add it to `.env` and restart.")


def stream_response(
    client: genai.Client,
    model: str,
    messages: list[dict[str, str]],
    system_prompt: str,
    temperature: float,
) -> Iterator[str]:
    contents = [
        {
            "role": "user" if message["role"] == "user" else "model",
            "parts": [{"text": message["content"]}],
        }
        for message in messages
    ]
    response_stream = client.models.generate_content_stream(
        model=model,
        contents=contents,
        config=types.GenerateContentConfig(
            system_instruction=system_prompt,
            temperature=temperature,
        ),
    )
    for chunk in response_stream:
        if chunk.text:
            yield chunk.text


def render_sidebar() -> tuple[str, str, float]:
    with st.sidebar:
        st.markdown("## Studio settings")
        st.caption("Tune the model for this local session.")
        env_key = os.getenv("GEMINI_API_KEY", "").strip()

        if env_key:
            st.session_state.api_key = env_key
            refresh_client()
        else:
            st.error(
                "No API key found. Get a free key at "
                "https://aistudio.google.com/apikey, then paste it below "
                "for this session or add it to `.env` and restart."
            )
            st.text_input(
                "Gemini API key",
                type="password",
                placeholder="Paste your key and press Enter",
                key="api_key_input",
                on_change=sync_pasted_key,
                help="This key remains in session state and is never written to disk.",
            )
            if st.session_state.api_key_input.strip() != st.session_state.api_key:
                sync_pasted_key()

        get_client()
        if st.session_state.api_key and not st.session_state.models_live:
            st.warning(
                "Couldn't load the live model list, showing common defaults instead. "
                "This usually means the key cannot list models or there is a network issue — "
                "try again in a moment, or pick a model below and continue."
            )
        model_labels = [label for label, _ in st.session_state.models]
        selected_label = st.selectbox("Model", model_labels, index=0)
        temperature = st.slider(
            "Temperature", 0.0, 2.0, st.session_state.temperature, 0.1
        )
        st.session_state.temperature = temperature
        system_prompt = st.text_area("System prompt", key="system_prompt", height=130)
        if st.button("Clear conversation", use_container_width=True):
            st.session_state.messages = []
            st.rerun()
        st.divider()
        render_connection_status()
        st.caption("Your key stays local to this app.")
    return dict(st.session_state.models)[selected_label], system_prompt, temperature


initialise_state()
model, system_prompt, temperature = render_sidebar()

st.markdown(
    """
    <div class="hero">
        <div class="eyebrow">DINESH AI ACADEMY <span>·</span> AI ENGINEERING BOOTCAMP</div>
        <h1>Dinesh AI Academy — Gemini Chat Studio</h1>
        <p>Built live in a hands-on session — Day 1: LLM Fundamentals</p>
    </div>
    """,
    unsafe_allow_html=True,
)

if not st.session_state.messages:
    st.info("Hi! Ask me anything about what we covered today.")
    if st.session_state.connection_status == "no_key":
        st.warning("Not connected — no key yet. Paste your API key in the sidebar, or add it to `.env` and restart.")
    elif st.session_state.connection_status == "rejected":
        st.error("That key wasn't accepted. Check it in the sidebar or get a new one at https://aistudio.google.com/apikey.")

for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

if prompt := st.chat_input(
    "Ask Gemini about today’s lesson...",
    disabled=st.session_state.connection_status != "connected",
):
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)
    client = get_client()
    if client is None:
        st.error("Your API key is not connected. Paste it in the sidebar and try again.")
    else:
        with st.chat_message("assistant"):
            try:
                response_text = st.write_stream(
                    stream_response(client, model, st.session_state.messages, system_prompt, temperature)
                )
                st.session_state.messages.append({"role": "assistant", "content": response_text})
            except Exception as error:
                if is_auth_error(error):
                    st.session_state.connection_status = "rejected"
                    st.error("Your API key wasn't accepted — check it in the sidebar, or get a new one at https://aistudio.google.com/apikey.")
                elif any(marker in str(error).lower() for marker in ("429", "rate", "quota")):
                    st.error("You've hit Gemini's rate limit — wait a few seconds and send your message again.")
                elif any(marker in str(error).lower() for marker in ("network", "connect", "timeout")):
                    st.error("Couldn't reach Gemini — check your internet connection and try again.")
                else:
                    st.error("Gemini couldn't complete that request. Try again, and if it keeps happening, check the Gemini API status page.")

st.divider()
st.caption("Made at Dinesh AI Academy · Powered by Google Gemini")
