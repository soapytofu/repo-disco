# Branch helper contract ablations (verifier only)

Status: job **55302459 completed on shared in 2m14s**, no requeue. All **22/22 checks matched expectations**: 14 passes and eight intended proof failures. **Zero model calls.** Exact fixture bytes, source hashes and diagnostics were reviewed; full evidence is in `verification-001/`.

The previous branching controls establish that each fixed client proof needs correct sign cases. This experiment asks a separate repository-level question: which distinct clients depend on the same helper guarantee? For each condition and each Case0A/Case1A/Case0B/Case1B helper, replace only its ensures clause with `true`, retaining all preconditions, signatures, bodies, exports, definitions and exact client source. Run each client independently with included-source verification. Baselines additionally verify the whole repository.

Expected sensitivity matrix: in shared, weakening Case0A or Case1A should break both clients, while weakening unused B helpers should break neither. In separate, weakening an A helper should break only ClientA, and weakening a B helper only ClientB. This provides four unused-helper negative controls in shared and isolates fixed-proof dependence from mere helper spelling or call counts. There are 14 expected passes and eight expected proof failures; resolution/parse errors do not count as proof failures.

Two offline tests check exact single-guarantee mutation, unchanged client/provider bytes outside that clause, and unique control IDs. `task.json` records the interventions; `checks.json` fixes expected statuses before verification. Full logs and hashes will be archived after the compute run. No prior experiment is edited.

## Interpretation and metric scope

Count distinct client targets affected by each weakened guarantee (0, 1 or 2), within a particular repository condition. Repeated trials are not new targets, and equal helper names across different repository variants do not prove a shared definition. Keep observed reference calls separate from ablation-tested contract dependence and from proof-prerequisite depth. These ablations test the saved reference proofs, not all possible proofs, model difficulty, or performance benefits of reuse. Both conditions retain common underlying definitions; separate does not mean zero shared code. No future model budget is authorized here.

## Measured fixed-proof sensitivity

| Weakened guarantee | Shared: affected targets | Separate: affected targets |
| --- | --- | --- |
| Facts.Case0A | ClientA, ClientB | ClientA |
| Facts.Case1A | ClientA, ClientB | ClientA |
| Facts.Case0B | None | ClientB |
| Facts.Case1B | None | ClientB |

Both baseline clients verify. The two used shared guarantees each affect two distinct targets; each separate guarantee affects one. Weakening unused shared B guarantees leaves both clients valid. `sensitivity.json` links each row to raw verifier evidence and scopes identity to the repository condition. These are measured dependencies of the fixed reference proofs, not model performance or proof-minimality results.
