# Eight proposed calls for guarded clamp monotonicity

Prepared November 4, 2026. Weeks 5–6 development calibration. **Eight calls proposed, zero dispatched.** The study asks whether a model can prove that clamping preserves the order of two integers when it must satisfy the provider preconditions in each module. Earlier conditional tasks yielded eight strict successes in eight requests. This task has four successful reference proofs, 24 intended proof failures and four intended name-resolution failures. [Earlier model results](../monorepo-reasoning-calibration-pilot-001/RESULTS.md) · [Verifier controls](../conditional-monotonicity-001/RESULTS.md)

## Design

One semantic task, four workspace variants, two fresh samples per variant. The two samples for a cell use identical request bytes. This lets us observe within-prompt variability and keeps the prompt free of trial, condition-order and previous-response metadata.

| Position within block | Block 1 | Block 2 |
| --- | --- | --- |
| 1 | Shallow, shared | Deep, separate |
| 2 | Deep, separate | Shallow, shared |
| 3 | Shallow, separate | Deep, shared |
| 4 | Deep, shared | Shallow, separate |

Dispatch would finish block 1 before block 2. Each block visits all four cells. Across blocks, both factors reverse at each position. Identical requests never occur consecutively. This balances the individual factors by position while leaving some cell-by-position and sequential effects unbalanced. [Eight trial slots and request hashes](frozen-001/trials.json) · [Four exact Bedrock payloads](frozen-001/requests/)

Every request contains its nine-file empty workspace, the include/import map derived from those files, the task-specific call signatures and the same output instructions. Both clients and all contracts are fixed. Reference bodies, negative controls, prior answers and reviewer annotations stay outside the payload. Reference depth counts **one** contract-application stage in shallow and **two** in deep. In deep, two facts can be obtained independently before an assembly call. In shared, HelperB forwards to one editable body. In separate, two editable bodies may contain the same proof. Two samples per cell inform task selection. The study cannot isolate the effect of sharing from the extra output workload or establish general model performance.

## Proposed execution and scoring

- Use the pinned Bedrock Claude Opus 4.5 ID in us-east-1, temperature 1.0 and up to 4,096 output tokens per request. Eight requests allow up to 32,768 output tokens plus input. Each reservation permits one fresh conversation and one SDK attempt. Slots cannot be reassigned. [Machine-readable plan](plan.json)
- A future run requires separate approval and a tested bounded runner tied to the freeze digest. Require durable reservations before dispatch, a deadline checked before every call, no automatic restarts or retries, and a single nonpreemptible compute job with requeue disabled. Stop on ambiguous transport, missing evidence, persistence failure, hash drift or verifier timeout/launch failure. A completed incorrect or malformed answer consumes its slot.
- Score success only if the v4 guard accepts the exact returned body strings, all protected bytes match, and the full workspace verifies with the pinned Dafny/Z3 toolchain. Use `dafny verify --verify-included-files All.dfy`, 60 seconds, strict exit zero. Record per cell how many of the two planned requests were dispatched, returned, admitted and verified. Keep unattempted slots visible if execution stops.
- Archive the ledger, request IDs, responses, token use, latency, guard decisions, sources, source hashes, verifier exit codes and raw diagnostics. Separate formatting, truncation, precondition, assertion/postcondition, termination, frontend, warning-only and infrastructure outcomes. Record when the two bodies in a separate response are identical. Review each failure against the guarded source before interpreting it.
- If 8/8 verify, keep this instance as an easy development anchor and prioritize a different reasoning obligation. If all fail, review the failure mechanisms before retaining the task. For mixed results, check whether failures expose boundary selection, missing facts or output syntax. A guard rejection or warning-only exit gets a separate diagnostic. The original score stands. Main-corpus selection and its proposed 192 calls remain a separate decision.

## Offline validation

From this directory run `python3 -B prepare.py`. It reconstructs all request bytes and the manifest in a temporary directory, checks the order, seed hashes and allowed APIs, and replays each reference against its archived strict verification record. [Frozen file and dependency hashes](frozen-001/freeze.json) · [Validation log](offline-checks.log) · [Validated v4 guard](../monorepo-policy-integration-001/README.md)
