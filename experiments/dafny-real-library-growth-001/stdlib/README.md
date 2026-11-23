# DynamicArray extension drafts

This preparation adds two executable operations to the real Dafny standard-library
`DynamicArray` component at release **v4.11.0**, commit
`fcb2042d6d043a2634f0854338c08feeaaaf4ae2`. The seven upstream artifacts were
checked against Git blob identities by the root task. Upstream files are
read-only. **Native status is UNKNOWN:** these analyst-authored sources and
construction tests are not Dafny proof evidence or model-generated results.

`AppendAll(a, values)` pushes an input sequence onto an existing valid dynamic
array. Its fixed contract preserves the complete previous sequence, specifies
the exact new sequence and size, preserves validity, prevents capacity shrinkage,
and guarantees freshness of representation objects introduced by allocation.
The reference maintains these properties through a loop over public `Push`
calls. A recursive alternative has the same fixed declaration and contract.

`AppendRotated(a, values, pivot)` appends the batch's suffix and then its prefix,
returning the exact appended index interval. For example, initial contents `[9]`,
input `[1,2,3]` and pivot `1` give `[9,2,3,1]` and interval `[1,4)`. The reference
calls the first-stage operation twice and uses its updated size, sequence and
freshness contracts across calls. A direct `Push` loop is also admissible. Future
stage-two evaluation must keep the actual accepted first-stage bytes and evidence
from its own lineage; analyst references cannot stand in for an accepted model
parent. Syntactic API reuse is an observation, not a necessary proof dependency.

Both operations accept empty input, and either endpoint is a legal pivot. Only
the public API is used: the backing `data` field and the opaque body of `Valid?`
remain hidden. The fixed `reads a, a.Repr` and `modifies a.Repr` clauses preserve
Dafny's dynamic-frame discipline, including permissions for newly allocated
objects. This does not establish memory availability or amortized runtime cost.

The dependency-closed source baseline is exactly:

- `Source/DafnyStandardLibraries/src/Std/BoundedInts.dfy`
- `Source/DafnyStandardLibraries/src/Std/Wrappers.dfy`
- `Source/DafnyStandardLibraries/src/Std/DynamicArray.dfy`

DynamicArray imports the other two modules; neither has further imports or
includes. Qualification must explicitly verify these sources. The
`--standard-libraries` preverified bundle is not coverage evidence. This scope is
the DynamicArray component, not every standard-library module.

`cases.json` lists twelve self-contained, small source workspaces with explicit
`command_files`, immutable source hashes and named target expectations. It
contains the baseline, two references, two alternatives, four ordinary proof
negatives, an unproved-parent control, and two omitted-module controls. Every
ordinary negative retains the exact target contract. The unproved-parent case
expects the helper to fail while the child can verify against its assumed
contract; the full workspace must still fail. Omission cases stage a failing
addition but exclude it from the native command, so native success must be
rejected for missing required coverage.

The first native phase should establish baseline and reference inventories.
Remaining controls stay gated until those actual source-bound results are
reviewed. All original emitted obligations and every new emitted obligation must
be checked, with both target methods' correctness results mandatory. Missing
providers, unexpected parse errors, warnings, resource failures and timeouts are
separate outcomes. If a fixed total definition emits no unit, record that fact
and its source hash rather than calling it a logged pass.

Use Dafny 4.11.0 and the pinned upstream semantic options recorded in
`design.json`, with root's fixed resource limit 1,000,000, per-obligation time
limit 300 seconds, native outer wall limit 360 seconds and one CPU. No implicit
project-config glob is needed: all checked files are explicit. Tool/solver
identity and real output inventory still require compute-node qualification.

`python -B build.py` reconstructs the drafts and refuses any differing existing
output. `python -B -m unittest -v test_construction` checks source identity,
protected boundaries, scope/omission controls, dependency closure and finite
counterexamples. It never executes Dafny. No model prompts, execution handler,
paid budget or accepted-model receipt is frozen here.

Sources: [release DynamicArray](https://github.com/dafny-lang/dafny/blob/fcb2042d6d043a2634f0854338c08feeaaaf4ae2/Source/DafnyStandardLibraries/src/Std/DynamicArray.dfy),
[standard-library build configuration](https://github.com/dafny-lang/dafny/blob/fcb2042d6d043a2634f0854338c08feeaaaf4ae2/Source/DafnyStandardLibraries/src/Std/dfyconfig.toml).
Upstream remains under its saved MIT license. New extension bodies are analyst
fixtures for a future generation study, not fixes to an upstream defect.
