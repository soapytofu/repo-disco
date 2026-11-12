# One-round verifier-feedback repair pilot — frozen proposal

**Prepared November 12, 2026. Proposed budget: EIGHT NEW model calls. No execution authorization or model calls.** This tests whether one repair round can correct the saved deep restriction/merge failures when supplied with the actual verifier diagnostics. A matched failure-notice control tests whether simply reconsidering the same proof is sufficient.

The [original pilot](../map-development-pilot-002/RESULTS.md) stays **12/16**. The [analyst reorder diagnostic](../map-order-diagnostic-002/RESULTS.md) already establishes that a valid repair exists; no corrected proof or analyst explanation enters these prompts.

## Budget and design

| Fixed failing workspace | Detailed verifier feedback | Failure notice only | Total new calls |
| --- | --- | --- | --- |
| Deep/shared | 2 fresh-context responses | 2 fresh-context responses | 4 |
| Deep/separate | 2 fresh-context responses | 2 fresh-context responses | 4 |
| Total | **4** | **4** | **8** |

There are four saved parent records (`map-balanced-04`, `08`, `09`, `11`) but only **two distinct failing workspace contents**. Each parent gets one request in each feedback condition; the duplicate shared/separate parents supply the second fresh-context sample, not extra independent problem instances. The frozen bundle has four unique payloads and eight trial IDs, `map-repair-01` through `08`.

Each trial gets **one model call and one guarded candidate verification**, with no subsequent repair round, feedback update, automatic retry, replacement call, resume or reassignment. Both conditions are collected even if an earlier trial succeeds. Ambiguous transport/save errors or verifier infrastructure failures stop the batch and preserve partial evidence; ordinary invalid output or proof failure consumes the slot. No unused historical calls are reused.

Settings remain Opus 4.5 (`global.anthropic.claude-opus-4-5-20251101-v1:0`), `us-east-1`, temperature 1.0, 4,096 output tokens per call: **32,768 maximum output tokens** across eight calls. Exact request sizes are [recorded](frozen-001/request-sizes.json); token counts and monetary cost are not yet measured. These eight calls are supplemental repair evaluation, outside the remaining matched-corpus collection. If every other original stage is retained, the prior attempted-request forecast of 154 becomes **162**, conditional on later approval and actual dispatch. That accounting is not authorization.

## What the model sees

Both conditions receive the same complete **failing** workspace, contracts, declared include/import map, permitted call/function signatures, clarified bounded syntax, requested editable filenames and statement that whole-workspace verification failed. Both return full replacement proof-body strings. Repairs may use any proof admitted by the unchanged grammar; they are not restricted to the analyst's reorder.

The detailed-feedback condition additionally receives the original verifier exit code, stdout and stderr. The only normalization removes the incidental `Results File: /tmp/.../TestResults/...csv` line; error locations, source excerpts, caret markers, related preconditions and verifier counts are unchanged. The control instead receives the fixed text “Detailed verifier diagnostics are not supplied for this attempt.” It is a **failure-notice control**, not a condition unaware that the proof failed. Feedback length differs by design and token usage must be reported.

[The prompt audit](frozen-001/prompt-review.json) checks that these conditions differ only inside the feedback block. The user prompt does not name the ordering failure, advise where to move calls, include analyst repairs or expose parent trial IDs. Repeated workspaces produce byte-identical payloads within a condition. No previous repair output or conversation is reused.

## Frozen order and provenance

| Position | Parent | Sharing | Feedback |
| --- | --- | --- | --- |
| 1 | map-balanced-04 | Shared | Verifier diagnostics |
| 2 | map-balanced-08 | Separate | Failure notice only |
| 3 | map-balanced-04 | Shared | Failure notice only |
| 4 | map-balanced-08 | Separate | Verifier diagnostics |
| 5 | map-balanced-11 | Separate | Verifier diagnostics |
| 6 | map-balanced-09 | Shared | Failure notice only |
| 7 | map-balanced-11 | Separate | Failure notice only |
| 8 | map-balanced-09 | Shared | Verifier diagnostics |

The second four-cell order reverses the first. Each sharing × feedback cell occupies symmetric positions summing to nine; each parent occurs in both conditions, with their order counterbalanced across the two samples. This is not a claim of perfect first-order transition balance or matched random seeds.

