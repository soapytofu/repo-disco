# Varied extensions of model-grown Dafny components

This follow-up tests four new extension tasks on the exact qualified Dafny
Standard Library and AWS MPL UInt component snapshots. The earlier pilot
accepted all twelve append/frame additions. Those results motivate tasks with
new reasoning demands; they do not establish these tasks are harder for models.

**Current result: fresh balanced cohort, 3/8 accepted.** Job 63440248 returned
all eight responses under the same task prompts and native limits: filtering
0/2, counted decoding 1/2, splicing 0/2 and tagged/bounded pairs 2/2. Four
candidate frontend failures remained rejected while collection continued;
one decoder exhausted its fixed solver budget. All eight passed extraction
and the edit guard, with eight unique request IDs, zero SDK retries and
73,890 tokens. The job completed in 4m25s on one CPU. See
[final results and full evidence](execution-002/COLLECTION.md).

**Earlier terminal partial cohort, unchanged.** Job 63210633 returned three
responses: counted-frame decoding passed, filtering failed a loop invariant,
and splicing failed on accesses to an unexported field. The frozen frontend-error
stop rule closed the remaining five slots. All three outputs passed extraction
and the edit guard; there were zero SDK retries and 25,719 tokens. This is one
accepted addition among three observed responses, not a balanced eight-trial
score. See [results and full evidence](execution-001/COLLECTION.md).

The planned tasks are stable array filtering, generic array splicing, counted
frame decoding, and tagged/size-bounded frame validation. Each is an independent
addition to a fixed source snapshot that includes previously accepted model
code where relevant. The two responses for a task see the same saved base;
neither response is repaired, retried, or used as the other's parent. This is
extension of model-grown components, not a newly collected two-stage trajectory.

Reference solutions, exact native unit inventories, targeted proof failures and
coverage controls must be reviewed before collection. The initial AWS references
pass, the revised filter passes all 59 native units, and the existing splice
alternative passes all 60 units under unchanged contracts and resource limits.
The shift-based splice reference's resource failure remains preserved separately.
Exact inventory mapping passed. The first 26 controls produced 24 matching
expectations and two splice resource failures, preserved separately. Two
replacement controls based on the passing rebuild implementation then matched
both intended ordinary proof failures. No prior observation is rerun or rescored.
See [initial native results](qualification-001/RESULTS.md) and
[revised reference results](qualification-003/RESULTS.md), and
[passing filter / remaining splice diagnostic](qualification-004/RESULTS.md),
the [splice resource failure](qualification-005/RESULTS.md), and the
[passing splice alternative](qualification-006/RESULTS.md).
The [control results](qualification-002/RESULTS.md) distinguish ordinary proof
failures, omitted coverage and resource exhaustion; the [two new replacement
controls](qualification-007/RESULTS.md) separately establish exact-content and
unproved-helper rejection using the passing rebuild implementation.
The [current 30-expectation gate](native-profiles-001/control-gate-001/gate.json)
binds four selected references and 26 matching controls. Three earlier resource
failures remain preserved outside that active matrix.
Only the current method/function body is editable; types,
contracts, fixed specification helpers, upstream files, saved accepted code,
termination clauses and the explicit source registration remain host-owned.

The bounded pilot allocated at most **eight new calls**: four tasks times
two fresh contexts. Task order is reversed for the second replicate. Ordinary
proof failures remain failures; collection is not extended to reach a favorable
score. The original execution-001 policy stopped on candidate frontend errors.
Fresh execution-002 prospectively allows a rejected candidate with fully
captured, source-bound frontend diagnostics to continue independent dispatch;
it keeps the original success criteria. Unknown native failures,
infrastructure, source-integrity or ambiguous provider failures still stop
collection. There are no retries or reassigned slots.

The primary outcome is strict acceptance of the complete selected workspace,
reported separately for each task (two planned responses each). Also report
parser/guard admission, proof versus resource failure, preserved inherited
coverage, request IDs, token counts and verification time. Undispatched requests
and ambiguous provider outcomes have no proof score. Any observed calls to
supplied APIs are descriptive; alternative direct implementations are valid.
The earlier twelve accepted additions remain a separate, simpler development
cohort, not a matched control or evidence of a causal difficulty difference.

The [current budget observation](research-budget-20261123-010.json) records
44 slots allocated within the user's 100-call ceiling, 30 returned responses
across the session, 14 permanently closed unused slots and 56 unallocated.
Both varied-pilot claims/ledgers are closed; the original five undispatched
slots were not reused.
The [four prompts and eight-slot order](pilot/README.md) and
[bounded runner](execution-001/README.md) remain frozen. Before collection,
98 tests passed locally, in the isolated package and on Cannon; the actual
eight-slot renderer simulation passed without provider or native calls.
The [fresh runner](execution-002/README.md) separately passed all 113 tests
locally, in isolation and on Cannon before the new collection, with complete
preparation and collection logs preserved.

This is selected-component development evidence. The Standard Library ancestry
shared with AWS, supplied contracts, prior exposure to the task families and
small sample size preclude independent-family, held-out or whole-project claims.
All previous scores and frozen artifacts remain unchanged.
