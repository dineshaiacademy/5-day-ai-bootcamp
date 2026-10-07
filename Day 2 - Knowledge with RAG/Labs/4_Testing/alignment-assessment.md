# Alignment assessment: test questions vs. source document

This checks that every question in
[`test-questions-and-answers.md`](test-questions-and-answers.md) is genuinely
answerable (or genuinely not answerable) from
[`../2_Docs/Dinesh_AI_Academy_Policies.pdf`](../2_Docs/Dinesh_AI_Academy_Policies.pdf)
/ [`.md`](../2_Docs/Dinesh_AI_Academy_Policies.md) — so the demo doesn't rely on
the model guessing right by luck.

## How this was verified
- The PDF's text was extracted (via `pypdf`) and compared against the `.md`
  source it was generated from — both are identical in content, so there's no
  drift between the two formats.
- Each positive question was matched to the exact section of the document that
  answers it.
- Each negative question was checked against all 10 sections to confirm the
  topic is genuinely absent, not just paraphrased differently.

## Results

| Question | Source section | Verdict |
|---|---|---|
| Q1 "What happens if I miss a class?" | §3 Attendance policy | ✅ answer present, matches exactly |
| Q2 "Cancel 3 days before — refund?" | §4 Cancellation & refund (falls in the 6–2 day / 50% window) | ✅ answer present, matches exactly |
| Q3 "What do I need to do for the certificate?" | §6 Certificate requirements | ✅ answer present, matches exactly |
| Q4 "Pets policy?" | — | ✅ genuinely absent, no section mentions it |
| Q5 "Who's the founder?" | — | ✅ genuinely absent, doc has zero bio/founder content |
| Q6 "Top-of-batch scholarship?" | — | ✅ genuinely absent, no rewards/scholarship section anywhere |

## Conclusion
No mismatches. The three positive questions exercise the sections a real student
would actually ask about first (attendance, refunds, certification), and the
three negative questions are confirmed absent from all 10 sections of the
document — so a correct app should ground its "not covered" answers honestly
rather than by accident. No changes needed to either the source document or the
test question set.
