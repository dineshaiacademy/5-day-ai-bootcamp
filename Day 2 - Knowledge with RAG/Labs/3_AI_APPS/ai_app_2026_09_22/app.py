import os
from typing import Iterable

import chromadb
import streamlit as st
from dotenv import load_dotenv
from google import genai
from pypdf import PdfReader

load_dotenv()

CHAT_MODELS = [
    "gemini-3.6-flash",
    "gemini-3.5-flash",
    "gemini-3.5-flash-lite",
]
EMBEDDING_MODEL = "gemini-embedding-001"

st.set_page_config(page_title="Dinesh AI Academy · PDF Chat", page_icon="📄")
st.title("Dinesh AI Academy — Chat With Your PDF")

if "messages" not in st.session_state:
    st.session_state.messages = []
if "chat_model" not in st.session_state:
    st.session_state.chat_model = CHAT_MODELS[0]
if "gemini_client" not in st.session_state:
    st.session_state.gemini_client = None
if "connection_checked" not in st.session_state:
    try:
        api_key = os.getenv("GEMINI_API_KEY") or os.getenv("GAISTUDIO_API_KEY")
        st.session_state.gemini_client = genai.Client(api_key=api_key)
        st.session_state.gemini_client.models.list()
        st.session_state.connection_ok = True
        st.session_state.connection_reason = ""
    except Exception as exc:
        st.session_state.connection_ok = False
        st.session_state.connection_reason = str(exc).splitlines()[0][:120]
    st.session_state.connection_checked = True


def extract_chunks(uploaded_file: object) -> list[str]:
    reader = PdfReader(uploaded_file)
    text = "\n".join(page.extract_text() or "" for page in reader.pages).strip()
    if not text:
        raise ValueError("The PDF does not contain extractable text.")
    words = text.split()
    chunk_size = 220
    overlap = 40
    chunks = []
    step = chunk_size - overlap
    for start in range(0, len(words), step):
        chunk = " ".join(words[start : start + chunk_size]).strip()
        if chunk:
            chunks.append(chunk)
    return chunks


def embed_texts(texts: list[str]) -> list[list[float]]:
    response = st.session_state.gemini_client.models.embed_content(
        model=EMBEDDING_MODEL,
        contents=texts,
    )
    return [embedding.values for embedding in response.embeddings]


def fallback_model(model: str) -> str:
    return "gemini-3.5-flash-lite" if model == "gemini-3.5-flash" else "gemini-3.5-flash"


def stream_gemini(contents: list[dict[str, object]]) -> Iterable[str]:
    selected = st.session_state.chat_model
    try:
        stream = st.session_state.gemini_client.models.generate_content_stream(
            model=selected,
            contents=contents,
        )
        for chunk in stream:
            if chunk.text:
                yield chunk.text
    except Exception:
        stream = st.session_state.gemini_client.models.generate_content_stream(
            model=fallback_model(selected),
            contents=contents,
        )
        for chunk in stream:
            if chunk.text:
                yield chunk.text


def conversation_contents() -> list[dict[str, object]]:
    return [
        {"role": message["role"], "parts": [{"text": message["content"]}]}
        for message in st.session_state.messages
        if message["role"] in {"user", "model"}
    ]


with st.sidebar:
    st.subheader("Connection")
    if st.session_state.connection_ok:
        st.success("🟢 Connected to Gemini")
    else:
        st.error(f"🔴 Not connected — {st.session_state.connection_reason}")

    st.session_state.chat_model = st.selectbox(
        "Chat model",
        CHAT_MODELS,
        index=CHAT_MODELS.index(st.session_state.chat_model),
    )

    uploaded_file = st.file_uploader("Upload a PDF", type=["pdf"], accept_multiple_files=False)
    if uploaded_file is not None and st.session_state.get("indexed_file_id") != uploaded_file.file_id:
        with st.spinner("Extracting, chunking, embedding, and storing your PDF..."):
            chunks = extract_chunks(uploaded_file)
            embeddings = embed_texts(chunks)
            chroma_client = chromadb.Client()
            collection_name = "dinesh_ai_pdf"
            collection_names = [collection.name for collection in chroma_client.list_collections()]
            if collection_name in collection_names:
                chroma_client.delete_collection(collection_name)
            collection = chroma_client.create_collection(collection_name)
            collection.add(
                ids=[f"chunk-{index}" for index in range(len(chunks))],
                documents=chunks,
                embeddings=embeddings,
            )
            st.session_state.chroma_collection = collection
            st.session_state.indexed_file_id = uploaded_file.file_id
        st.success("Ready to chat with your PDF.")
    elif st.session_state.get("indexed_file_id") == getattr(uploaded_file, "file_id", None):
        st.success("Ready to chat with your PDF.")

    if st.button("Clear conversation"):
        st.session_state.messages = []
        st.rerun()

for message in st.session_state.messages:
    with st.chat_message("assistant" if message["role"] == "model" else message["role"]):
        st.markdown(message["content"])
        if message.get("mode") == "pdf":
            st.caption("📄 Answered using your PDF")
        elif message.get("mode") == "general":
            st.caption("💬 Answered from general knowledge — no PDF uploaded")

prompt = st.chat_input("Ask Gemini anything, or ask about your PDF...")
if prompt:
    if not st.session_state.connection_ok:
        st.error("Gemini is not connected. Check GEMINI_API_KEY in your .env file and try again.")
    else:
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)
        try:
            collection = st.session_state.get("chroma_collection")
            if collection is not None:
                question_embedding = embed_texts([prompt])[0]
                results = collection.query(query_embeddings=[question_embedding], n_results=3)
                context = "\n\n".join(results.get("documents", [[]])[0])
                contents = conversation_contents()[:-1]
                contents.append({
                    "role": "user",
                    "parts": [{"text": (
                        "Answer only from the PDF content below. If the answer is not in it, say plainly "
                        "that it is not in the provided PDF.\n\nPDF content:\n" + context + "\n\nQuestion:\n" + prompt
                    )}],
                })
                mode = "pdf"
            else:
                contents = conversation_contents()
                mode = "general"
            with st.chat_message("assistant"):
                answer = st.write_stream(stream_gemini(contents))
                st.caption("📄 Answered using your PDF" if mode == "pdf" else "💬 Answered from general knowledge — no PDF uploaded")
            st.session_state.messages.append({"role": "model", "content": answer, "mode": mode})
        except Exception:
            st.error("Something went wrong — try again in a moment.")

st.divider()
st.caption("Made at Dinesh AI Academy · Powered by Google Gemini")
