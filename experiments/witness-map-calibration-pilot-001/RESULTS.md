# Sixteen-call witness/map calibration results

Completed November 6, 2026 Eastern (Cannon job 58541149, 2026-11-07 UTC). **16/16 requests completed, 16 unique request IDs, zero SDK retries, 64,085 tokens**: 52,480 input and 11,605 output. Runtime was 3m52s on non-preemptible `test`. The approved budget is exhausted; no request was retried or reassigned.

**Primary strict score: 8/16.** Every response passed single-object extraction and the bounded proof guard. Seven failed proof obligations; one verified all obligations but exited with trigger warnings, which remains a non-pass under the frozen strict exit-zero policy.

| Semantic instance | Interface | Sharing | Strict passes | Other outcomes |
| --- | --- | --- | ---: | --- |
| Separated witnesses | Shallow | Shared | 0/2 | 2 precondition failures |
| Separated witnesses | Shallow | Separate | 0/2 | 2 precondition failures |
| Separated witnesses | Deep | Shared | 2/2 | — |
| Separated witnesses | Deep | Separate | 0/2 | 2 precondition failures |
| Overwrite/delete | Shallow | Shared | 2/2 | — |
| Overwrite/delete | Shallow | Separate | 1/2 | 1 warning-only exit |
| Overwrite/delete | Deep | Shared | 1/2 | 1 pointwise proof failure |
| Overwrite/delete | Deep | Separate | 2/2 | — |

These are **two semantic instances**, eight workspace variants and two samples per variant. Family totals are witness 2/8 and map 6/8; do not treat eight cells as eight independent research tasks or pool historical studies into this score.

## What failed

Six witness responses (01, 03, 05, 10, 12, 14) chose `u = a`, `v = a + gap` unconditionally. The contract guarantees sufficient intersection width but does not imply `c <= a`. For example, `a=0, b=2, c=1, d=2, gap=1` satisfies every precondition, yet `u=0` is outside the second interval. Valid witnesses are `u=1, v=2`. Shallow calls fail `Direct`'s membership requirement; deep calls fail `Right`'s prerequisite. The two successful deep/shared answers explicitly split on `c <= a`, choosing the larger lower endpoint. This is one repeated endpoint-selection failure mechanism, not six distinct mathematical discoveries.

Map response 06 omits the inner-update value observation connecting `Put(m,k,x)[q]` to `m[q]` for surviving keys. Both pointwise `forall` postconditions fail. Response 13 to the same frozen prompt includes the relevant `PutAt(m,k,x,q)` instances and verifies. This agrees with the fixture's targeted missing-inner control; it is an observed omission, not a proof-minimality result.

Map response 15 verifies **16 obligations with zero proof errors**, but four missing-trigger warnings arise from concrete map comprehensions in the two helper bodies. Exit code is 2 because warnings are disallowed. This is a verifier-policy/representation issue, separately classified from the seven proof failures. The response was not rewritten or accepted, and no warning flag was relaxed.

## Extraction and preservation

Five responses were plain JSON, three were whole-response JSON fences, and eight included surrounding prose/fences. All 16 contained one accepted payload under the frozen policy. Exact payload spans and hashes are archived; no JSON or proof-body repair was performed. The eight prose-prefixed responses reached verification prospectively, unlike the older strict-envelope study. That observation is not a retroactive rescore of any earlier pilot.

The offline review reconstructed all 16 candidates from their original response strings, checked **120 immutable file comparisons and 24 protected helper-body boundaries**, and confirmed the exact verifier source hashes. All accepted workspaces preserve the supplied contracts, clients, providers and allowed export views. All eight separate-condition responses supplied identical A/B body strings; duplicated output is not evidence of independent proof discovery.

## Interpretation and next gate

The new tasks produce genuine mathematical failures after successful output admission, so they are useful development candidates. The observed witness deep/shared advantage is only two samples in one instance; prompt/interface structure, output workload and copied proofs prevent a general causal depth/sharing claim. More calls on these same two instances alone would not create semantic diversity or held-out evidence.

Two [separate analyst diagnostics](../witness-map-diagnostic-001/README.md) subsequently passed with 16 verified obligations, zero errors and no warnings each. Adding the omitted inner-update observation resolves trial 06's failure; substituting existing opaque expressions for the four concrete comprehensions removes trial 15's warnings without adding lemma calls. These are zero-model-call follow-ups, not model repairs or a rescore: **the primary score remains 8/16**. They establish sufficient edits, not minimality or necessary proof depth.

Before any new paid collection, use these diagnostics and the witness counterexample to define the failure mechanisms. Then select additional independently specified instances and a genuinely unseen family split. Do not expand the main corpus by renaming these tasks or infer new spending authorization from this completed budget.

## Full evidence

- [Machine-reviewed counts, cells and request IDs](results-review.json)
- [Exact-source and diagnostic audit](source-diagnostic-review.json), [reproducible audit code](analyze_results.py)
- [Complete original archive](model-001/) including frozen inputs/runtime, all requests/responses, candidates, stdout/stderr and accepted records
- [Original request ledger](model-001/requests/ledger.json), [archive hashes](model-001-sha256.json), [transfer inventory](transfer-001.json)
- [Scheduler stdout](model-58541149.log), [stderr](model-58541149.err), [accounting](accounting-58541149.txt)
- [Frozen proposal](../witness-map-calibration-001/README.md), [preflight controls and limitations](../witness-map-strengthening-001/README.md)

The review commands are offline and do not call a model or Dafny:

```sh
python3 -B experiments/witness-map-calibration-pilot-001/review_results.py
python3 -B experiments/witness-map-calibration-pilot-001/analyze_results.py
```
