# Eight-call syntax smoke results

Requests: 8/8 reserved, 8 responses, 8 unique request IDs. Zero SDK retries: True.
Parser/guard admission: **8/8**. Strict whole-workspace verification: **7/8**.
Predeclared syntax-readiness gate: **PASS**. No automatic expansion.

| Family | Deep/shared | Deep/separate |
| --- | --- | --- |
| conditional_preconditions | VERIFIED | VERIFIED |
| interval_witness | PROOF_FAILURE | VERIFIED |
| map_transfer | VERIFIED | VERIFIED |
| sequence_offset | VERIFIED | VERIFIED |

## Interpretation

Deep-only development syntax smoke test, one sample per configuration. No depth, sharing, held-out or population effect can be inferred; shared/separate output workload differs. No pooling with a future fresh 32-trial evaluation.

A guard pass establishes syntax and protected assembly, not a proof. Proof failures, frontend errors, timeouts and infrastructure failures are distinct outcomes. A syntax-gate pass is only a small development check, not a reliable error-rate estimate. Any larger run needs review and a new explicit budget. Previous scores remain unchanged.

Token usage: `{"cacheReadInputTokens": 0, "cacheWriteInputTokens": 0, "inputTokens": 24090, "outputTokens": 1614, "totalTokens": 25704}`.

Full messages, responses, ledger, extraction decisions, admitted source, hashes and raw verifier logs are in model-001. results-review.json and model-001-sha256.json bind this review to the archive.

## Failure inspection and completion

Job 56210087 completed on nonpreemptible test in **2m04s**, following the third
in-place partition adjustment. It retained the original job ID, eight-call cap,
resources and no-requeue policy. No duplicate job, model retry, feedback call or
replacement sample was used. The full eight-call budget is exhausted.

The sole failure is smoke-04, deep/shared interval witness. It calls
`S1.Left(a,b,c)` without proving the required `a <= c <= b`, then uses the same
unconditional witness in the remaining chain. The task's overlap assumptions do
not ensure `a <= c`. For example, a=2, b=5, c=0, d=4 satisfies all task
preconditions while witness c=0 is outside [2,5]. This is a manual explanation of
the saved diagnostic, not a repaired/reverified trial. The separate sample
branches on `a <= c` and selects c or a; its original submitted proof verified.

completion-review.json records the source/diagnostic inspection. No contracts or
original responses were changed. All eight trials meet the predeclared syntax
gate, but a one-sample-per-configuration smoke test cannot establish reliability
or a causal effect of sharing, depth or the prompt change. A future 32-call run
is not authorized automatically; review proof difficulty and the witness failure
before proposing another paid evaluation.
