# 5-Day AI Bootcamp

## 🧩 Templates

Before starting a new project, check [`Templates/`](Templates) for ready-made boilerplate (Streamlit UI, plain LLM API script, RAG starter) — copy one into the relevant day's `Projects/` folder instead of starting from scratch.

## 🧠 Skills

[`.claude/skills/`](.claude/skills) holds Claude Code **skills** — each a `<name>/SKILL.md` (+ optional `references/`) that Claude Code auto-discovers and can invoke directly (e.g. `/build-premium-chat-app`), or that you can trigger just by describing what you want. The `references/` content is plain text, so it also works pasted manually into any other LLM.

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
