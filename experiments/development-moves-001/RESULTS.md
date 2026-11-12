# Fresh-key move composition: verifier results

November 12, 2026. **38/38 expected outcomes, zero model calls.**

| Run | Job / elapsed | Observed |
| --- | --- | --- |
| Core | 60032605 / 1m04s | Four strict reference passes; four empty-body proof failures |
| Targeted controls | 60033595 / 1m23s | 26 proof failures; four hidden-export resolution failures |

Both jobs ran once on nonpreemptible `test`, without requeue. No source correction
or verifier retry was needed. References each verified 14 obligations with zero
errors/warnings; no case had a parse error, warning or timeout. These are control
outcomes across four cells of one semantic task, not model trials.

The deep `missing_inner_value` bodies fail a quantified postcondition. Stale-map
reads and occupied destinations fail call preconditions; retained-intermediate
keys and zero-value claims fail assertions; skipping singleton inputs fails the
helper postcondition; removing the intermediate certificate fails the domain-fact
call precondition. Every semantic failure is in an editable helper, not a
provider or client. Shallow omission removes a bundled domain/value observation
and also causes precondition/domain failures. Hidden calls report unresolved
`Certify` (shallow) or `ObserveMove` (deep); they are not proof failures.

The failure patterns are deliberately constructed controls. They establish that
the fixture detects the intended mistakes and can support a prospective model
experiment; they do not show that a model makes them on this task. A reference
path or a selected missing-call failure is not a minimum-depth proof.

Eight offline methods passed locally and on Cannon. The audits checked exact
frozen runtime/fixture hashes, all archived source bytes, full included-file
verification, one invocation per case, diagnostic categories, and fixed source
outside the allowed helper bodies. All prior pilot scores and frozen policies
are unchanged. Shared mode has one editable proof; separate mode has two and
allows copying. All supplied provider/client obligations must not be counted as
model-solved target specifications.

Evidence: [core review](verification-001-review.json), [negative review](verification-002-review.json),
[core raw archive](verification-001/), [negative raw archive](verification-002/),
[core transfer inventory](transfer-core.json), [negative transfer inventory](transfer-negatives.json),
the job-specific stdout/stderr/accounting files, and the hash-bound
[core gate](core-gate.json). `review.py verification-001` and
`review.py verification-002` reproduce the phase audits offline without invoking
Dafny or a model.
