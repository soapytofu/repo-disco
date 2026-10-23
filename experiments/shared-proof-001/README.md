# shared-proof-001: two clients depending on one lemma

Verifier-only task, October 23, 2026. No model calls requested or made. **All 16 checks matched expectations.** Job 54811081 completed on Cannon serial_requeue with exit 0:0 and automatic requeue disabled. Dafny 4.11.0 and Z3 4.12.1 ran on compute node holy7c02504. [Check log](VERIFICATION.md) · [Raw evidence](verification-001/) · [Summary](verification-001/summary.json).

One repository contains a provider, two client modules, and an aggregate include entry point. The provider exposes an opaque sequence-size function and the public contract of `SequenceFacts.LengthConcat`. Its definition stays opaque to the clients' verifier. Each reference proof calls that same lemma once:

- `ClientA.AppendPositive`: a positive-length prefix implies positive length after concatenation.
- `ClientB.AppendPreservesLowerBound`: a suffix length at least `k` implies concatenation length at least `k`.

These are two distinct client targets in the same repository, not repeated trials of one target. The canonical provider definition ID is shared across both usage edges in `task.json`. The graph is shallow and the proofs are intentionally elementary: this fixture tests the representation and measurement of shared-proof dependence before testing model difficulty.

## Deterministic controls

| Variant | Client A | Client B | Whole repository |
| --- | --- | --- | --- |
| Reference | Pass | Pass | Pass |
| Remove A's call | Proof failure | Pass | Proof failure |
| Remove B's call | Pass | Proof failure | Proof failure |
| Remove both calls | Proof failure | Proof failure | Proof failure |
| Weaken shared lemma guarantee to `true` | Proof failure | Proof failure | Proof failure |

An additional provider-only check must pass after weakening its guarantee, distinguishing loss of usable proof information from a broken provider or parse error. The lemma name remains present, so dependency is tested without introducing an unknown-name error. Client source, contracts, and call sites are unchanged in this ablation. All 16 checks use `dafny verify --verify-included-files` on compute nodes. Exit 4 with proof errors is required for negative controls; parse errors and timeouts do not count as expected failures.

`test_fixtures.py` checks that each mutation changes only the intended bytes and that the control matrix isolates clients correctly. Two offline tests passed before evidence review. `run_verification.py` snapshots inputs, checks, versions, commands, hashes, timing, and full diagnostics into a fresh output directory. It requires a Slurm compute-node environment. No SDK or credential loader is used.

For a later repair task, the `missing_both` variant can be the starting state; permitted changes would be confined to client proof bodies while preserving provider source and all client contracts. No model experiment is part of this task. A matched unshared-helper control and harder proof chains remain separate proposed extensions.

## Measured shared dependence

Both reference clients verify, individually and together (the aggregate reports four verified obligations, not four client targets). Removing either client call leaves the other client passing. Weakening the shared lemma guarantee produces a postcondition failure in each client, while the weakened provider itself verifies. All negative outcomes are proof failures, not parse or missing-name errors. Thus one provider lemma supports two distinct client targets, and its guarantee is needed by both archived reference proofs under the current exports and verifier configuration. This does not claim that every conceivable proof needs that lemma, or that an LLM has demonstrated reuse.

Post-run review matched every compute snapshot to the local fixtures, checked all recorded source hashes and exit codes, confirmed empty verifier stderr, and confirmed postcondition diagnostics for every negative control. Raw evidence includes all failures. Two offline mutation-isolation tests passed.