Freeze SHA-256:

`2b7f9bfb45bbe62081f999c831afee0520f84f48f74b78c7f2a154c729425867`

[freeze.json](frozen-001/freeze.json) binds 109 frozen files and 126 repository inputs, based on source commit `5fb3be95cfb41c55a0dfcbc8a9713039baccc5a6`. It pins the exact [requests](frozen-001/requests), [trial order](frozen-001/trials.json), [parent revisions](frozen-001/parents.json), original verification evidence, normalized feedback, unchanged output policies, settings and [target metrics](frozen-001/target-scope.json). These task and agent protocol artifacts are development material; no reserved families are used.

## Repair application and future agent integration

[protocol.py](protocol.py) is an offline adapter for replacing bodies in a fixed populated failing base. It checks the expected failing-source hashes and all protected bytes. The existing parser still receives its original trusted empty template to delimit bodies; the model receives the populated failing source. Guard-admitted replacements are reconstructed into a new candidate, never applied to the archived original. All four failing responses and all four already-verified analyst repairs replay byte-exactly through this adapter.

The future bounded runner must use a fresh isolated revision store for every trial, validate the frozen base and saved verifier evidence, dispatch the exact frozen payload once, apply the adapter, and verify all files on a compute node with pinned Dafny 4.11.0 / Z3 4.12.1 and a 60-second candidate timeout. Only strict exit-zero, zero-error, zero-warning success may promote a complete new revision. Failed attempts leave the trial's initial HEAD unchanged; the original experiment is never promoted or edited. The prior source-bound base diagnostics can be reused; they are not new verifier observations.

The existing repository agent has immutable-revision/promotion machinery, but its generic prompt formatter and multi-attempt defaults are **not** this protocol. A future adapter must bind the fixed request bytes, one-call limit, feedback masking and source hashes, and pass fake-transport/verification tests for success, failure, contract rejection, ambiguous stop and stale promotion before execution. This planning work creates no live dispatcher or new agent execution result.

## Evaluation

Primary outcome: guard-admitted whole-workspace strict verification, with all includes, at the one-call repair budget. Report planned, dispatched, returned, extracted, admitted and strictly repaired counts for every sharing × feedback cell. Undispatched or ambiguous requests are infrastructure/missing outcomes, not mathematical proof failures. Preserve envelope, policy, frontend, proof, warning, timeout and transport categories separately.

Secondary outcomes use the unchanged named-helper and dependency-closed client metrics. A supplied client that verifies locally against an unproved helper contract receives no model-repair credit. Log exact sources, diffs, verifier stdout/stderr/CSV, request IDs, retry counts, token usage and per-trial original/accepted revision hashes. Describe whether an accepted repair is an exact call reorder or makes other edits, without asserting minimality. All raw evidence, including failures, must be published separately.

Report feedback versus failure-notice repair counts on these same fixed inputs. If both conditions succeed, the pilot demonstrates repair feasibility without establishing added benefit from detailed feedback. If feedback does better, report that descriptive contrast for this selected failure; if both fail, retain those outcomes. Do not tune or replace failed trials mid-run.

This is **one inspected map task, one selected failure mechanism, two workspace contents and two responses per cell**. Shared/separate output workload differs, and separate bodies can be copied. There is no held-out, broad causal-sharing, necessary-depth, general feedback-effect, long-horizon-agent or statistical-significance claim. The original generation score stays 12/16 regardless of repair outcomes.

## Offline validation and next gate

[Eight offline tests](offline-tests-001.log) pass: exact reproducible freeze with network/process calls blocked; eight-call and one-call-per-trial caps; counterbalanced order; exact feedback normalization; identical non-feedback context; populated-base and verified-repair reconstruction; stale/contract-changing input rejection; fresh IDs and duplicate-workspace accounting; target-credit rules; and refusal to overwrite a freeze. All **812 original model-archive files** remain unchanged. This uses existing verifier evidence and runs no new Dafny job.

```sh
python3 -B -m unittest discover -s experiments/map-feedback-repair-plan-001 -p test_plan.py -v
```

Next gate: explicit approval of these eight new calls, followed by the separately tested and hash-bound bounded runner. No key handoff or reconnection is needed for this completed planning step. No execution or paid budget is inferred from this document.
