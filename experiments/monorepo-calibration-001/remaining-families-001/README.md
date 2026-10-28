# Remaining calibration families — verifier-only construction

Twelve configurations of three development semantic instances: explicit sequence
induction, relational joining, and two finite-map updates with frame preservation.
Each has shallow/deep × shared/separate variants and two immutable clients.
Job 56015268 is submitted to non-preemptible `test`, no requeue, for 92 controls.
**Verification pending; zero model calls.** Four offline design tests pass.

`build.py` generates exact source snapshots, `checks.json` defines expected
outcomes, and `manifest.json` pins the compute inputs. Failed controls and revisions
will be retained. References must pass; ordinary negatives must be proof failures;
six explicit hidden-Direct controls must fail name resolution, not parsing.

Depth is reference-relative. Sequence induction uses one versus three provider
stages per recursive step, plus the same recursive obligation and base case.
The relational diamond has two independent first-stage facts, a join, then Finish
(one versus three stages; one versus four calls). Map proofs use two sequential
updates followed by a common Compose lemma (three versus seven calls). These are
not identical linear chains or certified minimal proof depths. In every family,
shared mode edits one helper and retains an immutable forwarding wrapper;
separate mode edits two equivalent helper bodies. Source size/edit count and the
shared forwarding edge differ intentionally. No model difficulty finding is made.
