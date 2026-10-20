# repair-003 — Complete-program repair

**Outcome: PASS after a verifier-only recheck — 4 verified, 0 errors.** Date: 2026-10-20.

| Field | Record |
| --- | --- |
| Question | Can Claude repair the same failed extension when asked for complete Dafny source instead of a custom diff? |
| Parent input | Original [extension-001](../extension-001/README.md); same input hash as repair-002 |
| Model / provider | `us.anthropic.claude-sonnet-4-6` / AWS Bedrock, `us-east-1` |
| Source revision | `10c3f1785336002e3cbb6b4f79e3d01585c2ff4d` |
| Run ID | `full-program-repair-20261020T230243-365318Z` |
| Model requests | **1**; no retry or manual edit of the returned program |
| Configured budget | 4,096 output tokens; SDK retries disabled; 300-second process limit |
| Observed tokens | **541 input + 372 output = 913 total**; cache creation/read both 0 |
| Initial verification | 10-second process timeout; exit status 124; no verifier diagnostic |
| Verification recheck | Same output, 60-second process limit; **4 verified, 0 errors** in 2.524 seconds |
| Preservation review | Passed: original contracts and intended algebraic checks retained |
| Measured cost | Not captured |

**Change:** the model returned a complete source file that reattached the `TestMax` body and retained `MaxCommutative` and `TestMaxAlgebra`. It matches the previously verified assisted candidate from repair-001 except for surrounding whitespace. No assisted correction was applied to this response.

**Verification accounting:** the first invocation timed out. The backend labeled that `FAIL`, but it was not a Dafny proof or parse diagnostic. We retained that result, then verified the identical file with a larger wall-clock limit. There was **one model request and two verifier invocations**. The cause of the initial timeout is not established.

**Preservation:** `Max` keeps its original ensures clauses; `TestMax` keeps its assertions; the commutativity lemma and the commutativity/idempotence/associativity checks remain. No assumptions or verification-disabling attributes were introduced in the saved candidate. [Review record](preservation-review.json).

## Evidence

- [Final combined result](final-result.json)
- [Original input](input-program.dfy) and [model-generated output](output-program.dfy)
- [Exact prompt](prompt.json) and [response](response.json)
- [Token usage](token-usage.json)
- [Run configuration](run-config.json), [environment and source hashes](environment.json), [runner](runner.py)
- [Initial result](result.json), [initial verifier stdout](verifier-stdout.txt), [initial verifier stderr](verifier-stderr.txt)
- [Recheck result](verification-recheck.json), [successful verifier stdout](recheck-verifier-stdout.txt), [recheck stderr](recheck-verifier-stderr.txt)
- [Original verifier feedback supplied to the model](input-verifier-output.txt)

The initial `result.json` retains the runner's original timeout and pending-review fields for provenance. Use `final-result.json` and the separate preservation review for the completed outcome.

## Scope and interpretation

This was a standalone complete-program request using the same model, input program, and original verifier feedback. It bypasses the diff worker and does not update any agenda checkpoint. The prompt also explicitly requires preservation, so this is an exploratory comparison, not an experiment changing only one controlled variable.

The result shows that Claude produced a verified repair of this one program under the complete-program prompt. It does not establish that full-program responses generally outperform diffs or estimate a benchmark success rate.

The assistant executed the run through the authenticated SSH connection in the active Cannon allocation. The private key handoff was consumed and removed before the request; credentials are absent from the saved evidence.

**Next research step:** evaluate both response formats on a small, predefined set of failed programs, using matched budgets, consistent verifier limits, and preservation checks. Keep raw model outcomes distinct from assisted corrections and verifier-timeout rechecks.

[All experiments](../README.md).
