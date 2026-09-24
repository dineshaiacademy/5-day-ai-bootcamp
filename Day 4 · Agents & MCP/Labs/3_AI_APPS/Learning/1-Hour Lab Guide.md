# Day 4 · Agents & MCP — Smart Expense Tracker Lab

## Learning objectives

By the end of this one-hour lab, learners can:

- Explain the difference between an MCP host, client, and standalone server.
- Expose typed Python functions as MCP tools, plus a resource and reusable prompt.
- Connect to a streamable-HTTP server, discover schemas, and call tools without hard-coding them.
- Trace an LLM agent loop: model chooses, MCP client executes, tool result returns to the model.
- Select Gemini or a local LM Studio model and explain safe fallback behavior.

## Timeline

| Time | Activity |
|---|---|
| 0–10 min | **MCP concepts:** protocol, host/client/server boundaries, tools vs resources vs prompts, and streamable HTTP. |
| 10–25 min | **Build and walk the server:** inspect `MCPServer`, the typed expense tools, safe calculator, resource, prompt, and in-memory state. |
| 25–40 min | **Client + agent loop:** discover schemas, convert MCP tools to OpenAI function schemas, execute tool calls, and inspect the trace. |
| 40–55 min | **Hands-on exercises:** use the Tool Explorer, change provider, test fallback, and add a new tool. |
| 55–60 min | **Recap:** share one design decision, complete the quiz, and identify one production improvement. |

## Setup

Run `pip install -r requirements.txt`, start `server/mcp_server.py` in one terminal, and run `streamlit run app.py` in another. The app creates `.env` on first run. Gemini is the default; LM Studio is available locally without a cloud key.

## Graded exercises

### 1. Direct MCP discovery (30%)

Open **Tool Explorer**, discover the server, call `add_expense` with amount `450`, category `food`, and a description, then call `get_spending_summary`.

**Expected result:** a new record is returned with the next integer id; the summary count increases by one and the INR total increases by 450.

### 2. Agent orchestration (35%)

In **Agent Chat**, ask: “Delete expense 2 and show the new summary.” Open **Tool calls**.

**Expected result:** the trace shows `delete_expense` followed by `get_spending_summary` (the exact order may vary only if the model can safely satisfy both); the final answer reflects the deleted record and updated totals.

### 3. Provider resilience and extension (35%)

With Gemini selected and auto-fallback enabled, use an invalid key or unavailable Gemini endpoint, then select LM Studio if available. Add a typed `check_budget` server tool and restart the server.

**Expected result:** the UI explains the Gemini failure and does not offer a fake answer; a working local model is identified as the responder. Tool Explorer discovers `check_budget` and renders its JSON-schema inputs without editing the client.

## Quiz (with answers)

1. **What is the MCP client responsible for?**  
   **Answer:** Establishing the MCP session, discovering capabilities, and sending tool/resource/prompt requests; it does not choose tools or provide an LLM.

2. **Why is the server a separate process in this lab?**  
   **Answer:** It demonstrates an independently managed network service whose lifecycle is decoupled from the Streamlit host and LLM provider.

3. **What does the model do in the agent loop?**  
   **Answer:** It chooses whether and which tool to call; the MCP client performs the actual call and returns the result for the model to interpret.

4. **Why does `calculate` use `ast` instead of `eval`?**  
   **Answer:** A restricted AST visitor can allow only numeric arithmetic operators and reject arbitrary names, calls, attributes, and code execution.

5. **When should Gemini fallback happen?**  
   **Answer:** Only after a Gemini `ProviderError` when auto-fallback is enabled; it retries the same request once with LM Studio and never loops. MCP server outages propagate separately because changing an LLM cannot fix a stopped server.

## Reflection

The demo uses in-memory data and static exchange rates to keep attention on protocol boundaries. In production, add durable storage, authentication, audit logs, live rates with clear provenance, input limits, and a model/provider policy appropriate to the data.
