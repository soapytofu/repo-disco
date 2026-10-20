# <experiment-id> — <short description>

**Outcome:** PENDING / PASS / FAIL / INCOMPLETE. Date: YYYY-MM-DD.

| Field | Record |
| --- | --- |
| Question | What does this experiment test? |
| Parent / input program | Experiment ID and file link, or seed |
| Model / provider | Exact model ID, relevant settings, provider/region |
| Run / source revision | Run directory and Git commit; note local code changes |
| Environment | Python, Dafny, Z3, relevant SDK versions |
| Budget / actual attempts | Separate configured limits from observed counts |
| Verifier result | Exact verified/error counts, or why verification did not run |
| Task preservation | Confirmed / failed / not reviewed, with explanation |
| Token usage / measured cost | Observed values, or not captured |

**Change:** one sentence describing what the model generated or modified.

**Evidence:** link input, output, model prompt/response, resolved config, verifier output, and scheduler log. List missing artifacts explicitly.

**Interpretation:** what this result supports and its main limitation.

**Next step:** one concrete follow-up.

Do not include API keys, credentials, or private account details.
