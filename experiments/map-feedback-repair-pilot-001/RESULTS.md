# Verifier-feedback repair comparison

**Detailed verifier feedback: 4/4 strict repairs. Failure notice only: 1/4.** All eight responses were admitted by the frozen output policy. Job **60215841** completed on `test` / `holy8a24101` in **2m20s**, with eight unique provider request IDs, zero SDK retries and no replacement requests. The original generation result stays **12/16**.

| Condition | Shared | Separate | Total |
|---|---:|---:|---:|
| Saved verifier diagnostics | 2/2 | 2/2 | **4/4** |
| Failure notice only | 1/2 | 0/2 | **1/4** |
| All repair trials | 3/4 | 2/4 | **5/8** |

Each strict success verified the whole nine-file workspace: 20 obligations, zero errors, zero warnings, exit 0. Five complete revisions were atomically promoted in isolated trial stores. The three failed attempts left their original HEADs unchanged. No original repository or experiment result was promoted or overwritten.

## What changed

All successful responses placed the restricted-map `Certify` call after facts establishing the restricted maps' key sets. The four feedback responses also supplied explicit subset/disjointness reasoning, sometimes using local aliases or a quantified proof. The one successful failure-notice response reordered the existing call and grouped a conjunction, adding no lemma calls.

The three failed controls (02, 03, 07) changed only Boolean parentheses and left `Certify` before its prerequisites. Dafny reported the same disjointness precondition failure in the affected helper bodies: one error for shared, two for separate. These were proof failures, with no parse, name-resolution, extraction or warning-only failures. The post-run [semantic review](semantic-review.json) and [complete editable-file diffs](source-diffs.patch) distinguish this interpretation from the frozen line-based edit classifier, which labels all non-pure-reordering edits `other_edit`.

| Trial | Parent | Sharing | Feedback | Strict result | Repair description |
|---|---|---|---|---|---|
| 01 | 04 | Shared | Diagnostics | Pass | Reorder, aliases, disjointness assertions |
| 02 | 08 | Separate | Notice | Fail | Parentheses only; premature certificate remains |
| 03 | 04 | Shared | Notice | Fail | Parentheses only; premature certificate remains |
| 04 | 08 | Separate | Diagnostics | Pass | Reorder and quantified disjointness proof |
| 05 | 11 | Separate | Diagnostics | Pass | Reorder and quantified disjointness proof |
| 06 | 09 | Shared | Notice | Pass | Reorder existing call and group conjunction |
| 07 | 11 | Separate | Notice | Fail | Parentheses only; premature certificate remains |
| 08 | 09 | Shared | Diagnostics | Pass | Same candidate workspace as 01 |

Parent numbers refer to `map-balanced-XX`; trial numbers refer to `map-repair-XX`. All four separate responses copied the same body into both editable helpers. Candidate workspaces 01/08 and 02/07 are respectively byte-identical, yielding six distinct candidate workspaces from eight fresh requests.

## Interpretation and limits

This is preliminary evidence that exact verifier diagnostics can help this one-round agent correct a concrete cross-module precondition-ordering failure. Both arms received the same failed source, contracts, declared dependency map, syntax policy and failure notice; only the detailed diagnostic block differed. No analyst-corrected proof or repair hint was sent. The observed difference is 75 percentage points in this small batch, without a claim of statistical significance or generality.

The four parent records contain only **two unique failing workspace contents**, drawn from one inspected development task. Repeated responses are not independent task instances. This is failure-selected repair, not fresh generation, held-out performance, a multi-round agent evaluation, or evidence of a general sharing/depth effect. Separate conditions have two editable bodies and permit copying. Reference call order does not establish a minimum proof-depth bound. One notice-only response succeeded, so detailed feedback was not necessary for every repair.

Named editable helpers passed 7/12 across these observations. Supplied clients verified locally in all runs, but only **10/16 client observations** were dependency-closed; clients relying on failed helper proofs receive no model success credit. Provider and CSV obligations are not counted as independent task trials.

The useful next evaluation is the same controlled feedback comparison across additional semantic failure modes and task instances, with frozen diagnostics and balanced structural conditions. No further model requests are approved by this run; all eight slots are exhausted.

## Evidence and reproducibility

- [Frozen proposal](../map-feedback-repair-plan-001/README.md), [runtime freeze](runtime-freeze.json), [explicit eight-call approval](authorization.json), and [single submission](submission.json).
- [Reviewed results](reviewed-results.json), [reproducible audit](review_results.py), [audit log](review-001.log), [raw model archive](model-001), and [587-file archive hashes](model-001-sha256.json).
- [Raw ledger](model-001/requests/ledger.json), exact frozen requests, provider responses/IDs, extraction decisions, candidate source, verifier stdout/stderr, byte-preserved declaration CSV and initial/accepted revision metadata are included per trial.
- [Slurm stdout](model-60215841.log), [stderr](model-60215841.err), [accounting](accounting-60215841.txt), [594-file transfer inventory](transfer-001.json).
- [18 local tests](runner-tests.log) and [18 Cannon fake-transport tests](environment-preflight.log), with no API or Dafny calls during those tests. The first offline preflight timeout is preserved in [preflight-attempt-001](preflight-attempt-001); runtime 002 changed environment startup/scratch location only, before any paid dispatch.
- Source review replayed every admitted output, checked **60 protected-file comparisons**, **12 body/contract boundaries**, all eight original trial revisions and all five promotions. [Preservation review](preservation-review.json) confirms all **812 original model files** and **165 analyst-diagnostic files** are unchanged.

Token use: **38,082 input + 7,348 output = 45,430 total**, with zero reported cache read/write tokens. No cost estimate is inferred. All eight requests completed; no calls were retried, resumed or reassigned.
