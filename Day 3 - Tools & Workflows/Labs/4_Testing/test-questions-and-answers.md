# Test the app: questions to ask and answers to expect

This app has exactly two tools — a calculator and a current-date-time lookup —
and the model decides for itself whether a question needs one. The test here
isn't "is the answer in a document" (that's Day 2); it's "did the model call
the right tool when it needed one, and correctly skip tools when it didn't."
The "How this reply was generated" panel under each answer is what proves it.

---

## Positive examples — the question NEEDS a tool

### 1. "What is 4562 multiplied by 8917?"
**Expect:** The panel shows `calculator` was called with that expression, and
the final answer is the correct product: **40,679,354**. A wrong number here
means the tool wasn't actually used, or its result wasn't passed back to the
model correctly.

### 2. "What's today's date and the exact time right now?"
**Expect:** The panel shows `get_current_datetime` was called (no arguments
needed), and the answer matches the real current date and time on the machine
running the app.

### 3. "If I'm 3891 days old, roughly how many years is that? Use 365.25 days
per year."
**Expect:** The panel shows `calculator` was called with an expression like
`3891 / 365.25`, and the answer is approximately **10.65 years**.

---

## Negative examples — the question needs NO tool at all

This is the more important half of the test — it proves the model isn't
calling tools reflexively for everything, only when it actually needs to.

### 4. "What's the capital of France?"
**Expect:** The panel says no tool was needed — the model answers "Paris"
directly from its own knowledge, with no calculator or datetime call.

### 5. "Explain what a system prompt is, in one sentence."
**Expect:** The panel says no tool was needed — a direct, from-knowledge
answer, since neither tool is relevant to this question.

### 6. "What's 2 + 2?"
**Expect:** This one's a judgment call worth discussing live — a model *could*
reasonably answer "4" directly without calling the calculator, since it's
trivial arithmetic. Either outcome (tool called, or answered directly) is
acceptable; what matters is that the panel accurately reflects whichever one
actually happened.
