# Reasoning expansion: six development tasks

Status: constructed, six offline design tests pass; verifier-only reference gate
**57104220** submitted once and pending. It was updated in place from `test` to
`shared,sapphire`, both live-confirmed `PreemptMode=OFF`; no requeue or duplicate
job. An earlier attempt to combine test with those partitions was rejected by
Slurm and made no change; both scheduling records are preserved. Actual Dafny
results are pending. No model requests, credentials, or future pilot authorization.

At approximately 20:20 UTC November 2, the [Harvard status page](https://fasrc.instatus.com/)
reported scheduler maintenance scheduled through 23:00 UTC (6 PM Eastern). This
is consistent with the pending job and absent start estimate, not proof of an
individual scheduler cause. A follow-up will inspect the existing job, review
all reference evidence, then submit the distinct negative phase only if that
gate passes. No fixture is marked validated at this checkpoint.

The preceding [balanced pilot](../monorepo-balanced-calibration-pilot-001/RESULTS.md)
reached 8/8 in each of conditional, sequence and map families. This new experiment
replaces exported target-law composition with proofs of relations among primitive
operations. It preserves the previous frozen experiments and failed evidence.
These are designed to increase reasoning demands; **model difficulty is unmeasured**.

| Family | New semantic instance | Obligation to construct |
|---|---|---|
| Conditional | Nested clamp | Clamping to an outer interval then a contained interval equals direct inner clamping, including boundary/equality cases. |
| Conditional | Clamp stability | A nonnegative change in input changes the clamped result by an amount between zero and that change. |
| Sequence | Reverse over concatenation | Induct on an arbitrary sequence and compose the recursive result with single-element append equations. |
| Sequence | Nested threshold filter | Induct and split on retention of the head; filtering twice at nested thresholds equals the stricter filter. |
| Maps | Commuting updates | Distinct-key updates commute; establish equal domains and equal values for every key. |
| Maps | Delete after update | Split the same-key/distinct-key cases and prove domain/value equality, including originally absent keys and empty maps. |

Each semantic instance has shallow/deep × shared/separate cells: **24 workspace
variants**, each containing two immutable clients. All seven provider/client/entry
files are byte-identical across the four cells of an instance. Helper contracts,
parameters, explicit induction setting and termination measure are also fixed.
The declaration and import differences are generated explicitly by `build.py`.

Shared has one editable helper and a fixed second helper that forwards to it.
Separate has two editable helper bodies with equal contracts. Copying the proof
is possible and legitimate. Number of editable bodies, output workload, helper
imports and source length therefore differ: this is not an equal-work causal
sharing comparison. Primitive definitions and map extensionality remain shared
in both conditions. Clients B use mirrored/shifted inputs or compose multiple
instances; they do not create independent sampled repositories.

Shallow views expose a complete equation for **one operation**, never the target
composition law. Deep views require assembling primitive facts across modules:
lower/upper/assembly for clamps, unfold/constructor for sequences, domains/pointwise
values for maps. `reference_operation_fact_depth` describes that designed
reference path (1 vs 3 or 2), **not measured minimum proof/dependency depth**.
Map equality uses an explicit common extensionality stage in both conditions.
Solver automation may still make some obligations easy; only a later approved
model evaluation can assess a remaining ceiling effect.

## Validation protocol

`test_design.py` checks deterministic reconstruction, balanced cells, immutable
clients/provider bytes, helper signatures/contracts, precise control mutations,
source inventories, unchanged shared forwarding body and absence of reference
proof bypasses. Six tests passed; full output is in `offline-tests.log`.

The 164 planned checks are split into two explicit, single-pass Slurm phases:

1. References: 24 expected whole-workspace successes plus 24 empty-helper proof
   failures. No negative-control job is submitted until reference evidence is reviewed.
2. Targeted negatives: 96 ordinary proof failures, 8 nondecreasing-recursion
   termination failures and 12 hidden-export name-resolution failures.

Negative controls omit operation facts, remove/mis-instantiate induction, assert
incorrect identities, repair only one separate helper, or deliberately weaken
HelperA's contract while retaining its clients. Contract weakening is an explicit
invalid control, never an allowed candidate edit. Hidden shortcuts must fail name
resolution; ordinary reasoning failures must not be credited for parse errors.
Termination controls require a termination diagnostic, even if other proof errors
also occur. We do not infer minimal proofs from these selected mutations.

Every check stages its exact nine sources and runs `dafny verify
--verify-included-files All.dfy` on a compute node with a 60-second limit, once.
The immutable manifest pins code, fixtures, tests and scripts. Runs save all input
bytes, source hashes, commands, exit codes, stdout/stderr, elapsed time and compute
metadata. `review.py` independently checks those records without rerunning Dafny.
Unexpected failures are preserved before any deliberate versioned correction.

These fixtures are trusted, authored development tasks, not model-generated data
or held-out tasks. Their proofs use locals and universal pointwise proof blocks
beyond the old calibration grammar. A separately tested protected-body protocol
is required before any future model trial; no old parser or freeze is changed.

The separate [development output guard](protocol/README.md) now passes nine
offline test methods, including exact reconstruction of all 24 reference sources
and 104 semantic negatives plus adversarial contract/scope/bypass rejections.
This code is outside the original verifier input manifest and does not change the
queued job. Its own test/code hashes are archived separately. Semantic fixture
validation and any future model protocol freeze remain pending.

Reproduce construction in a fresh directory with `build.build(path)`, run
`python3 -B test_design.py`, and use the pinned scripts only inside a Slurm compute
allocation. `preflight.py` refuses login-node execution and existing output paths.
