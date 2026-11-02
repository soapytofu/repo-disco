# Reasoning expansion: six verified development tasks

**Complete: all 164 final fixture checks matched their expected outcomes. No model
calls.** Current sources are in [revision-003](revision-003/README.md); use that
builder and fixtures. Root fixtures and runtime-002 preserve earlier versions.
See [results](RESULTS.md) and the [complete evidence index](revision-003/completion-review.json).

The preceding [balanced model pilot](../monorepo-balanced-calibration-pilot-001/RESULTS.md)
reached 8/8 in the conditional, sequence and map families. These new tasks require
constructing relationships among primitive operations, rather than calling a
provider lemma that already states the target law. They are designed to increase
reasoning demands; **their difficulty for models remains unmeasured**.

| Family | Semantic instance | Required reference reasoning |
|---|---|---|
| Conditional | Nested clamp | Relate an outer clamp, a contained clamp and a direct inner clamp, including boundaries. |
| Conditional | Clamp stability | Bound the change in the clamped result under a nonnegative input increment. |
| Sequence | Reverse over concatenation | Construct induction, instantiate one-step equations and reassociate sequences. |
| Sequence | Nested threshold filter | Induct and split on head retention under two ordered thresholds. |
| Maps | Commuting updates | Prove equal domains and equal values for all keys after two distinct-key updates. |
| Maps | Delete after update | Handle equal/distinct keys, absent keys and empty maps through domain and pointwise reasoning. |

Each instance has shallow/deep × shared/separate cells: **24 workspace variants**,
with two immutable clients each. Within an instance, all seven provider/client/
entry files are byte-identical across cells. Helper contracts, parameters,
induction settings and termination measures are fixed across reference conditions.

Shared has one editable helper and a fixed forwarding helper for its second client.
Separate has two editable helper bodies with equal contracts; copying a proof is
legitimate. Source length, imports, output workload and editable-body count differ.
This is not an equal-work causal sharing comparison. Primitive definitions and
map extensionality remain shared in both conditions. The second client applies
mirrored/shifted inputs or composes applications; it is not a new independent sample.

Shallow views provide a complete equation for one operation, never the target law.
Deep views split facts across modules: lower/upper/assembly for clamps,
unfold/constructor for sequences, and domains/pointwise values for maps.
`reference_operation_fact_depth` describes this designed path (1 versus 3 or 2),
not proved minimum dependency depth. Map extensionality is common to both depths.
Solver automation may still make some tasks easy; verifier results establish no
model performance or sharing/depth effect. All instances are authored development
fixtures, not held-out tasks or a model-generated corpus.

## Validation and evidence

The final set contains 24 reference passes, 120 ordinary proof failures (including
24 empty-helper controls), 8 nondecreasing-recursion failures and 12 hidden-export
name-resolution failures. No parse failure is credited as a reasoning failure.
Controls remove operation facts, omit/mis-instantiate induction, assert incorrect
identities, repair only one separate helper, weaken one helper contract, or call a
hidden shortcut. Contract weakening is an explicitly invalid control, not an
allowed candidate edit. Selected ablations do not establish minimal proofs.

Every executed check stages nine exact sources and runs `dafny verify
--verify-included-files All.dfy` once on a nonpreemptible compute node, with a
60-second process limit. Archives contain all inputs, source hashes, commands,
exit codes, stdout/stderr, durations and environment metadata. Offline review
scripts check those records without rerunning Dafny.

- [runtime-002/verification-001](runtime-002/verification-001): first 48 semantic
  checks; four reverse references failed. Original failures remain unchanged.
- [revision-003/verification-001](revision-003/verification-001): four revised
  reverse references passed after making base/induction/reassociation explicit.
- [reference gate](revision-003/reference-gate.json): reuses 44 earlier outcomes
  only because their source bytes match the final revision exactly.
- [revision-003/verification-002](revision-003/verification-002): all 116 targeted
  negative controls matched their expected diagnostic categories.
- [completion review](revision-003/completion-review.json): all 164 final conditions,
  evidence links, hashes, categories and reuse flags. There were 168 actual Dafny
  invocations across history, including four preserved failed original references.

The initial job 57104220 failed before Dafny on missing Python package imports;
its [startup review](startup-failure-review.json), logs and scheduling records are
also preserved. The first attempt to combine test with other partitions was
rejected without changing the job; later scheduling changes made no duplicates.
Maintenance was reported, but jobs did start, so it is not assigned as their cause.

## Output policy and reproduction

The separate [output guard](protocol/README.md) passes nine offline tests for
bounded locals, recursion, branches, assertions and universal pointwise proofs.
The final revision's eleven offline tests include six design invariants, two
runtime checks and three revision/evidence/guard checks. All 24 final references
reconstruct exactly through the guard. Syntax admission is not verification;
alpha-renamed alternative test sources have not independently run through Dafny.
Prior frozen parsers and model prompts are unchanged. No model pilot is frozen
or authorized for these tasks.

For the final offline evidence audit, run:
`python3 -B experiments/monorepo-reasoning-expansion-001/revision-003/review_completion.py`.
For fresh construction, use revision-003/build.py's `build(path)` with a new empty
directory. Compute preflight scripts refuse login nodes and existing output paths.
Do not rerun archived jobs merely to reproduce this review.
