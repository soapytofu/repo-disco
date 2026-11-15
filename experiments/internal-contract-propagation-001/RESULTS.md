# Internal API migrations: verified caller propagation

Verifier-only job **60723362** completed on the nonpreemptible `test` partition
in 43 seconds, with no requeue, duplicate submission or model calls. All **18
planned controls** produced their expected whole-workspace and named-target
outcomes: six strict successes and twelve ordinary proof failures. There were no
parse/name-resolution errors, timeouts or warnings.

The two tasks deliberately change an internal API while preserving the public
client signature, preconditions and postconditions. In both tasks, the chosen
helper-only and caller-only migrations leave `Helper.Transfer` verified while
`Client.Target` fails. The coordinated migration and its alternative both pass.
This is measured caller-proof propagation, not an inference from a declared
dependency graph.

| Variant, applied once to each task | Checks | Helper | Client | Whole workspace |
| --- | ---: | --- | --- | --- |
| Original reference | 2 | Pass | Pass | Strict pass |
| Paired migration | 2 | Pass | Pass | Strict pass |
| Alternative paired implementation | 2 | Pass | Pass | Strict pass |
| Helper-only migration | 2 | Pass | Fail | Proof failure |
| Caller-only adaptation | 2 | Pass | Fail | Proof failure |
| Unguarded call to new API | 2 | Pass | Fail | Proof failure |
| Missing return-value transformation | 2 | Pass | Fail | Proof failure |
| Contract-only migration | 2 | Fail | Pass under assumed contract | Proof failure |
| Incorrect new helper implementation | 2 | Fail | Pass under assumed contract | Proof failure |

A passing client unit when its helper implementation fails does **not** make the
repository correct: modular verification reasons from the helper's declared
contract, which the failing helper has not established. Whole-workspace success
requires both obligations.

## What the two migrations test

- **Capped endpoint:** the original helper returns an absolute endpoint. The new
  helper requires `start <= cap` and returns a relative advance. The caller must
  handle the excluded domain and add the origin back. Helper-only migration
  fails both a call precondition and the public postcondition; caller-only
  adaptation fails the postcondition.
- **Extracted map entry:** the original helper returns a remainder map. The new
  helper requires the key to be present and returns the removed entry instead.
  The caller must handle absence and reconstruct the remainder. Helper-only
  migration fails its call precondition and public postcondition; caller-only
  adaptation fails the explicit assertion that the returned patch is the entry.

The exact examples and prospective expectations remain in the immutable
[design README](README.md), [tasks](tasks.json) and [cases](cases.json).

## Evidence and review history

The [full transfer inventory](transfer-001.json) contains 171 exact files,
including all sources, per-case JSON, raw stdout/stderr/CSV, scheduler output and
[terminal accounting](accounting-60723362.txt). The verifier's
[raw archive](verification-001/) contains 165 files. Review checks all 72 source
files, 18 public-contract prefixes, 18 immutable-kernel comparisons and 36 body
boundaries. No fixture, contract, runtime pin or raw result changed after dispatch.

The first [named review](reviews/review-001/results-review.json) correctly accepted
the nine map cases but flagged all nine arithmetic cases because it required a
logger entry for every function. The total `Kernel.Endpoint` definition emits no
separate verification unit in this run. Its source is fixed; both arithmetic
method correctness units are present. The original reviewer, seven synthetic
tests and unsuccessful review are preserved.

The separately versioned [reviewer](review_v2.py) binds that single unlogged
definition to its exact source hash and distinguishes it from verified provider
units. It still requires both method correctness units and all three map-provider
well-formedness units. The [second review](reviews/review-002/results-review.json)
uses the same original archive; it does not rerun Dafny or change expected
mathematical outcomes. Missing, duplicate or malformed target evidence cannot
count as a pass. Local preparation failures and the precompute diagnostic-category
correction remain archived separately.

Six additional offline tests pass for the versioned correction, including absent
map-provider/target rejection and refusal to hide an observed failed Endpoint
unit. The final report records 27 passed map-provider unit observations and nine
explicitly unlogged Endpoint observations. Neither category is an independent
model trial.

## Scope of the result

These are two analyst-constructed development migrations. The single-sided
controls establish insufficiency of those particular patches, not that every
correct solution must edit two files. Keeping the original API preserves the
original behavior, and a caller may have other implementations. The target
internal semantics are explicit migration goals, not bugs found in an initially
incorrect program.

No model repair capability, causal depth/sharing effect, repair minimality or
held-out performance was measured here. The earlier model scores and freezes
are unchanged. A future migration experiment needs a separate edit protocol
that permits the specified internal API change while protecting public contracts;
the existing body-only model runner cannot be silently reused.
