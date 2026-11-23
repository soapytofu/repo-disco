# Varied extensions of model-grown Dafny components

This follow-up tests four new extension tasks on the exact qualified Dafny
Standard Library and AWS MPL UInt component snapshots. The earlier pilot
accepted all twelve append/frame additions. Those results motivate tasks with
new reasoning demands; they do not establish these tasks are harder for models.

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
Only the current method/function body is editable; types,
contracts, fixed specification helpers, upstream files, saved accepted code,
termination clauses and the explicit source registration remain host-owned.

The bounded pilot will allocate at most **eight new calls**: four tasks times
two fresh contexts. Task order is reversed for the second replicate. Ordinary
proof failures remain failures; collection is not extended to reach a favorable
score. Infrastructure, source-integrity or ambiguous provider failures stop
dispatch. There are no retries or reassigned slots.

The primary outcome is strict acceptance of the complete selected workspace,
reported separately for each task (two planned responses each). Also report
parser/guard admission, proof versus resource failure, preserved inherited
coverage, request IDs, token counts and verification time. Undispatched requests
and ambiguous provider outcomes have no proof score. Any observed calls to
supplied APIs are descriptive; alternative direct implementations are valid.
The earlier twelve accepted additions remain a separate, simpler development
cohort, not a matched control or evidence of a causal difficulty difference.

The user's existing 100-call ceiling covers this requested pilot. The latest
completed budget snapshot allocates 28 calls, with 19 returned responses and
nine unused slots permanently closed. Eight new slots are now allocated in snapshot 007, bringing cumulative
allocation to 36 and leaving 64 unallocated. No request has been dispatched for
this cohort. Runtime-bound execution authorization waits for qualification and
runner review.

This is selected-component development evidence. The Standard Library ancestry
shared with AWS, supplied contracts, prior exposure to the task families and
small sample size preclude independent-family, held-out or whole-project claims.
All previous scores and frozen artifacts remain unchanged.
