# Day 4 — Agents & MCP: Step-by-Step Lab Guide

You will use GitHub Copilot to create a working **MCP Expense Lab** — an MCP server that
exposes expense tools, and a Streamlit app where Google Gemini decides which tool to call.
Understanding *why* it is split into three pieces — Host, Client, Server — is the goal.

```text
Human ──► HOST: Streamlit app.py ──► Gemini
              │                        │ chooses a tool
              ▼                        ▼
        MCP CLIENT ── streamable HTTP ──► MCP SERVER
       client/mcp_client.py               server/mcp_server.py
              ◄──────── tool result ─────────┘
```

- **Server** — a standalone process exposing tools, a resource and a prompt. It knows nothing about the LLM.
- **Client** — connects to the server over HTTP, discovers the tools, converts them into a schema the LLM can read.
- **Host** — the Streamlit app you use. It runs Gemini, the client and the chat UI.

## Step 1 — Install Python
Install Python 3.10+ from https://www.python.org/downloads/ (Windows: tick **Add python.exe to PATH**).

## Step 2 — Install GitHub Copilot
Install VS Code, then the **GitHub Copilot** and **GitHub Copilot Chat** extensions, and sign in.

## Step 3 — Open an empty folder in Copilot
Create a new empty folder (for example `mcp-expense-lab`), open it in VS Code, open Copilot Chat and
switch to **Agent mode**. Copilot builds everything directly inside this folder.

## Step 4 — Copy the prompt
Open [`BUILD_PROMPT.md`](BUILD_PROMPT.md) (or the GitHub link from the course page) and copy everything
inside the fenced block. Do not edit it.

## Step 5 — Paste it into Copilot Chat
Paste and send. The code is already written inside the prompt, so Copilot only has to create the files,
install the packages and run its checks — usually a few minutes. No Gemini key is needed for this step.

## Step 6 — Check the folder structure
```text
your-folder/
├── app.py
├── requirements.txt
├── .env
├── .env.example
├── .gitignore
├── README.md
├── start_server.bat
├── start_server.sh
├── .streamlit/config.toml
├── server/   (__init__.py, mcp_server.py)
├── client/   (__init__.py, mcp_client.py)
└── src/      (__init__.py, env_setup.py, llm.py)
```
There should be **no extra wrapper folder** — `app.py` sits directly in the folder you opened.

## Step 7 — Add your Gemini key
Get a key at https://aistudio.google.com/apikey, open `.env`, paste it after `GEMINI_API_KEY=` and save.
(If `.env` is missing, copy `.env.example` to `.env`; the app also creates it on first run.)
Never share the key or commit it to GitHub.

## Step 8 — Start the MCP server (Terminal 1)
Run `start_server.bat` (Windows) or `bash start_server.sh` (Mac/Linux). You should see a banner with the
endpoint `http://127.0.0.1:8766/mcp` and the 7 tools. **Leave this window open.**

## Step 9 — Start the app (Terminal 2)
In a second terminal, in the same folder:
```bash
streamlit run app.py
```
Open http://localhost:8501. The sidebar should show **✅ Connected to Gemini** and **✅ Online** for the MCP server.

## Step 10 — Take the tour
- **💬 Agent Chat** — ask questions; expand **🔧 Tool calls** under a reply to see what was called.
- **🧰 Tool Explorer** — call any tool yourself, no LLM involved.
- **📚 Resources & Prompts** — read `expenses://all` and the `monthly_report` prompt.
- **🏗️ How it works** — the architecture diagram.

## Step 11 — Try these questions
The server starts with 5 sample expenses (₹4,419). Ask them in order:

1. "How much did I spend on travel?" → ₹600.
2. "Add 450 rupees for lunch today" → one `add_expense` call; total becomes ₹4,869.
3. "Convert my total spending to USD" → summary + `convert_currency`; ≈ $58.66.
4. "Delete expense 2 and show the new summary" → `delete_expense` then a summary.
5. "Give me a monthly report for September 2026" → `get_spending_summary` with `month="2026-09"`.
6. "What's the weather like today?" → **no tool** — the agent should say it can't, not invent an answer.

Restarting the MCP server resets the expenses to the 5 samples.

## What to observe
```text
User request → Gemini decides if a tool is needed → tool + arguments chosen
→ tool runs on the SERVER over HTTP (not inside the model) → result returns to Gemini → final answer
```
The line under each answer says which Gemini model answered. If the first model is rate-limited or busy,
the app automatically tries another Gemini model (or waits and retries) instead of failing.

## 🏆 Practice challenge — add your own tool
1. In `server/mcp_server.py` add e.g. `set_budget(category: str, amount: float) -> dict` and
   `check_budget(category: str) -> dict` (a simple dict holds the budgets) with full type hints,
   a one-line docstring and the `@mcp.tool()` decorator.
2. Stop the server (Ctrl+C) and start it again.
3. Do **not** touch the client or the app — the Tool Explorer discovers your tool automatically.
4. Test it in Tool Explorer, then ask the agent: "Set my food budget to 2000 rupees" and "Am I over my food budget?"

## If something goes wrong
- **"No GEMINI_API_KEY found"** — paste the key into `.env`, save, refresh the page.
- **"API key was rejected"** — re-copy the key (no spaces or quotes), save `.env`, refresh.
- **MCP server shows Offline** — start the server (Step 8) before using the app.
- **Port 8766 in use** — change `MCP_SERVER_PORT` in `.env`, restart both the server and the app.
- **`ImportError: MCPServer`** — an old `mcp` package: `pip install -U "mcp>=2.0"`.
- **Slow answers** — free Gemini keys have small quotas; a paid key removes most waiting.

More test questions with expected answers: [`../4_Testing/test-questions-and-answers.md`](../4_Testing/test-questions-and-answers.md).
A finished reference copy of this app is in [`../3_AI_APPS/Projects/mcp-expense-lab`](../3_AI_APPS/Projects/mcp-expense-lab).
