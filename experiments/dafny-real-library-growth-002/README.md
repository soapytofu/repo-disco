# Varied extensions of model-grown Dafny components

This follow-up tests four new extension tasks on the exact qualified Dafny
Standard Library and AWS MPL UInt component snapshots. The earlier pilot
accepted all twelve append/frame additions. Those results motivate tasks with
new reasoning demands; they do not establish these tasks are harder for models.

**Current result: terminal partial cohort.** Job 63210633 returned three
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
score. The frozen policy also stops on candidate frontend errors, new warnings,
infrastructure, source-integrity or ambiguous provider failures. There are no
retries or reassigned slots.

The primary outcome is strict acceptance of the complete selected workspace,
reported separately for each task (two planned responses each). Also report
parser/guard admission, proof versus resource failure, preserved inherited
coverage, request IDs, token counts and verification time. Undispatched requests
and ambiguous provider outcomes have no proof score. Any observed calls to
supplied APIs are descriptive; alternative direct implementations are valid.
The earlier twelve accepted additions remain a separate, simpler development
cohort, not a matched control or evidence of a causal difficulty difference.

The [budget observation](research-budget-20261123-008.json) records 36 slots
allocated within the user's 100-call ceiling, 22 returned responses across the
session, 14 permanently closed unused slots and 64 unallocated. The current
claim/ledger is terminal; its five undispatched slots cannot be reused.
The [four prompts and eight-slot order](pilot/README.md) and
[bounded runner](execution-001/README.md) remain frozen. Before collection,
98 tests passed locally, in the isolated package and on Cannon; the actual
eight-slot renderer simulation passed without provider or native calls.

This is selected-component development evidence. The Standard Library ancestry
shared with AWS, supplied contracts, prior exposure to the task families and
small sample size preclude independent-family, held-out or whole-project claims.
All previous scores and frozen artifacts remain unchanged.
