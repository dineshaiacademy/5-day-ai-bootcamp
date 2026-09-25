# Test the app: questions to ask and answers to expect

This tests the **MCP Expense Lab** — a Gemini agent with 7 tools (add / list / delete expenses,
spending summary, currency conversion, calculator, current date) reached over an MCP server.
**Restart the MCP server first** so you start from the same 5 sample expenses (₹4,419 total), then ask
the questions in order in the **Agent Chat** tab. Expand **🔧 Tool calls** under each reply to check the trace.

---

## Positive examples — the question NEEDS a tool

### 1. "How much did I spend on travel?"
**Expect:** `get_spending_summary` (or `list_expenses`) with `category="travel"`. The one travel expense
(Metro recharge) is **₹600**.

### 2. "Add 450 rupees for lunch today"
**Expect:** exactly **one** `add_expense` call (`amount=450`, `category="food"`). The new total is **₹4,869**.
(A second identical `add_expense` in the trace would be a bug — the app blocks duplicate calls.)

### 3. "Convert my total spending to USD"
**Expect:** a spending-summary call followed by `convert_currency` (fixed demo rate: 83 INR = 1 USD).
After test 2 the answer is **≈ $58.66**; on a fresh server it would be ≈ $53.24.

### 4. "Delete expense 2 and show the new summary"
**Expect:** `delete_expense` with `expense_id=2` (the "Metro recharge", ₹600), then a summary call.
After tests 1–3 the total drops to **₹4,269**.

### 5. "What's (348 times 12) minus 900, then add 15% to that?"
**Expect:** a `calculate` call, result **3,767.4** — the agent uses the tool instead of doing the math itself.

### 6. "Give me a monthly report for September 2026"
**Expect:** `get_spending_summary` called with `month="2026-09"` (optionally `list_expenses` too). The numbers
come from the tool, not from the model adding things up — on a fresh server: **₹4,419 across 5 expenses**.

### 7. "What is today's date?"
**Expect:** a `get_current_date` call and the real date and weekday.

---

## Negative examples — no tool exists, or none is needed

This is the more important half: it proves the agent only uses tools it really has.

### 8. "What's the weather like today?"
**Expect:** **no tool call.** The agent says plainly it can't check the weather — it must not invent one.

### 9. "What's the capital of France?"
**Expect:** no tool call — a direct answer, "Paris".

### 10. "Explain what MCP stands for."
**Expect:** no tool call — "Model Context Protocol".

---

## Reliability checks

- **Model attribution:** the caption under every answer shows which Gemini model answered. With a free key
  it is normal to see a lite model sometimes — the app switches models when one is rate-limited.
- **Rate-limit recovery:** ask 5–6 questions quickly. You should see every question answered, possibly with
  a "Gemini is busy or rate-limited. Retrying in Ns…" notice — never a raw error or a blank answer.
- **Bad key:** put a wrong key in `.env`, refresh the page → the sidebar shows the key was rejected and the
  app explains how to fix it.
- **No key:** empty `GEMINI_API_KEY=` → a warning explains what to do and the chat box is disabled.
- **Server stopped:** stop the MCP server and ask a question → a message with the exact command to start it.

## After the base build works
Do the practice challenge in
[`../1_Prompts/STUDENT_STEP_BY_STEP_GUIDE.md`](../1_Prompts/STUDENT_STEP_BY_STEP_GUIDE.md): add a `set_budget` /
`check_budget` tool to the server, restart it, and confirm the Tool Explorer finds it with no client changes.
