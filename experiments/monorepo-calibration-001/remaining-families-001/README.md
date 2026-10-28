# Remaining calibration families — verifier-only construction

Twelve configurations of three development semantic instances: explicit sequence
induction, relational joining, and two finite-map updates with frame preservation.
Each has shallow/deep × shared/separate variants and two immutable clients.
Job 56015268 completed all 92 checks on non-preemptible `test` in 4m07s.
**Relational and map families: 58/58 expected outcomes reviewed.** The initial
sequence provider has a well-formedness error in an opaque predicate: 32 checks
contain an out-of-range tail slice; the two hidden-name checks resolve earlier.
These initial sequence results are not accepted calibration evidence. All original
snapshots and logs are retained in verification-001. Four offline design tests pass;
zero model calls. The stricter offline review classifies these failures separately
from the preflight runner’s broad diagnostic matches.

A deliberate [revision-002](revision-002/README.md) adds the explicit nonempty
guard to StepReady. Only its 34 sequence controls are rerun, as job 56016216.
Relational/map sources are not rerun or altered.

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
