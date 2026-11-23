# Varied Dafny extension pilot: terminal partial cohort

Job **63210633** returned three responses before the frozen frontend-error stop
rule closed the run. **One addition passed**, one failed proof checking, and
one failed name resolution. Five declared requests were never dispatched and
remain closed. This is not a completed balanced eight-trial result; no 1/8
score or result for an unobserved task is reported.

| Task | Returned / planned | Outcome | Native evidence |
| --- | ---: | --- | --- |
| Stable filtering | 1 / 2 | Proof failure | 58 units passed; the new method's correctness unit failed on loop-invariant entry |
| Counted frame decoding | 1 / 2 | **Accepted** | All 81 units passed, including all 77 inherited units; zero warnings |
| Generic range splice | 1 / 2 | Frontend failure; stopped collection | Ten accesses to an unexported field; one indentation warning; no proof units checked |
| Tagged/bounded frame pair | 0 / 2 | Unobserved | No request or candidate |

All three outputs passed JSON extraction and the protected-body guard. There
were **three unique provider request IDs, zero SDK retries, zero ambiguous
outcomes and 25,719 tokens** (23,445 input; 2,274 output). Each request used a
fresh context and received no repair feedback. The scheduler reports 83 seconds
on one CPU, exit 2 from the deliberate terminal stop; no requeue or additional
submission occurred. The 398-file transfer includes the full package, exact
prompts and raw responses, candidate sources, CSV, stdout/stderr, resources,
authorization, permanent allocation claim, ledger and accounting.

[Strict collection replay](collection-review-001.json) reports
`PASS_TERMINAL_ACCOUNTING`, with `score: null`, and checks the complete archive.
That audit status validates evidence/accounting; it does not mean all candidates
passed. The full originals are under [retrieved-001](retrieved-001/), with the
[transfer inventory](transfer-001.json) and [raw archive](transfer-001.tar.gz).
The [independent evidence audit](reviews/independent-collection-001/REPORT.md)
and [source-bound reasoning diagnosis](reviews/reasoning-diagnosis-001/README.md)
agree with these outcomes without changing sources or invoking a verifier/model.

## Concrete findings

**The accepted decoder composes an existing generated API recursively.** Its
body calls the immutable `F.ReadU16Frame(input)` and recursively calls
`ReadCountedFrames(rest, count - 1)`. The fixed specification covers count zero,
malformed or insufficient input, exact payload count/order, bounded lengths,
re-encoding and the unconsumed suffix. It also uses `reveal F.ReadU16Frame()`;
this is source-assisted API reuse, not opaque-contract-only reasoning. The
previously accepted frame and frame-pair sources remain byte-identical and
verify in the new scope. This is one independently sampled addition to a fixed
saved base, not a new two-stage current-run trajectory.

**The filter supplied a false invariant.** At loop entry, `i = 0` and
`n = a.size`, so its proposed equality reduces to
`a.items == KeepBelow(original[..0], limit)`, whose right-hand side is empty.
A valid nonempty input, such as `[0]` with limit 1, contradicts that invariant.
This is an analyst counterexample to the annotation, consistent with the saved
native diagnostic. It is not a demonstrated incorrect executable filtering
result, and no repaired body was submitted or rescored.

**The splice crossed an actual export boundary.** The supplied DynamicArray
source exposes its public operations but omits `data` from the default export.
The candidate directly reads and writes `a.data`, producing ten native
resolution errors. The lexical edit guard correctly admitted a body-only edit;
Dafny then rejected inaccessible members. No source registration was omitted,
and there is no evidence of a provider or harness failure. The indentation
warning is retained separately; the primary failure is name resolution.

## Interpretation and next gate

These observations reveal failure patterns beyond the earlier 12/12 simpler
additions: stateful invariants and module visibility, alongside a successful
recursive composition. The cohorts differ in tasks and the new sample is
truncated, so they do not estimate a causal difficulty, repository or feedback
effect. The selected component scopes share Standard Library ancestry; this
is not whole-project verification or held-out generalization.

The protocol also limited the evidence: it stopped the remaining independent
trials on an ordinary candidate frontend error. A future separately frozen
cohort could classify fully captured candidate parse/type/resolution errors as
failed trials and continue, while retaining stops for provider ambiguity,
integrity drift and unresolved native execution. This run and its ledger must
remain closed; that prospective policy is not applied retrospectively here.

The [new budget observation](../research-budget-20261123-008.json) records
22 returned calls across the current 100-call budget, 36 allocated slots,
14 unused slots permanently closed across allocations, and 64 unallocated.
No additional model or diagnostic verifier calls were made after this run.
All historical scores and the four-task qualification evidence remain unchanged.
