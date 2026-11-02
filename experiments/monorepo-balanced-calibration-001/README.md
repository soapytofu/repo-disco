# Balanced clarified-syntax calibration — frozen, not authorized to run

Prepared November 2, 2026. **Zero new model calls and zero new Dafny runs.**
The [difficulty review](DIFFICULTY_REVIEW.md) explains the interval-witness failure,
likely ceilings in the other families, and shared/separate workload limits.
Historical responses, scores and frozen protocols remain unchanged.

## Exact proposed scope

**32 fresh requests** = four development families × shallow/deep × shared/separate
× two samples. There are four semantic instances and 16 workspace configurations,
not 32 independent problems. Each family has eight requests, each structural cell
has eight across families, and each family/cell has two. Full source plus declared
file map is the fixed context policy. No feedback, retries, replacement samples,
quota reassignment or pooling with older runs.

The [frozen bundle](frozen-001/README.md) preserves every clarified prompt, seed,
guard, inference setting and dispatch position from statement-syntax-v1. Only
trial IDs change to `balanced-01` through `balanced-32`, with parent IDs retained.
[Trial order](frozen-001/trials.json) uses four cyclic Latin rows, interleaved
families and full reversal for sample two. This balances positions, not every
ordered transition. The midpoint repeats a variant in separate fresh contexts.

Settings remain the pinned Bedrock Claude Opus 4.5 configuration, temperature 1.0,
maxTokens 4096 and body-json-v2.1 guard. The aggregate output-token cap is 131,072;
inputs are additional. This is not an expected-use or dollar estimate.
[scope.json](frozen-001/scope.json) defines scoring, stopping rules, future
execution gates and the only files permitted in model messages.

Freeze SHA-256:
`df6771bf7ac6e81d2201811a84888ca01156eb6974bee4af85d6e2eb67e49c6f`.

## Reviewed evidence and validation

Nine offline test methods pass. The [audit](frozen-001/evidence-review.json)
checks 136 archived verifier outcomes, reconstructs all 16 previously verified
reference workspaces byte-for-byte, and replays all eight smoke responses to their
unchanged candidates. All 267 raw smoke archive files match their saved hashes.
The smoke score remains **8/8 admission, 7/8 verification**. These checks reuse
existing compute evidence; they do not launch a verifier or provider.

Tests also cover balance, fresh trial identities, exact parent inputs, immutable
clients/providers/helper contracts, tampered files/order, overwrite refusal,
invalid statement syntax, verification bypasses, source drift and the interval
counterexample. A finite arithmetic illustration checks 532 admissible endpoint
quadruples in [-3,3]: 196 invalidate the unconditional choice c, while the already
verified branching choice satisfies all 532. This is explanatory only, not a
universal proof, and never enters a model prompt.

The first test run incorrectly applied the empty-editable-seed splitter to the
immutable **nonempty** shared forwarding wrapper. The test now compares the known
template's lemma header; task/parser/prompt bytes were not changed. The
[initial failed log](offline-tests-001-failed.log) and [passing log](offline-tests.log)
are preserved. This was an audit-test bug, not a Dafny failure or model finding.
`review-manifest.json` pins the final code, documentation and both logs.

Reproduce offline from the repository root:

```sh
python3 -B experiments/monorepo-balanced-calibration-001/test_plan.py
```

`prepare.py` reproduces the freeze in a fresh destination and refuses to overwrite
an existing one. The tests compare deterministic reproduction with the saved bundle.

## Execution and decision gates

Preparation only: no live runner, authorization, job submission, SSH connection
or credential access was created. A later run needs explicit **32 new call**
authorization and a tested bounded runner/runtime freeze bound to this scope.
Use a new ledger/output directory, one nonpreemptible compute job, no Slurm requeue
and one SDK attempt per reserved request. Stop on ambiguous transport, persistence,
integrity or verifier-infrastructure failures.

Primary outcome is strict whole-workspace verification with protected contracts
and sources intact. Keep parser/schema/edit failures separate from proof, frontend
and infrastructure failures, and report planned/reserved/dispatched denominators.
Any protocol failure or family at 0/8 or 8/8 requires review before scaling;
near-ceiling or trivial-copying patterns can also make collection uninformative.
Inspect all accepted strategies and failures. The 192-call main corpus remains
deferred and needs separate review/authorization. This plan does not establish a
causal sharing/depth effect or held-out performance.
