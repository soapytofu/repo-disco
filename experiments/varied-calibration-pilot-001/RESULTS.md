# Varied calibration results — November 10, 2026

**27/32 strict whole-repository successes.** All 32 approved requests completed
with distinct provider IDs and zero SDK retries; the budget is exhausted.
There were four proof failures and one proof-body policy rejection. All 32 JSON
envelopes were extracted; 31 bodies were admitted. No admitted candidate produced
a parse/name error, warning or timeout. No responses were repaired or rescored.

Job **59517240** completed on nonpreemptible `test` in **6 minutes 14 seconds**.
Usage: **106,344 input + 12,850 output = 119,194 tokens**; no cache tokens reported.
These are usage counts, not a dollar-cost estimate. Model/settings, frozen order
and exact request hashes are in the [pilot README](README.md) and
[results-review.json](results-review.json).

## Results by task and structural cell

| Task | Shallow shared | Shallow separate | Deep shared | Deep separate | Total |
| --- | ---: | ---: | ---: | ---: | ---: |
| Bounded allocation | 2/2 | 2/2 | 2/2 | 2/2 | 8/8 |
| Map swap | 2/2 | 1/2 | 0/2 | 0/2 | 3/8 |
| Clamp distance | 2/2 | 2/2 | 2/2 | 2/2 | 8/8 |
| Prefix splitting | 2/2 | 2/2 | 2/2 | 2/2 | 8/8 |

Each cell contains two fresh-context responses to the same exact request. This
is four semantic development instances and 16 workspaces, not 32 distinct tasks.
All family and cell positions followed the frozen two-replicate order.

## Failures and policy limits

- **Deep map swaps, trials 05, 15, 24 and 30:** Dafny exit 4, failure of the
  `forall` statement's postcondition. All four responses use the same helper-body
  text, duplicated across the separate helpers. The proof calls `SwapAt` on the
  original and once-swapped maps only at the current query key `q`. Inspection of
  the visible contracts indicates missing original-map observations at the other
  swapped key: for `q == k`, the outer result depends on the first swap's value at
  `j`, and conversely for `q == j`. The verified reference supplies both key
  instantiations. This is a source-based diagnosis, not a newly verified repair
  or a minimality claim. Full original diagnostics remain in
  [trial 05](model-001/varied-cal-05/verification.json),
  [15](model-001/varied-cal-15/verification.json),
  [24](model-001/varied-cal-24/verification.json) and
  [30](model-001/varied-cal-30/verification.json).
- **Shallow separate map swap, trial 27:** valid extracted JSON, rejected by the
  frozen body guard with `Unknown expression name`. The response uses
  `assert forall q :: ...;`; the admitted grammar supports the statement form
  `forall q | ... ensures ... { ... }`, not quantified expressions inside
  assertions. It was never sent to Dafny, so its mathematical validity is
  unmeasured. See the [response](model-001/varied-cal-27/response.json) and
  [decision](model-001/varied-cal-27/extraction.json). The primary result remains
  a policy rejection; changing the parser would require a separate diagnostic.

Allocation responses choose feasible witnesses by case splits or clamping an
endpoint, clamp-distance responses select the appropriate observations for both
inputs, and prefix-splitting responses use a decreasing recursive call. These
27 accepted candidates preserve the original contracts and all provider/client
code. There is no evidence of weakened specifications.

All **16 separate-condition JSON responses contain identical HelperA/HelperB
body strings**, including the rejected response. This measures output copying;
it does not establish separate independent proof synthesis or a sharing benefit.

## Integrity and full evidence

- [results-review.json](results-review.json) replays extraction and body guards,
  and checks exact requests/order, provider IDs, zero retries, usage metadata,
  candidate hashes, toolchain, verifier commands and accepted records.
- [source-review.json](source-review.json) records **233 whole protected-file
  checks and 46 editable-body boundary checks** across 31 admitted candidates.
  All signatures, contracts, imports, exports, decreases clauses, providers and
  clients are unchanged. Twenty-one distinct admitted body strings were reviewed.
- [transfer-001.json](transfer-001.json) records all **1,219 transferred files**.
  Every transferred hash was rechecked after review. The [model archive hash
  inventory](model-001-sha256.json) pins the complete original model archive.
- [model-001](model-001) contains exact frozen requests, seeds, runtime code,
  authorization, environment, durable reservations, full provider responses,
  extraction decisions, guarded candidates, verification stdout/stderr and
  accepted records. No credentials are included.
- [stdout](model-59517240.log), [stderr](model-59517240.err),
  [accounting](accounting-59517240.txt), [submission](submission.json),
  [exclusive lock](submission.lock) and [raw scheduler metadata](raw-scheduler)
  preserve execution provenance. Both proposal and runtime freezes are unchanged.

No model calls, proof edits or verifier reruns were made during this review.
The sixteen offline runner tests ran in four concurrent groups; live requests
and their verification were sequential, preserving the approved dispatch order.

