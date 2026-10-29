# Revised sequence and relational development instances

Eight matched snapshots and 72 verifier controls. Six offline tests pass.
Verifier-only job 56197680 completed in 3m25s. All 42 sequence controls matched.
All four relational references failed in trusted existential provider proofs;
the relational negative controls are therefore not validation evidence. The full
failed run is preserved. Only sequence tasks are selected from this directory.
A separate revision-002 re-expresses the same existential using a named Witness
predicate/trigger, preserving helper and client contracts; it failed on a
non-ghost quantifier frontend error. Revision 003 adds the ghost modifier and
passes all 30 relational checks in job 56197984 (1m52s). Both failed runs and
their full logs are preserved. Only revision 003 relational tasks are selected.
No model calls, retries or credentials. This additive directory preserves all
prior calibration fixtures, guards, failures and scores.

Sequence Score(s,o) weights each element by its index starting at o. Concatenation
requires the generalized recursive call Prove(tail,t,o+1), not a fixed offset;
the suffix starts at o+length(s). The shared/separate helper interfaces and two
immutable clients are matched. Deep mode composes Split → Lift → Finish per
recursive step; shallow mode uses Direct with the same induction hypothesis.
Controls distinguish wrong offsets, missing recursion/base/step, wrong suffix,
nondecreasing calls, contract weakening and hidden Direct. This shares append
induction ancestry; it is not a new held-out family.

Relational Overlap requires constructing a common witness for two intervals;
there is no supplied witness parameter. References choose max(a,c) and establish
both interval facts at that identical value. Deep mode joins the two facts before
Finish; shallow Direct still requires a valid witness. A second client swaps and
shifts both intervals. Controls test the wrong witness, missing facts/join, and
facts established at incompatible witnesses. Development diamond ancestry is
retained. No claim of greater model difficulty follows from verifier validation.

The additive body-json-v2.1 protocol keeps the v2 syntax rules and adds only the
pure function signatures needed by these two families. Explicit branches and pure
inline if expressions are admitted; no variables, quantifiers, multiplication,
reveals, assumptions or arbitrary declarations may appear in generated bodies.
Provider source can use richer Dafny; it is immutable and independently verified.

Shared mode exposes one editable body plus a fixed forwarding helper; separate
mode exposes two equivalent editable bodies. Copying is permitted, delegation is
not. Output/source workload differs; depth is reference-relative, not minimum
proof depth or raw import depth. These limitations remain part of the revised
pilot. Do not freeze or run a model until every selected verifier control passes
its expected category and the full evidence has been reviewed.
