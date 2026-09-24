# MCP Expense Lab

A standalone streamable-HTTP MCP server and Streamlit host where an LLM manages an in-memory Smart Expense Tracker through discovered tools.

## Architecture

```text
Human ──► HOST: Streamlit app.py ──► LLM (Gemini or LM Studio)
              │                         │ chooses a tool
              ▼                         ▼
        MCP CLIENT ── streamable HTTP ──► MCP SERVER
       client/mcp_client.py               server/mcp_server.py
              ◄──────── tool result ─────────┘
```

| Capability | Name | Purpose |
|---|---|---|
| Tool | `add_expense` | Add a validated INR expense |
| Tool | `list_expenses` | List newest expenses, optionally filtered |
| Tool | `delete_expense` | Safely delete an expense by id |
| Tool | `get_spending_summary` | Total, count, average, and category breakdown |
| Tool | `convert_currency` | Convert with fixed static demo rates |
| Tool | `calculate` | Safe AST arithmetic |
| Tool | `get_current_date` | Date, weekday, and ISO timestamp |
| Resource | `expenses://all` | JSON snapshot of the in-memory book |
| Prompt | `monthly_report` | Asks the model to gather a monthly report with tools |

## Quickstart

From this folder, with the bootcamp repository's Python 3.12 environment active:

```text
(0) pip install -r requirements.txt
(1) Terminal 1: start_server.bat       # or: ./start_server.sh
(2) Terminal 2: streamlit run app.py
```

The first run creates `.env` automatically and never overwrites an existing one. Gemini is selected by default: paste a key in the sidebar and click **Save key to .env**, then choose any model from **Model**. No external key is needed by the MCP tools themselves.

## Choosing provider & model

The sidebar remembers a separate model for Gemini and LM Studio, keeps chat history when switching providers, supports a custom model name, and shows a provider health status. Enable **Auto-fallback to LM Studio if Gemini fails** to retry one failed Gemini request locally.

## Gemini not working? Switch to LM Studio

Use the provider radio control to select **LM Studio (local)**. Chat history is preserved and the local model list is refreshed independently. The automatic fallback toggle retries the same message once; it never loops between providers. If both providers fail, the UI names both failures.

## LM Studio setup

1. Open LM Studio and load a tool-capable instruct model such as `Qwen2.5-7B-Instruct`.
2. Open the **Developer** tab and choose **Start Server**.
3. Keep the OpenAI-compatible server at `http://localhost:1234/v1`, or update `LOCAL_LLM_BASE_URL` in `.env`.
4. Select LM Studio in the app and choose the loaded model.

## Try these prompts

- Add 450 rupees for lunch today
- How much did I spend on travel?
- Convert my total spending to USD
- Delete expense 2 and show the new summary

## Exercise: add your own tool

Add a `set_budget(category, amount)` or `check_budget(category)` function to `server/mcp_server.py` with a complete type hint and one-line docstring. Restart the server: the Tool Explorer discovers its schema automatically, and the agent can select it without a client-side schema change.

## Troubleshooting

- **Port in use:** change `MCP_SERVER_PORT` in `.env` and use the same value for the server and client, then restart both.
- **Server not running:** run `python server/mcp_server.py` from this project; the sidebar prints the exact command.
- **Invalid Gemini key:** create a key at https://aistudio.google.com/apikey and save it in the sidebar.
- **Gemini quota hit:** switch to LM Studio or wait for the quota window; the fallback toggle handles the first failure.
- **Model not found:** select a model returned by the provider's Model dropdown or type the exact local model id.
- **Model does not call tools:** load an instruct model with function/tool-calling support, such as Qwen or Llama instruct, and retry.
- **LM Studio unreachable:** use Developer → Start Server and load a model before refreshing the app.

The expense store is intentionally in memory for teaching: restarting the MCP server restores the five sample records.
