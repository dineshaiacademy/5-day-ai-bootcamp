import hashlib
import os

import streamlit as st
from dotenv import load_dotenv
from openai import OpenAI
from pypdf import PdfReader

load_dotenv()

# ── Config ────────────────────────────────────────────────────────────────
CHUNK_SIZE = 1000
CHUNK_OVERLAP = 150
TOP_K = 4

DEFAULT_SYSTEM_PROMPT = (
    "You are a helpful assistant. When context from uploaded documents is provided "
    "below, answer using that context and say so if the answer isn't in it. When no "
    "context is provided, answer normally from your own knowledge."
)

# Gemini's newer models "think" before answering, which can silently eat the whole
# max_tokens budget and come back with an empty reply. reasoning_effort="low" keeps
# them fast and reliable for a chat app; it's ignored by providers that don't support it.
GEMINI_REASONING_EFFORT = "low"

# Non-text Gemini models (image/audio/video/etc.) to hide from the chat model picker.
GEMINI_EXCLUDE = (
    "image", "audio", "tts", "live", "transcribe", "computer-use", "robotics",
    "veo", "lyria", "aqa", "deep-research", "antigravity", "nano-banana",
)

PROVIDERS = {
    "LM Studio (local)": {
        "base_url": os.getenv("LOCAL_LLM_BASE_URL", "http://localhost:1234/v1"),
        "api_key": "local",
        "needs_key": False,
    },
    "Gemini (Google AI)": {
        "base_url": "https://generativelanguage.googleapis.com/v1beta/openai/",
        "api_key": os.getenv("GEMINI_API_KEY") or os.getenv("GAISTUDIO_API_KEY"),
        "needs_key": True,
    },
}

st.set_page_config(page_title="PDF Chat", page_icon=":material/forum:", layout="wide")


# ── LLM client ───────────────────────────────────────────────────────────
@st.cache_resource
def get_client(base_url: str, api_key: str) -> OpenAI:
    return OpenAI(base_url=base_url, api_key=api_key)


@st.cache_data(ttl=30)
def list_models(base_url: str, api_key: str) -> list[str]:
    client = get_client(base_url, api_key)
    return sorted(m.id.removeprefix("models/") for m in client.models.list().data)


# ── Document indexing (Chroma) ───────────────────────────────────────────
def chunk_text(text: str, size: int = CHUNK_SIZE, overlap: int = CHUNK_OVERLAP) -> list[str]:
    text = " ".join(text.split())
    chunks = []
    start = 0
    while start < len(text):
        end = start + size
        chunks.append(text[start:end])
        start = end - overlap
    return chunks


def get_collection(base_url: str, api_key: str, embed_model: str, collection_key: str):
    # Kept in session_state (not @st.cache_resource): uploaded documents are
    # per-user data, not a shared resource other sessions should see.
    if st.session_state.chroma_client is None:
        import chromadb

        st.session_state.chroma_client = chromadb.Client()

    if st.session_state.collection is None or st.session_state.collection_key != collection_key:
        from chromadb.utils.embedding_functions import OpenAIEmbeddingFunction

        embed_fn = OpenAIEmbeddingFunction(api_key=api_key, api_base=base_url, model_name=embed_model)
        st.session_state.collection = st.session_state.chroma_client.get_or_create_collection(
            name=f"pdf_chat_{abs(hash(collection_key))}", embedding_function=embed_fn
        )
        st.session_state.collection_key = collection_key
        st.session_state.indexed_files = {}

    return st.session_state.collection


def index_file(uploaded_file, collection) -> int:
    reader = PdfReader(uploaded_file)
    text = "\n".join(page.extract_text() or "" for page in reader.pages)
    chunks = chunk_text(text)
    if not chunks:
        return 0
    digest = hashlib.md5(uploaded_file.getvalue()).hexdigest()[:8]
    ids = [f"{digest}-{i}" for i in range(len(chunks))]
    metadatas = [{"source": uploaded_file.name}] * len(chunks)
    collection.add(documents=chunks, ids=ids, metadatas=metadatas)
    return len(chunks)


def retrieve(collection, query: str, k: int = TOP_K) -> list[dict]:
    if collection.count() == 0:
        return []
    results = collection.query(query_texts=[query], n_results=min(k, collection.count()))
    return [
        {"source": meta["source"], "text": doc}
        for doc, meta in zip(results["documents"][0], results["metadatas"][0])
    ]


def render_sources(chunks: list[dict]) -> None:
    with st.expander(f"Sources ({len(chunks)} chunk(s) retrieved)"):
        for i, c in enumerate(chunks):
            st.caption(f":material/description: {c['source']}")
            preview = c["text"][:600] + ("…" if len(c["text"]) > 600 else "")
            st.text(preview)
            if i < len(chunks) - 1:
                st.divider()


# ── Session state ────────────────────────────────────────────────────────
for key, default in {
    "messages": [],
    "indexed_files": {},
    "chroma_client": None,
    "collection": None,
    "collection_key": None,
}.items():
    if key not in st.session_state:
        st.session_state[key] = default