## Interpretation and next gate

Three C1 instances reached 8/8; map swap exposed a repeatable deep-contract
instantiation failure plus one separate policy mismatch. This is useful
calibration evidence, not a family-wide causal depth/sharing result. Two samples
per cell and one instance per family are insufficient for that conclusion, and
separate mode has twice the editable bodies with copying allowed. The reference
path annotations do not prove necessary or minimum reasoning depth.

Before any broader paid collection, review the quantified-expression policy
mismatch offline, confirm the map diagnosis in a separately logged verifier-only
diagnostic if desired, and implement the planned distinct M1/M2 development
instances rather than extrapolating difficulty from these C1 results. Keep the
reserved tree/transition families out of tuning and audit their lineage before
primary evaluation. The proposed later 64/48-call stages are not authorized.

## Individual observations

| Trial | Workspace | Outcome |
| --- | --- | --- |
| [varied-cal-01](model-001/varied-cal-01/result.json) | bounded_allocation-shallow-shared | VERIFIED |
| [varied-cal-02](model-001/varied-cal-02/result.json) | map_swap-shallow-separate | VERIFIED |
| [varied-cal-03](model-001/varied-cal-03/result.json) | clamp_distance-deep-shared | VERIFIED |
| [varied-cal-04](model-001/varied-cal-04/result.json) | prefix_split-deep-separate | VERIFIED |
| [varied-cal-05](model-001/varied-cal-05/result.json) | map_swap-deep-shared | PROOF_FAILURE |
| [varied-cal-06](model-001/varied-cal-06/result.json) | bounded_allocation-deep-separate | VERIFIED |
| [varied-cal-07](model-001/varied-cal-07/result.json) | prefix_split-shallow-shared | VERIFIED |
| [varied-cal-08](model-001/varied-cal-08/result.json) | clamp_distance-shallow-separate | VERIFIED |
| [varied-cal-09](model-001/varied-cal-09/result.json) | clamp_distance-deep-separate | VERIFIED |
| [varied-cal-10](model-001/varied-cal-10/result.json) | prefix_split-deep-shared | VERIFIED |
| [varied-cal-11](model-001/varied-cal-11/result.json) | bounded_allocation-shallow-separate | VERIFIED |
| [varied-cal-12](model-001/varied-cal-12/result.json) | map_swap-shallow-shared | VERIFIED |
| [varied-cal-13](model-001/varied-cal-13/result.json) | prefix_split-shallow-separate | VERIFIED |
| [varied-cal-14](model-001/varied-cal-14/result.json) | clamp_distance-shallow-shared | VERIFIED |
| [varied-cal-15](model-001/varied-cal-15/result.json) | map_swap-deep-separate | PROOF_FAILURE |
| [varied-cal-16](model-001/varied-cal-16/result.json) | bounded_allocation-deep-shared | VERIFIED |
| [varied-cal-17](model-001/varied-cal-17/result.json) | map_swap-shallow-shared | VERIFIED |
| [varied-cal-18](model-001/varied-cal-18/result.json) | bounded_allocation-shallow-separate | VERIFIED |
| [varied-cal-19](model-001/varied-cal-19/result.json) | prefix_split-deep-shared | VERIFIED |
| [varied-cal-20](model-001/varied-cal-20/result.json) | clamp_distance-deep-separate | VERIFIED |
| [varied-cal-21](model-001/varied-cal-21/result.json) | clamp_distance-shallow-separate | VERIFIED |
| [varied-cal-22](model-001/varied-cal-22/result.json) | prefix_split-shallow-shared | VERIFIED |
| [varied-cal-23](model-001/varied-cal-23/result.json) | bounded_allocation-deep-separate | VERIFIED |
| [varied-cal-24](model-001/varied-cal-24/result.json) | map_swap-deep-shared | PROOF_FAILURE |
| [varied-cal-25](model-001/varied-cal-25/result.json) | prefix_split-deep-separate | VERIFIED |
| [varied-cal-26](model-001/varied-cal-26/result.json) | clamp_distance-deep-shared | VERIFIED |
| [varied-cal-27](model-001/varied-cal-27/result.json) | map_swap-shallow-separate | OUTPUT_REJECTED |
| [varied-cal-28](model-001/varied-cal-28/result.json) | bounded_allocation-shallow-shared | VERIFIED |
| [varied-cal-29](model-001/varied-cal-29/result.json) | bounded_allocation-deep-shared | VERIFIED |
| [varied-cal-30](model-001/varied-cal-30/result.json) | map_swap-deep-separate | PROOF_FAILURE |
| [varied-cal-31](model-001/varied-cal-31/result.json) | clamp_distance-shallow-shared | VERIFIED |
| [varied-cal-32](model-001/varied-cal-32/result.json) | prefix_split-shallow-separate | VERIFIED |
