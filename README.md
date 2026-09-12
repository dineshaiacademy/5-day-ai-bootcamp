# 5-Day AI Bootcamp

## 🧩 Templates

Before starting a new project, check [`Templates/`](Templates) for ready-made boilerplate (Streamlit UI, plain LLM API script, RAG starter) — copy one into the relevant day's `Projects/` folder instead of starting from scratch.

## 🧠 Skills

[`skills/`](skills) holds reusable **prompts** (not code) — paste one into any LLM to generate a project from scratch, rather than writing it by hand. Model-agnostic by design: the same prompt should produce a working result whether you run it through Claude, GPT, Gemini, DeepSeek, or a local model.

## 📂 Repository Structure

Each day is split into two independent folders:

```
Day N - Topic/
├── Learning/     ← concepts, ideas, tools, framework notebooks (VS Code or Colab)
└── Projects/     ← one or more hands-on projects (UI + API + LLM integrations)
```

- **`Learning/`** holds the day's teaching notebooks — theory, demos, exercises.
- **`Projects/`** holds real, runnable apps. A day can have zero, one, or many projects; each project is a self-contained folder:

```
Projects/<project-name>/
├── app.py             # Streamlit / UI entry point
├── requirements.txt   # project-specific dependencies
├── .env.example       # template for required API keys (never commit real .env)
└── src/                # optional: helper modules, LLM/API integration code
```

Example — Day 1 currently has two sample projects side by side:

```
Day 1 - LLM Fundamentals/
├── Learning/
│   └── test.ipynb
└── Projects/
    ├── sample-project-1/
    └── sample-project-2/
```

## 🔐 Secrets

- **VS Code / local**: copy a project's `.env.example` to `.env` and fill in your keys (`.env` is gitignored).
- **Colab**: use the 🔑 Secrets manager in the sidebar instead of a `.env` file.

## ▶️ Running a project

```bash
cd "Day 1 - LLM Fundamentals/Projects/sample-project-1"
python -m venv venv
venv\Scripts\activate        # Windows
pip install -r requirements.txt
streamlit run app.py
```
