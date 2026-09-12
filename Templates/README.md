# 🧩 Templates

Reusable boilerplate for common project types, so you don't rebuild the same scaffolding in every day's `Projects/` folder.

## Available templates

| Template | Use it for |
|---|---|
| [`streamlit-basic/`](streamlit-basic) | A minimal Streamlit UI wired to an LLM call |
| [`llm-api-integration/`](llm-api-integration) | A plain Python script that calls an LLM API — no UI |
| [`rag-starter/`](rag-starter) | A minimal Retrieval-Augmented Generation scaffold (load → embed → query) |

## How to use a template

Copy the template folder into the day's `Projects/` folder and rename it:

```bash
cp -r "Templates/streamlit-basic" "Day 2 - Knowledge with RAG/Projects/my-new-project"
cd "Day 2 - Knowledge with RAG/Projects/my-new-project"
python -m venv venv
venv\Scripts\activate        # Windows
pip install -r requirements.txt
cp .env.example .env         # then fill in your keys
streamlit run app.py
```

Every template is self-contained: `app.py` (or `main.py`), `requirements.txt`, and `.env.example`.
