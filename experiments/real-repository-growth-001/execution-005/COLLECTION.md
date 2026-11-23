# Completed sequential growth cohort on real source

**Reviewed result: 2/4 planned lineages completed both additions.** Both are
Vest proof-library trajectories that reuse their actual accepted model parent.
Dafny-VMC produced no accepted first addition at the fixed resource limit.

Job **63033780** completed on November 23, 2026 in **1h10m26s**, on
nonpreemptible `shared` with **one CPU**, 8 GB, no requeue or restarts.
[Offline evidence replay](review-001.stdout) and the
[source, coverage, lineage and accounting review](collection-review-001.json)
passed. All **14,403 transferred files (435,280,127 bytes)** were checked against
the [transfer inventory](transfer-001.json). No model or verifier was called by
these reviews.

| Project | Accepted first additions / attempted | Accepted second additions / attempted | Complete two-addition lineages / planned |
| --- | ---: | ---: | ---: |
| Dafny-VMC | 0/2 | — (both children blocked) | **0/2** |
| Vest | 2/2 | 2/2 | **2/2** |
| Total | 2/4 | 2/2 | **2/4** |

**Four of six returned additions were accepted.** All six passed the parser and
protected-edit guard and received exactly one native invocation. There were
six unique request IDs, zero SDK retries, no ambiguous requests and no
unprocessed slots. Two child slots stayed unused because their parents failed.
The second-stage rate is conditional on an accepted parent.

## Every frozen slot

| Slot | Lineage | Addition | Outcome | Native seconds |
| --- | --- | --- | --- | ---: |
| 01 | Dafny 01 | MoveToFront | Bounded solver-resource failure; unaccepted | 90.58 |
| 02 | Vest 01 | Frame roundtrip | Accepted | 611.93 |
| 03 | Dafny 01 | PickPair | Blocked parent; no request | — |
| 04 | Vest 01 | Counted-batch roundtrip | Accepted | 584.46 |
| 05 | Vest 02 | Frame roundtrip | Accepted | 583.15 |
| 06 | Dafny 02 | MoveToFront | Bounded solver-resource failure; unaccepted | 76.87 |
| 07 | Vest 02 | Counted-batch roundtrip | Accepted | 588.79 |
| 08 | Dafny 02 | PickPair | Blocked parent; no request | — |

Both Vest children call `frame_roundtrip` once and recurse on the remaining
payloads. For example, the [slot-04 model proof](retrieved-001/model-001/slot-04/native/workspace/vest_dev/src/formats/growth_batch.rs)
contains:

```rust
frame_roundtrip(first, encode_batch(rest, tail));
batch_roundtrip(rest, tail);
```

Each child's frame file is byte-identical to its own accepted model parent,
not an analyst substitute. The two parent hashes and two child hashes are
distinct; all six new candidate source files are distinct within this cohort.
The host supplied the specifications and declarations; the model supplied
implementation/proof bodies. Vest growth is a specification/proof-library
extension, not executable parser generation. Observed API calls do not establish
that every valid proof must use the parent.

## Coverage, warnings and failures

Both Dafny checks retain all **267 upstream passes** and log the new target as
the sole failed unit: **268/268 required units present**, exit 4, zero ordinary
errors and one out-of-resource result. Each preserves the three inherited
warnings, with no added warnings or wall timeout. The complete resource
diagnostic, extended summary, raw CSV and source hashes agree.

Slot 01 is byte-identical to the earlier incorrect MoveToFront source
(`ef4dacc5fe562fba502477c827762d028df4ea14e5505344cce29fdfd2a09ef2`).
Its existing [analyst counterexample](../execution-004/diagnostics/counterexample-001.json)
therefore applies unchanged: `[0,1,2]`, `k=2` gives `[1,2,0]` instead of
`[2,0,1]`. This is a fresh request, not a transport retry or an independent
new counterexample analysis.

Slot 06 uses `Model.Swap(prev, 0, k)` after recursion, rather than
`Model.Swap(prev, k - 1, k)`. It is a different algorithm, and the preceding
counterexample does not refute it. **No mathematical counterexample has been
established for slot 06.** Its native outcome remains resource-limited and
unaccepted; no higher-limit rerun or rescore occurred.

Vest preserves all **5,410 upstream timed occurrences** in every check.
Each frame scope passes **5,411** occurrences across 5,301 tuple keys; each batch
scope passes **5,416** across 5,306 keys. Native crate-summary totals are separately
5,722 and 5,727, respectively; these measures are not interchangeable or counts
of new model-generated obligations. The six fixed frame spec definitions remain
explicitly unlogged. All four scopes have exit 0, the same five inherited
warnings, and no added warnings or timeout. Both accepted parent files remain
unchanged in their children, with complete required coverage.

## Accounting and archived evidence

Usage: **242,257 input + 1,744 output = 244,001 tokens**, zero reported cache
tokens. There were six native invocations, no retries and no native wall timeout.
Native elapsed time totals 2,535.78 seconds; Slurm records 2,520.43 CPU seconds
and 1,548,788 KiB peak batch RSS on one allocated CPU.

The [budget snapshot](../research-budget-20261123-004.json) records seven returned
requests across the two new cohorts: one in the earlier stopped cohort, six here.
Sixteen slots were allocated under the 100-call ceiling; **84 remain unallocated**.
The old seven unused slots and this cohort's two blocked slots remain closed.
All older budgets, ledgers and scores—including the real-source repair
**7/16**—remain unchanged.

The source/prompt and success rules stayed frozen. Execution-005 prospectively
contains fully audited Dafny solver-resource failures within their lineage;
it never promotes them. This is a separate cohort from
[execution-004](../execution-004/COLLECTION.md), not recovery of its ledger.

Full evidence: [run summary](retrieved-001/model-001/summary.json),
[all slot results](retrieved-001/model-001/results.json),
[canonical ledger and responses](retrieved-001/model-001/requests),
[accepted heads](retrieved-001/model-001/accepted-heads),
[native sources and raw logs](retrieved-001/model-001),
[accounting](retrieved-001/accounting.txt),
[approval](approval-receipt-001.json), [authorization](authorization.json),
[single submission](submissions/model.json).

Two pre-mutation archival failures are retained: the original read-only
inventory exceeded 90 seconds; the first correction then exceeded the local
SSH argument-size limit before launching its write phase. The final
[stdin transport correction](archive-recovery-002.py) reuses the exact frozen
fetch and all integrity, space and exclusive-write checks, with bounded
600-second SSH archival limits. Its [record](archive-recovery-002.json),
[first timeout](fetch-001.stderr) and [argument-limit error](archive-recovery-001.stderr)
are preserved. Only generated Cargo targets are excluded; all source workspaces
and native evidence are retained. Archival recovery made zero model/native calls
and changed no experimental outcome.

## Interpretation

This is concrete sequential model growth on a selected real Vest codebase,
with actual verified parent reuse. The current one-response setup did not
produce an accepted Dafny extension at these fixed limits. The next useful
diagnostic is to distinguish the second Dafny candidate's proof/resource issue
from the first candidate's established algorithmic error.

There are only two repetitions of one selected chain per project, with fixed
contracts and curated context. These observations do not establish general
repository-generation ability, a causal language/depth effect, held-out
generalization or readiness for fine-tuning.
