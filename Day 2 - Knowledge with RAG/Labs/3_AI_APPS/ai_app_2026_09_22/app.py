import os
from io import BytesIO

import chromadb
import streamlit as st
from dotenv import load_dotenv
from google import genai
from google.genai import types
from pypdf import PdfReader


CHAT_MODELS = [
    "gemini-3.6-flash",
    "gemini-3.5-flash",
    "gemini-3.5-flash-lite",
]
FALLBACK_MODEL = "gemini-3.5-flash"
ALTERNATE_FALLBACK_MODEL = "gemini-3.5-flash-lite"
EMBEDDING_MODEL = "gemini-embedding-001"
COLLECTION_NAME = "pdf_chunks"

st.set_page_config(page_title="Dinesh AI Academy · PDF Chat", page_icon="📄")
load_dotenv()


def initialize_state():
    if "messages" not in st.session_state:
        st.session_state.messages = []
    if "connection_checked" not in st.session_state:
        st.session_state.connection_checked = False
        st.session_state.connected = False
        st.session_state.connection_reason = ""
    if "selected_model" not in st.session_state:
        st.session_state.selected_model = CHAT_MODELS[0]
    if "chroma_collection" not in st.session_state:
        st.session_state.chroma_collection = None
    if "indexed_file_id" not in st.session_state:
        st.session_state.indexed_file_id = None
    if "client" not in st.session_state:
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            st.session_state.connection_reason = "GEMINI_API_KEY is missing"
        else:
            st.session_state.client = genai.Client(api_key=api_key)
            try:
                st.session_state.client.models.list()
                st.session_state.connected = True
            except Exception as exc:
                st.session_state.connection_reason = str(exc).splitlines()[0][:120]
        st.session_state.connection_checked = True


def chunk_text(text, chunk_size=1200, overlap=200):
    text = " ".join(text.split())
    if not text:
        return []
    chunks = []
    start = 0
    while start < len(text):
        end = min(start + chunk_size, len(text))
        chunks.append(text[start:end])
        if end == len(text):
            break
        start = end - overlap
    return chunks


def embed_text(text):
    response = st.session_state.client.models.embed_content(
        model=EMBEDDING_MODEL,
        contents=text,
    )
    return response.embeddings[0].values


def index_pdf(uploaded_file):
    reader = PdfReader(BytesIO(uploaded_file.getvalue()))
    chunks = chunk_text("\n".join(page.extract_text() or "" for page in reader.pages))
    if not chunks:
        raise ValueError("The PDF does not contain extractable text.")

    chroma_client = chromadb.Client()
    collection_names = [c.name for c in chroma_client.list_collections()]
    if COLLECTION_NAME in collection_names:
        chroma_client.delete_collection(COLLECTION_NAME)
    collection = chroma_client.create_collection(COLLECTION_NAME)
    embeddings = [embed_text(chunk) for chunk in chunks]
    collection.add(
        ids=[f"chunk-{index}" for index in range(len(chunks))],
        documents=chunks,
        embeddings=embeddings,
    )
    st.session_state.chroma_collection = collection
    st.session_state.indexed_file_id = f"{uploaded_file.name}:{uploaded_file.size}"


def stream_answer(prompt):
    selected_model = st.session_state.selected_model
    fallback_model = (
        ALTERNATE_FALLBACK_MODEL
        if selected_model == FALLBACK_MODEL
        else FALLBACK_MODEL
    )
    try:
        response = st.session_state.client.models.generate_content_stream(
            model=selected_model,
            contents=prompt,
        )
        return (chunk.text for chunk in response if chunk.text)
    except Exception:
        response = st.session_state.client.models.generate_content_stream(
            model=fallback_model,
            contents=prompt,
        )
        return (chunk.text for chunk in response if chunk.text)


def answer_question(question):
    collection = st.session_state.chroma_collection
    if collection is None:
        prompt = question
        mode_caption = "💬 Answered from general knowledge — no PDF uploaded"
    else:
        question_embedding = embed_text(question)
        results = collection.query(query_embeddings=[question_embedding], n_results=3)
        context = "\n\n".join(results["documents"][0])
        prompt = (
            "Answer the user's question only from the PDF content below. "
            "If the answer is not in that content, say plainly that it is not "
            "in the PDF.\n\nPDF content:\n"
            f"{context}\n\nUser question: {question}"
        )
        mode_caption = "📄 Answered using your PDF"
    return stream_answer(prompt), mode_caption


initialize_state()

st.title("Dinesh AI Academy — Chat With Your PDF")

with st.sidebar:
    st.subheader("Connection")
    if st.session_state.connected:
        st.success("🟢 Connected to Gemini")
    else:
        st.error(
            f"🔴 Not connected — {st.session_state.connection_reason or 'unknown error'}"
        )

    selected_model = st.selectbox(
        "Chat model",
        CHAT_MODELS,
        index=CHAT_MODELS.index(st.session_state.selected_model),
    )
    st.session_state.selected_model = selected_model

    uploaded_file = st.file_uploader("Upload a PDF", type=["pdf"])
    if uploaded_file is not None:
        file_id = f"{uploaded_file.name}:{uploaded_file.size}"
        if file_id != st.session_state.indexed_file_id:
            with st.spinner("Extracting, chunking, embedding, and storing PDF..."):
                try:
                    index_pdf(uploaded_file)
                    st.success("Ready to chat with your PDF.")
                except Exception:
                    st.session_state.chroma_collection = None
                    st.session_state.indexed_file_id = None
                    st.error("Could not index that PDF. Please try another file.")

    if st.button("Clear conversation"):
        st.session_state.messages = []
        st.rerun()

for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])
        if message.get("caption"):
            st.caption(message["caption"])

question = st.chat_input("Ask Gemini a question...")
if question:
    st.session_state.messages.append({"role": "user", "content": question})
    with st.chat_message("user"):
        st.markdown(question)

    with st.chat_message("assistant"):
        if not st.session_state.connected:
            st.error("Gemini is not connected. Check your .env file and try again.")
        else:
            try:
                answer_stream, mode_caption = answer_question(question)
                answer = st.write_stream(answer_stream)
                st.caption(mode_caption)
                st.session_state.messages.append(
                    {
                        "role": "assistant",
                        "content": answer,
                        "caption": mode_caption,
                    }
                )
            except Exception:
                st.error("Something went wrong — try again in a moment.")

st.divider()
st.caption("Made at Dinesh AI Academy · Powered by Google Gemini")
