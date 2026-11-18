# Real-repository evaluation stability

This verifier-only follow-up addresses two acceptance confounds identified by the
saved-output syntax diagnostic. It makes **zero model requests** and preserves
all original pilot and diagnostic files and scores.

## Warning policy

`warning_policy.py` adds a separate reporting layer to the unchanged native
coverage/proof scorers. Proof completion, original qualified acceptance,
additional operational warnings and unknown warnings are separate fields.
It recognizes only the exact observed Cargo incremental-session cleanup warning,
with error 39, a `vest_dev` session shape and a path inside that invocation's
recorded fresh target. It retains the complete warning text.

Unknown warnings, missing baseline warning blocks, ambiguous target arguments,
path traversal and warnings outside the exact target remain blocking for the
new policy. No warning can turn an unproved or incompletely covered workspace
into an eligible result. This reporting revision does not modify historical
acceptance files or automatically promote a revision. A future collection must
freeze the chosen policy explicitly.

The local replay reads twelve existing source-bound native observations by
repository path and exact hash, without duplicating their large raw logs.
This is policy qualification on inspected development evidence, not a new model
evaluation or a fresh success-rate estimate.

## Fixed resource experiment

Four new full-scope Dafny commands run sequentially on the same compute node:

| Order | Source | CLI resource limit |
| --- | --- | --- |
| 1 | Exact upstream reference | 20,000 |
| 2 | Exact saved swap candidate | 20,000 |
| 3 | Exact saved swap candidate | 100,000 |
| 4 | Exact upstream reference | 100,000 |

The two 20,000-limit observations are deliberate contemporaneous controls,
not automatic retries or replacements for historical results. Source order is
reversed at the higher budget. Each cell runs once, with all 28 explicit inputs
and 267 required named units, identical pinned Dafny/Z3/container versions,
one CPU, 2 GB and a 300-second wall cap per native command. The job has a
30-minute limit, no requeue and an exclusive submission record; the partition
must be confirmed nonpreemptible at submission.

Only the body of `FisherYates.Model.Swap` differs between the two sources.
Contracts, other sources, command scope and warning policy are unchanged.
The candidate is exactly the saved model response; no analyst repair is added.
The experiment records each target's CSV outcome/resource count and full-workspace
completion. A larger-budget pass supports budget sensitivity for that observation;
continued exhaustion is not proof of incorrect mathematics. Variation at the
same budget must be reported rather than selected away. One observation per
cell does not establish robustness, a minimal budget or a general causal effect.

All native invocations are compute-only. `preflight.py` runs unit and fake-process
tests without a verifier or provider. `ops.py` stages the frozen package, runs
that offline preflight, submits once, then retrieves full source-bound raw
stdout/stderr/CSV/resource/accounting records. There is no adaptive budget
escalation, source mutation after freezing, retry or model runner.
