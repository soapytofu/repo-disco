# Initial growth reference checks

Status: November 18, 2026, 06:49 UTC. These are analyst reference checks with
zero model calls. They are not generated-repository results.

| Project | Job | Native observation | Next gate |
| --- | --- | --- | --- |
| Dafny-VMC | 61747428 | Completed; exit 2, module-resolution cycle, zero logged proof units | Preserve this failure and verify a separately versioned namespace correction |
| Vest | 61747454 | Still running at the last check | Retrieve and review the complete native evidence when terminal |

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
This remains unverified by Dafny and requires a separate
source review, frozen package and native observation. The original job will not
be retried. Neither the negative controls nor a model pilot can proceed yet.

The historical 7/16 real-source repair score is unchanged.
