# Fresh repair-task validation

**36/36 current controls match their expected outcomes; zero model calls.** Canonical sources are in [revision-003](revision-003). The [validation gate](validation-gate.json) combines **24 unchanged observations** from job **60219031** and **12 corrected witness observations** from job **60220144**. Reused evidence is byte-identical and is not a new trial.

| Fresh development instance | Intended primary fault | Positive controls | Ordinary proof failures | Termination failures |
|---|---|---:|---:|---:|
| D1-M1: soft thresholds compose | Omits the intermediate saturation case; calls an above-threshold fact with an unmet precondition | 4 | 8 | 0 |
| D3-M2: interval witness excluding a value | Always chooses the lower endpoint; disequality assertion fails when that endpoint is excluded | 4 | 8 | 0 |
| D2-M2: weave/unweave reconstruction | Omits the inductive hypothesis on paired sequence tails; postconditions fail | 4 | 6 | 2 |
| Total | Six shared/separate repair inputs | **12** | **22** | **2** |

Each instance has shared and separate variants, two immutable clients, a correct reference, a different valid proof form, a primary faulty seed, an empty proof and two targeted negatives. All current positives verify strictly with zero errors/warnings. The six primary faulty seeds fail in the editable helper(s), while supplied providers verify. All failure categories were checked against the actual diagnostics; frontend errors and warnings do not count as proof failures.

These failures are **analyst-constructed**, not model outputs. They test controlled repair of fresh development task instances. They cannot be pooled with the earlier naturally observed map failures or presented as a model success rate. The tasks retain their familiar conditional/interval/sequence family ancestry; no held-out claim is made. Tree and transition-system reservations remain untouched.

The separate condition has two editable, copyable bodies; shared has one editable body and a protected forwarding helper. There is no newly varied depth factor. Each task records its actual reference structure: case-dependent threshold facts, bounds-to-existence facts, or recursive paired-tail reasoning. These annotations do not establish minimum reasoning depth or comparable cross-family depth.

## Preserved fixture history

- **60219031**, initial 36 checks, 1m32s: all 24 threshold/sequence controls were valid. The 12 witness controls exposed an existential-provider proof failure and trigger warning. Full original sources and logs remain in `verification-001`; the failed provider makes those witness observations unusable as task controls.
- **60219889**, revision 002, 12 checks: adding an internal witness predicate exposed a frontend compilability error because the existential predicate was not explicitly ghost. These are frontend failures, not proof findings. Full evidence remains in `revision-002/verification-001`.
- **60220144**, revision 003, 12 checks, 59s: declaring the existential predicate proof-only (`opaque ghost predicate`) resolves the frontend issue. All 12 witness expectations now pass, with no warnings. The internal predicate and explicit witness assertion establish the same arithmetic existence goal. Public argument/return types, goal meanings, helper contracts, repair seed bodies and clients are unchanged; the ghost qualification is explicit in the final source.

All jobs ran once on live-confirmed nonpreemptible Cannon `test` compute nodes, without requeue or automatic retries. Initial and revised offline suites passed six and seven tests respectively; the latest seven also passed on Cannon. All 36 current bodies replay through the bounded output grammar exactly. Scope tests reject contract/provider changes, assumptions, reveals, attributes, alias shadowing and cross-helper delegation. The parser below its task registry is unchanged from the prior common grammar.

## Evidence

[Source/diagnostic gate](validation-gate.json), [gate audit](assemble_gate.py), [audit log](gate-review.log), [named-target scope and 18 control replays](measurement-scope.json). The existing target interpreter is copied unchanged; reference, alternate and faulty states test provider validity and dependency-closed client scoring for each task. Recursive induction is checked inside the helper's own obligations, not represented as a cyclic cross-target dependency.

Original [review](results-review.json), [archive](verification-001), [transfer](verification-001-transfer.json); revision 002 [review](revision-002/results-review.json) and [archive](revision-002/verification-001); revision 003 [review](revision-003/results-review.json), [archive](revision-003/verification-001), [transfer](revision-003/verification-001-transfer.json). Each archive includes source/code hashes, exact staged `.dfy` files, stdout/stderr, byte-preserved declaration CSV, environment, scheduler logs and accounting. No credential or model invocation was needed.