# ── Sidebar ──────────────────────────────────────────────────────────────
with st.sidebar:
    # Brand header
    st.markdown("### :material/auto_awesome: Dinesh AI Academy")
    st.caption("PDF chat · RAG playground")
    st.space("small")

    # ── Provider & model ─────────────────────────────────────────────────
    with st.container(border=True):
        st.markdown("**:material/cloud: Provider & model**")
        provider_name = st.segmented_control(
            "Provider", list(PROVIDERS), default="LM Studio (local)", required=True, label_visibility="collapsed"
        )
        provider = PROVIDERS[provider_name]

        if provider["needs_key"] and not provider["api_key"]:
            st.error(
                f"No API key found for {provider_name}. Add `GEMINI_API_KEY=...` to your "
                "`.env` file (get a free key at aistudio.google.com/apikey), then reload."
            )
            st.stop()

        client = get_client(provider["base_url"], provider["api_key"])

        try:
            all_models = list_models(provider["base_url"], provider["api_key"])
        except Exception:
            all_models = []

        if not all_models:
            if provider_name.startswith("LM Studio"):
                st.error(
                    f"Can't reach a local LLM server at `{provider['base_url']}`.\n\n"
                    "Start LM Studio, load a chat model **and** an embedding model in the "
                    "**Developer** tab, and click **Start Server** — then reload this page."
                )
            else:
                st.error("Couldn't list Gemini models. Check that your API key is valid, then reload.")
            st.stop()

        st.badge(f"Connected · {len(all_models)} models", icon=":material/check_circle:", color="green")

        if provider_name.startswith("Gemini"):
            chat_models = sorted(m for m in all_models if "embed" not in m and not any(x in m for x in GEMINI_EXCLUDE))
        else:
            chat_models = [m for m in all_models if "embed" not in m.lower()] or all_models
        embed_models = [m for m in all_models if "embed" in m.lower()]

        default_chat = "gemini-flash-latest" if "gemini-flash-latest" in chat_models else chat_models[0]
        model = st.selectbox(
            "Chat model", chat_models, index=chat_models.index(default_chat), help="Models available from the selected provider."
        )

        with st.expander("Advanced", icon=":material/tune:"):
            temperature = st.slider("Temperature", 0.0, 1.5, 0.7, 0.1)
            max_tokens = st.slider("Max tokens", 50, 4000, 600, 50)
            st.caption("Response looks empty? Some 'thinking' models spend tokens on hidden reasoning — try a different model or raise this limit.")

    # ── Documents ────────────────────────────────────────────────────────
    with st.container(border=True):
        st.markdown("**:material/library_books: Documents**")

        if not embed_models:
            st.warning(f"No embedding model available from {provider_name} — document upload is disabled.")
            collection = None
        else:
            embed_model = st.selectbox("Embedding model", embed_models)
            collection = get_collection(
                provider["base_url"], provider["api_key"], embed_model, f"{provider_name}:{embed_model}"
            )

            uploaded_files = st.file_uploader(
                "Upload PDFs to chat with", type="pdf", accept_multiple_files=True, label_visibility="collapsed"
            )
            if uploaded_files:
                new_files = [f for f in uploaded_files if f.name not in st.session_state.indexed_files]
                for f in new_files:
                    with st.spinner(f"Indexing {f.name}...", show_time=True):
                        st.session_state.indexed_files[f.name] = index_file(f, collection)

            if st.session_state.indexed_files:
                for name, count in st.session_state.indexed_files.items():
                    row = st.container(horizontal=True)
                    row.caption(f":material/description: {name}")
                    row.badge(f"{count} chunks", color="violet")
                if st.button("Clear documents", icon=":material/delete:", width="stretch"):
                    st.session_state.chroma_client = None
                    st.session_state.collection = None
                    st.session_state.indexed_files = {}
                    st.rerun()
            else:
                st.caption("No documents yet — chat will use general knowledge only.")

    st.space("small")
    if st.button("Clear conversation", icon=":material/mop:", width="stretch"):
        st.session_state.messages = []
        st.rerun()


# ── Header ───────────────────────────────────────────────────────────────
st.title(":material/forum: Chat with your documents")
if st.session_state.indexed_files:
    st.caption(f":material/library_books: Answering using {len(st.session_state.indexed_files)} uploaded document(s) — {provider_name}, `{model}`")
else:
    st.caption(f"General chat — upload PDFs in the sidebar to ask about your own documents. Provider: {provider_name}, `{model}`.")


# ── Chat history ─────────────────────────────────────────────────────────
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.write(message["content"])
        if message.get("sources"):
            render_sources(message["sources"])


# ── Handle a new turn ─────────────────────────────────────────────────────
prompt = st.chat_input("Ask a question", submit_mode="disable")

if prompt:
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.write(prompt)

    retrieved_chunks = []
    with st.chat_message("assistant"):
        if collection is not None and st.session_state.indexed_files:
            with st.status("Searching your documents", type="step"):
                retrieved_chunks = retrieve(collection, prompt)

        if retrieved_chunks:
            context = "\n\n---\n\n".join(c["text"] for c in retrieved_chunks)
            user_turn = f"Context from uploaded documents:\n{context}\n\nQuestion: {prompt}"
        else:
            user_turn = prompt

        history = [{"role": m["role"], "content": m["content"]} for m in st.session_state.messages[:-1]]
        request_messages = [
            {"role": "system", "content": DEFAULT_SYSTEM_PROMPT},
            *history,
            {"role": "user", "content": user_turn},
        ]

        extra_args = {}
        if provider_name.startswith("Gemini"):
            extra_args["reasoning_effort"] = GEMINI_REASONING_EFFORT

        stream = client.chat.completions.create(
            model=model,
            messages=request_messages,
            temperature=temperature,
            max_tokens=max_tokens,
            stream=True,
            **extra_args,
        )
        response = st.write_stream(
            chunk.choices[0].delta.content or "" for chunk in stream if chunk.choices
        )

        if retrieved_chunks:
            render_sources(retrieved_chunks)

    st.session_state.messages.append(
        {"role": "assistant", "content": response, "sources": retrieved_chunks or None}
    )
