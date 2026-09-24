# Test the app: questions to ask and answers to expect

This app has exactly two tools — `calculate` and `get_weather` — and the model
decides for itself whether a question needs one. The test here isn't "is the
answer in a document" (that's Day 2); it's "did the model call the right tool
when it needed one, and correctly skip tools when it didn't." The Tool-Call
Trace panel under each answer (toggle it on in the sidebar) is what proves it.

---

## Positive examples — the question NEEDS a tool

### 1. "What's 47 times 89?"
**Expect:** The trace shows `calculate` was called with that expression, and
the final answer is the correct product: **4,183**. This is the exact example
from the LMS practice page.

### 2. "What's the weather in Delhi?"
**Expect:** The trace shows `get_weather` was called with `"Delhi"`, and the
final answer reports the (simulated) temperature and conditions it returned.
This is also directly from the LMS practice page. The weather data is mocked,
not live — that's expected at this scope.

### 3. "If I'm 3891 days old, roughly how many years is that? Use 365.25 days
per year."
**Expect:** The trace shows `calculate` was called with an expression like
`3891 / 365.25`, and the answer is approximately **10.65 years**.

---

## Negative examples — the question needs NO tool at all

This is the more important half of the test — it proves the model isn't
calling tools reflexively for everything, only when it actually needs to.

### 4. "Explain what an AI tool is."
**Expect:** The trace shows no tool was called — a direct, from-knowledge
answer. This is the exact "no tool required" example from the LMS practice
page.

### 5. "What's the capital of France?"
**Expect:** The trace shows no tool was needed — the model answers "Paris"
directly, with no calculator or weather call.

### 6. "What's 2 + 2?"
**Expect:** This one's a judgment call worth discussing live — a model *could*
reasonably answer "4" directly without calling `calculate`, since it's trivial
arithmetic. Either outcome (tool called, or answered directly) is acceptable;
what matters is that the trace panel accurately reflects whichever one
actually happened.

---

## Provider check — run the same test twice
This app supports both Gemini and LM Studio. If any of the above misbehaves on
one provider, switch to the other in the sidebar and re-ask the exact same
question:
- Fails on both → the bug is in the app's tool-calling logic.
- Fails only on Gemini → likely a key, quota, or model-availability issue on
  the Gemini side, not the app.
- Fails only on LM Studio → check that LM Studio is running locally with a
  model loaded that actually supports tool calling (not every local model
  does).

## After the base build works
Try the LMS's practice challenge: add a third tool yourself (e.g.
`get_current_time()`) and ask a question that should trigger it, to confirm
the model picks it up correctly alongside the original two.
