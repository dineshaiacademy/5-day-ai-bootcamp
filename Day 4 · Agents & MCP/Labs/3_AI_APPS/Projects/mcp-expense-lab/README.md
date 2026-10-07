# MCP Expense Lab

A standalone MCP server plus a Streamlit app where Google Gemini manages an in-memory Smart Expense Tracker by calling MCP tools.

## Architecture

```text
Human ──► HOST: Streamlit app.py ──► Gemini
              │                        │ chooses a tool
              ▼                        ▼
        MCP CLIENT ── streamable HTTP ──► MCP SERVER
       client/mcp_client.py               server/mcp_server.py
              ◄──────── tool result ─────────┘
```

| Capability | Name | Purpose |
|---|---|---|
| Tool | `add_expense` | Add one validated INR expense |
| Tool | `list_expenses` | List newest expenses, optionally by category / month |
| Tool | `delete_expense` | Safely delete an expense by id |
| Tool | `get_spending_summary` | Total, count, average, category breakdown (optional category / month) |
| Tool | `convert_currency` | Convert with fixed static demo rates |
| Tool | `calculate` | Safe arithmetic (no `eval`) |
| Tool | `get_current_date` | Date, weekday, ISO timestamp |
| Resource | `expenses://all` | JSON snapshot of the in-memory expense book |
| Prompt | `monthly_report` | Asks the model to build a monthly report with the tools |

## Quickstart

1. Install: `pip install -r requirements.txt`
2. Open `.env` and paste your Gemini key after `GEMINI_API_KEY=` (get one at https://aistudio.google.com/apikey). No `.env`? Copy `.env.example` to `.env`.
3. Terminal 1 - start the MCP server: `start_server.bat` (Windows) or `bash start_server.sh` (Mac/Linux). Leave it running.
4. Terminal 2 - start the app from the same folder: `streamlit run app.py`, then open http://localhost:8501

## Try these prompts

- How much did I spend on travel?
- Add 450 rupees for lunch today
- Convert my total spending to USD
- Delete expense 2 and show the new summary
- Give me a monthly report for September 2026
- What's the weather like today? (no tool exists for this - the agent should say so plainly)

## Reliability built in

If Gemini is rate-limited or briefly overloaded, the app automatically tries the other Gemini models in the Model list, then waits and retries, and shows a "retrying" notice instead of failing. The caption under each answer shows which model actually answered.

## Exercise: add your own tool

Add `set_budget(category, amount)` / `check_budget(category)` to `server/mcp_server.py` with full type hints, a one-line docstring and the `@mcp.tool()` decorator. Restart the server - the Tool Explorer tab discovers it automatically and the agent can use it with no client changes.

## Troubleshooting

- **"No GEMINI_API_KEY found":** paste the key into `.env`, save, refresh the page.
- **"API key was rejected":** re-copy the key from Google AI Studio (no spaces or quotes), save `.env`, refresh.
- **MCP server offline in the sidebar:** start `python server/mcp_server.py` in its own terminal first.
- **Port already in use:** change `MCP_SERVER_PORT` in `.env`, then restart both the server and the app.
- **`ImportError: MCPServer`:** you have an old `mcp` package - run `pip install -U "mcp>=2.0"`.
- **Answers are slow:** Gemini free-tier quotas are small; a paid key removes most waiting.

The expense book is in memory on purpose: restarting the MCP server restores the five sample records.
