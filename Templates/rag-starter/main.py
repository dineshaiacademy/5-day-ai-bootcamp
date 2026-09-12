import os

from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# TODO: 1. Load your documents
DOCS = [
    "Replace this with real document text loaded from files/PDFs.",
]

# TODO: 2. Embed documents and store them (e.g. FAISS, Chroma, or a simple in-memory list)


def retrieve(query: str, k: int = 1) -> list[str]:
    # TODO: replace with real similarity search over embeddings
    return DOCS[:k]


def ask(query: str) -> str:
    context = "\n".join(retrieve(query))
    prompt = f"Context:\n{context}\n\nQuestion: {query}\nAnswer using only the context above."
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": prompt}],
    )
    return response.choices[0].message.content


if __name__ == "__main__":
    print(ask("What is this document about?"))
