# Fresh varied Dafny pilot: three of eight accepted

Job **63440248** completed the fresh, balanced eight-response cohort. **3/8
additions passed strict whole-selected-workspace acceptance**; four failed
frontend resolution/type checking and one exhausted its fixed solver-resource
limit. All eight passed JSON extraction and the protected-body edit guard.
There were **eight unique request IDs, zero SDK retries, no ambiguous outcomes
and no reassigned slots**. The allocation and ledger are closed.

| Task | Accepted / returned | Exact native outcome |
| --- | ---: | --- |
| Stable array filtering | **0/2** | Both access the unexported `DynamicArray.data` field: 11 and 6 resolution errors; no proof units checked |
| Counted frame decoder | **1/2** | One passes all 81 units; one passes 80 and exhausts resources on the new decoder's unit |
| Generic range splice | **0/2** | Ghost-derived sequences passed to executable `AppendAll`: 2 and 1 resolution/type errors; no proof units checked |
| Tagged, size-bounded frame pair | **2/2** | Both pass all 79 units, with zero warnings |
| **Total** | **3/8 (37.5%)** | **3 verified, 4 frontend failures, 1 solver-resource failure** |

The four task payloads, model settings, forward/reverse order, contracts, edit
guard, native toolchains and proof limits are unchanged from the original
partial cohort. Each response used an independent context, one request and
one native invocation, with no repair feedback. This is a fresh collection;
the [earlier one-accepted/three-returned partial result](../execution-001/COLLECTION.md)
and its five closed unused slots remain unchanged and are not pooled here.

## What the runner change did

The prospective policy rejects a fully captured candidate frontend error and
continues to the next independent trial. It requires normal exit 2, complete
resource evidence, zero proof units, matching counted frontend diagnostics
located in the editable addition, and no infrastructure markers or stderr.
It never treats missing proof coverage as acceptance. Unknown or inconsistent
evidence, provider ambiguity and infrastructure failures still stop dispatch.
Closed, source-bound solver-resource failures retain the existing unsuccessful
trial handling. The common native scorer and success criteria were not changed.

All **113 tests passed locally, in an isolated manifest-only package and on
Cannon** before submission, including the actual eight-slot synthetic renderer
simulation. The independent frontend-policy review includes 15 focused tests
and an exact replay of the old splice failure. In this live cohort, four such
frontend failures remained rejected and all eight planned responses were
collected. This demonstrates the changed dispatch behavior on these cases;
it does not establish universal harness correctness or improve their proofs.

## Concrete findings

**API visibility and ghost/executable boundaries remain model failure modes.**
Both filters attempt to manipulate the array's private backing field, although
its implementation appears in context and its export declaration excludes that
field. Both splices instead use the public append API but derive executable
sequence arguments from ghost `items` state. Dafny rejects those arguments.
The summary names `BoundedInts.dfy`, while the actual located diagnostics all
point to the added filter/splice files. These are compiler-level candidate
failures, not parser/edit-guard rejections or mathematical proof failures.

**Verified recursive and tagged composition is possible.** The accepted decoder
calls the saved `F.ReadU16Frame` API and recursively processes `count - 1`,
proving exact count, payload order, re-encoding and suffix preservation. The
tagged candidates call the saved pair reader, check the tag and combined size
bound, and preserve the exact unconsumed suffix. All three preserve and verify
the 77 inherited units. They also reveal supplied function definitions, so this
is source-assisted composition rather than opaque-contract-only reasoning.
They extend fixed previously model-grown bases; they are not new two-stage
trajectories collected in this run.

**One similar decoder remains unproved at the fixed budget.** Slot 07 reports
`Verification out of resource` for `ReadCountedFrames (well-formedness)`, with
500,057,327 recorded resource units against the predeclared 500-million limit.
The other 80 units pass, all inherited units are preserved, and the process
exits normally with code 4; no wall timeout occurred. This is not an established
semantic counterexample. The accepted decoder's corresponding unit used
1,230,898 resources. Their source bodies differ; no causal explanation or
minimal repair has been tested, and no resource limit was raised.

## Evidence and accounting

The strict offline [collection replay](collection-review-001.json) reports
`PASS_COMPLETE`, score 3/8 and a complete **550-file** transfer. It replays
exact request payloads, raw provider responses, guard reconstruction, protected
sources, fresh native execution bindings, full inventories, warnings, usage,
claim/authorization and the closed ledger. This audit status means the evidence
is consistent; only three candidates passed verification. The
[independent audit](reviews/independent-collection-001/) is separate from the
frozen production reviewer. Neither review made model or native calls.

- **73,890 tokens:** 69,626 input and 4,264 output.
- **4m25s on one CPU**, one nonpreemptible `test` submission, no requeue;
  119.051 CPU seconds and 308,056 KiB peak batch RSS in Slurm accounting.
- **Zero warnings** in all eight observations. Frontend failures have no proof
  coverage; the four AWS observations have complete inventories, including
  the unsuccessful resource-limited one.
- [Raw archive](transfer-001.tar.gz), [550-file hash inventory](transfer-001.json),
  [all extracted originals](retrieved-001/), [per-slot sources and native logs](retrieved-001/model-001/slots/),
  [request ledger](retrieved-001/model-001/requests/ledger.json),
  [Slurm accounting](retrieved-001/accounting.txt), and
  [full production review transcript](reviews/collection-review-001/).

The [new budget observation](../research-budget-20261123-010.json) records
30 returned requests across the current session, 44 allocated slots,
14 permanently closed unused historical slots and 56 unallocated. Unused
capacity is not a reason to extend this completed experiment. No further
model or verifier calls were made after collection.

These results show both usable constrained extensions and clear limitations
on more varied selected components. They do not establish full-project support,
independent-family generalization, a language advantage or a causal difficulty
effect against the earlier 12/12 simpler cohort. All historical scores,
qualification failures, prompt freezes and old ledgers remain unchanged.
