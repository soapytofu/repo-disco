# Named-target measurement results

November 12, 2026. All five verifier checks matched their expected outcomes.
**Zero model calls.** These analyst controls validate measurement; they do not
demonstrate an LLM local-versus-global performance gap.

| Fresh-move state | Editable helpers locally complete | Supplied clients locally verified | Clients with verified helper dependencies | Strict whole workspace |
| --- | ---: | ---: | ---: | --- |
| Shared reference | 1/1 | 2/2 | 2/2 | Pass |
| Shared empty helper | 0/1 | 2/2 | 0/2 | Fail |
| Separate, only A repaired | 1/2 | 2/2 | 1/2 | Fail |
| Separate, only B repaired | 1/2 | 2/2 | 1/2 | Fail |

Job **60035863** ran on nonpreemptible test in 21 seconds. Each state logged
14 verification units; supplied providers passed. Failures are helper
postcondition failures, with no parse errors or warnings. Both clients can verify
locally against declared helper contracts even when a helper body fails. Their
local success therefore cannot be credited as model-completed work or accepted
as whole-workspace correctness.

Job **60038131** ran one unchanged corrected deep/shared restriction reference
on test in 14 seconds: 20 verified obligations, zero errors/warnings, strict
exit zero. Its different declaration inventory also matches the logger and
interpreter. This checks compatibility on a second task, not another independent
model trial.

The unit is one named lemma's complete contract, grouped across all its logged
obligations. It is not one CSV row or one `ensures` clause. HelperA/HelperB are
the possible editable units; ClientA/ClientB and provider definitions are supplied.
Shared mode has one editable body and separate mode has two, so their denominators
and workload differ. Dependency closure follows the fixed forwarding/client
calls; it does not establish necessary mathematical proof depth.

Both collectors used the existing all-included-files verification flags plus
`--log-format csv`. Exact sources, contracts, guards and runtime hashes are
preserved. No old parser, verifier, model response, frozen prompt or score changed.
Four runtime tests per collector passed locally and on Cannon; six interpretation
tests check saved evidence, malformed/missing/duplicate units and graph errors.

- [Reviewed target results](target-review.json), reproduced by
  `python3 -B review_targets.py` without model or verifier execution.
- [Four-state raw archive](verification-001/), including exact sources, stdout,
  stderr, exit status, raw CSV and environment.
- [Restriction compatibility archive](restriction-001/verification-001/).
- Job logs, accounting, submission locks, transfer hashes and offline test logs
  are retained alongside each archive.
