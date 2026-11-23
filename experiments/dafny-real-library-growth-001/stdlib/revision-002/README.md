# DynamicArray body revision 002

The original compute run, job `63086889`, passed all 56 baseline obligations. Its
`AppendAll` correctness check failed because the loop invariant `a.Valid?()` could
not establish the function's reads footprint. The `AppendRotated` correctness
check passed under the declared parent contract while `AppendAll` remained
unproved. Those sources, logs and outcomes remain unchanged.

This version moves the existing `fresh(a.Repr - old(a.Repr))` invariant immediately
before `a.Valid?()` in three loop bodies: `append-reference`, `append-reverse`, and
`rotate-direct`. At a loop head, the current representation may differ from the
method-entry representation. The proposed ordering makes its freshness fact
available before checking validity's reads footprint. No invariant formula,
executable statement, contract, signature, import, frame, or decreases clause is
changed. `permitted-body-diff.patch` records the complete three-body change.

All five other bodies are byte-identical, including the recursive append
alternative and both call-based rotation implementations. Every applicable
stage-two workspace contains the exact revised stage-one reference. The
unproved-parent and omission controls remain deliberate failures of workspace
qualification. A direct rotation implementation remains admissible; API reuse
is an observed property, not a necessary proof dependency.

`cases.json` contains eleven source workspaces. The first native phase should run
only `append-reference` and `rotate-reference`, preserving the fixed 1,000,000
resource limit, 300-second verifier limit, 360-second outer limit and one CPU.
The baseline is reused as prior evidence rather than rerun. Nine remaining
controls are prepared but gated on a source-bound review of both revised
references and their complete unit inventories. The old run exposes 58 units
for append and 60 for rotation: the 56 baseline units and two units per new
method. Every required unit must be checked; a passing child is insufficient
when parent correctness fails.

`build.py` validates the original source construction and exact upstream release
blobs, then reconstructs these versioned workspaces without modifying prior
files. `revision.json` binds the old sources and native evidence; the manifest
pins all generated bodies, workspaces and revision metadata. Construction tests
check only scope and byte integrity. The revision's mathematical outcome is
**unknown until the new compute checks**. No model calls are authorized here.
