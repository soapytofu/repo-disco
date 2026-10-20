# repair-002 — Fresh Claude trial with strict patch validation

**Outcome: FAIL — malformed edit rejected; input program unchanged.** Date: 2026-10-20.

| Field | Record |
| --- | --- |
| Question | Does a fresh repair attempt produce a valid edit with explicit anchor instructions and strict validation? |
| Parent input | Original failed [extension-001](../extension-001/README.md), not the output of repair-001 |
| Model / provider | `us.anthropic.claude-sonnet-4-6` / AWS Bedrock, `us-east-1` |
| Source revision | `39beffaff58bcddff392d2b2c9809349948aa95d` |
| Run ID | `bedrock-repair-20261020T174429-927120Z` |
| Model invocations / completions | **1 / 1** |
| Budget | 1 additional attempt; 4,096 output-token cap; SDK retries disabled; 300-second process limit |
| Observed tokens | **885 input + 166 output = 1,051 total**; cache creation/read both 0 |
| Measured cost | Not captured; do not treat the token cap as actual usage |
| Final task state | `ATTEMPTED`; cumulative attempt count 2 → 3 |
| Failure stage | Patch parsing/application, before program update or new Dafny verification |
| Error | `Malformed anchor at diff line 3: expected @@ context @@` |
| Program preservation | Output bytes identical to input bytes |
| New verifier result | **Not run** — no new candidate was applied |

**What changed from repair-001:** the patch reader rejects malformed or unmatched directives, and the actual system prompt explicitly requires both opening and closing `@@` markers. The supplied example also shows both markers. This was a fresh response to the original failed extension.

**What happened:** Claude again identified the disconnected method body, but emitted two anchors without their closing markers. The first malformed anchor was rejected. The worker preserved the input, recorded the diff error, and stopped at the attempt limit.

**Interpretation:** the defensive patch behavior worked in a live model run. Clarifying the prompt did not ensure valid output on this one attempt. This is not a proof failure, a verified repair, or a reliable estimate of model success rate.

## Evidence

- [Input program](input-program.dfy) and [unchanged output](output-program.dfy)
- [Exact model prompt](prompt.json) and [response](response.json)
- [Token usage](token-usage.json) and [result summary](result.json)
- [Run configuration](run-config.yaml) and [environment / source revision / hashes](environment.json)
- [Scheduler log](scheduler.log)
- [Exact runner used](runner.py)

The [stored verifier stdout](inherited-verifier-stdout.txt) and [stderr](inherited-verifier-stderr.txt) are **inherited from extension-001**, not new verification results. The checkpoint's stored outcome `FAIL` must be interpreted with that distinction.

The run configuration and scheduler log replace the absolute repository prefix with `<CHECKOUT>/`. All other saved evidence is copied from the run. The checkpoint remains in the ignored Cannon output directory and is not committed.

## Execution and credentials

The assistant ran this directly through the authenticated SSH connection, inside the existing Cannon compute allocation. A mode-0600 temporary key handoff was consumed and deleted before the model request. The runner removed the key from its environment afterward; it is absent from the committed artifacts. Future model-running processes need credentials supplied again.

The runner captures only model prompt/content, usage, selected response metadata, and non-secret configuration/environment details. It does not serialize the SDK client or credentials. Its callback enforces at most one model invocation.

To reproduce with a fresh authorized request, run from the repository root with a trusted local checkpoint and a new private key handoff:

```bash
timeout 300 python experiments/repair-002/runner.py \
  --checkpoint outputs/extension-pilot-20261014-022417/agenda.pkl
```

This creates a new run directory and makes a paid request. A rerun is not necessary to inspect the saved evidence.

**Next proposed experiment:** a separately labeled full-program repair response using the same failed input, with explicit preservation checks. That would test whether avoiding this custom diff syntax helps; it has not been run.

[All experiments](../README.md).
