# Initial growth reference checks

Status: November 18, 2026. Both initial jobs are complete. These are analyst reference checks with
zero model calls. They are not generated-repository results.

| Project | Job | Native observation | Next gate |
| --- | --- | --- | --- |
| Dafny-VMC | 61747428 | Completed; exit 2, module-resolution cycle, zero logged proof units | Preserve this failure and verify a separately versioned namespace correction |
| Vest | 61747454 | Exit 0; complete original inventory plus six new timed entries, zero errors, five exact inherited warnings | Reference source/inventory gate passed; negative controls still pending |

Both jobs were submitted once to live-confirmed nonpreemptible `test`, with one
CPU each and no requeue. The remote fake-process/import preflight passed all 31
tests before submission. No remaining control is released by either job's
scheduler completion status.

## Dafny reference: namespace failure before proof checking

The worker job completed in 28 seconds. Its native command took 10.197 seconds
and exited 2. The compiler reported:

```text
module FisherYates -> module GrowthPick -> import Shift -> module FisherYates
```

The two additions were children of the existing `FisherYates` namespace. The
qualified sibling import induced a cycle because a parent module implicitly
depends on its children. This is a frontend failure, not a mathematical
counterexample or resource failure. No verification units were logged; all 267
required old units and both provisional new targets are absent. Whole-scope
acceptance is therefore false.

All 23 transferred artifacts are retained, including exact overlays, source
audits, native stdout/stderr and CSV, resource measurements, accounting and
submission records. `review.py dafny-vmc` replayed their bindings successfully;
that confirms evidence integrity, not proof success. The original command,
resource cap, fixtures and failed observation remain unchanged.

The separately prepared [namespace revision](../dafny-revision-002/README.md)
puts the additions in distinct top-level modules, retains their local
`Model`/`Shift` aliases with explicit bindings, and preserves every other source
byte, including contracts, bodies and termination clauses. Five offline checks
pass; all 31 frozen artifacts and 24 source provenance entries were reviewed.
That distinct source revision subsequently passed all 269 logged units in
[job 61753046](../qualification-002/RESULTS.md), under the same native limits.
The original failure is unchanged and was not retried. Negative controls and
model collection remain separate gates.

The historical 7/16 real-source repair score is unchanged.

## Vest reference: compositional proof succeeds

Both new modules pass in the full qualified default `vest_dev` scope and its
dependency crates. All 5,410 original timed occurrences retain their exact
multiplicities. The frame proof, batch proof and four recursive batch spec
checks add six successful entries: 5,416 occurrences across 5,306 inventory
keys. Native summary counts are separate: 346 verified for `vest_dev`, 3,279
for `vest_lib` and 2,102 for `vstd`, each with zero errors. Six fixed frame spec
definitions do not emit timing entries; they are source-bound and explicitly
unlogged, not six more observed passes.

`batch_roundtrip` calls `frame_roundtrip(first, rest_encoded)` and composes the
frame encoding, decoding, fit and length APIs. The two additions and exact
host registration are the only source changes. Root and an independent reader
checked source inventories, raw success flags, all 23 transferred artifacts,
tool bindings and the exact five inherited warnings. There are no new warnings
or proof bypasses in the additions. The source-bound inventory is frozen in
[reference-gate-vest-001.json](reference-gate-vest-001.json).

With one Cargo worker and one Verus thread, the native command took 385.64
seconds, used 84% of one CPU and peaked at about 1.17 GiB RSS. The complete
one-CPU Slurm job took 655 seconds and used 50.8% CPU over that interval, with
about 1.24 GiB peak RSS. Native timing and whole-job preparation costs remain
separate; this is not a controlled concurrency-speed comparison.

This establishes analyst-authored compositional proof feasibility. It is not
model-generated growth, executable parser generation, two sequential acceptance
events, or completed negative-control qualification. A separately prepared
[Dafny correction runtime](../qualification-002/README.md) passed 28 offline
tests locally, in isolation and on Cannon. Its native reference now passes
with complete source/inventory review. The remaining 23 controls may therefore
be prepared under a separately reviewed runtime. No model calls were made.
