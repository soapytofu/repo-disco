# Restriction over disjoint merge: verifier results

November 12, 2026. **Revision 002 matches 38/38 expected outcomes; zero model calls.**

| Stage | Job / time | Evidence |
| --- | --- | --- |
| Initial core | 60033315 / 30s | Eight frontend failures from non-inferred finite comprehension bounds; preserved, not counted as successful controls |
| Corrected core | 60035065 / 43s | Four strict reference passes; four empty-helper proof failures |
| Targeted negatives | 60035790 / 2m11s | 26 proof failures; four hidden-interface resolution failures |

Current reference workspaces each verify 20 obligations with zero errors and
warnings. Every semantic negative fails only in editable HelperA/HelperB bodies;
providers and clients are sound under the unchanged contracts. No current case
has a parse error, warning, timeout or infrastructure failure.

The deep left/right observation omissions fail the `forall` postcondition.
Wrong-filter calls and the omitted restricted-disjointness certificate fail
preconditions. Assuming every value comes from the left map, or losing the right
map's domain, fails assertions. Skipping empty-left inputs fails the helper
postcondition. Shallow missing bundled observations also lose domain facts and
fail restricted-merge preconditions. Hidden interfaces reject `Certify` or
`ObserveMerge` as intended; these are resolution controls, not proof failures.

The correction changes only the equivalent domain expression in Kernel.dfy:
`q in m || q in n` becomes `q in m.Keys + n.Keys`. All helper bodies, target
contracts, clients, imports and exports are byte-identical to the corresponding
original controls. Nine offline methods passed locally and on Cannon. All eight
core checks were rerun because kernel bytes changed; no failed original outcome
was relabeled or reused as a successful check. No negative phase ran on the
invalid initial version.

This adds set-domain algebra, filtering and source-branch obligations to the
development map family. It does not measure model difficulty or demonstrate a
sharing effect, necessary proof depth, or held-out generalization. Separate mode
has two copyable helper bodies. Provider verification totals are not independent
model-completed specifications.

Reproducible current reviews:
[core](revision-002/verification-001-review.json),
[negatives](revision-002/verification-002-review.json).
Full raw input/diagnostic archives:
[core](revision-002/verification-001/),
[negatives](revision-002/verification-002/),
[initial failure](verification-001/).
Each run includes job stdout/stderr, accounting, submission lock, exact transfer
hashes and pinned code. The negative submission is bound to the reviewed core
gate. Run `review.py verification-001` and `review.py verification-002` from
revision-002 to reproduce the audits without Dafny/model execution.
