# Dafny-VMC sequential extension candidate

Prepared offline November 18, 2026. **No model calls and no Dafny invocations.**
The sources below are analyst-authored feasibility controls, not generated
repositories or verified results. Native qualification under pinned Dafny 4.4.0
is still required before a model prompt freeze.

## Two new operations in a dependent chain

The pinned upstream Fisher-Yates API has sequence swap and shuffle operations,
but no stable extraction or ordered two-position selection operation was found
in its `src/Util`/`src/Math` source review. This extension adds deterministic
permutation utilities; it does not assert a sampling distribution or add a new
random generator.

1. **MoveToFront(xs, k)** rotates the selected element to the front and preserves
   the relative order of every other element. The exact result is
   `[xs[k]] + xs[..k] + xs[k+1..]`. Length and multiset are preserved. The reference
   performs adjacent calls to the existing `FisherYates.Model.Swap`, then recurses
   with the strictly smaller index. This adds stable movement, not a renamed
   swap: swapping only positions zero and `k` violates the contract for `k >= 2`.
2. **PickPair(xs, i, j)**, for `i < j`, moves the two original selected elements to
   the first two positions, in that order, while preserving the remaining order.
   The exact result is
   `[xs[i], xs[j]] + xs[..i] + xs[i+1..j] + xs[j+1..]`.
   The reference applies the accepted `MoveToFront` to index `i`, then applies it
   to the suffix with adjusted index `j-1`. The alternative selects `j` first and
   then index `i+1`. Both depend on the first addition's published contract, and
   require index/sequence reasoning beyond simply forwarding one call.

For example, on `[0,1,2,3]`, `MoveToFront(_,2)` yields `[2,0,1,3]`, and
`PickPair(_,1,3)` yields `[1,3,0,2]`. Duplicate values and endpoint choices are
included in the finite semantic checks.

The first module exports the function contract with `provides`, hiding its
implementation from the second module's public import. This supports a genuine
provider/client proof boundary. A valid direct implementation might still avoid
calling the first addition; actual API use must be reported separately, and
syntactic calls do not establish necessary proof dependence. The direct-slice
MoveToFront alternative is explicitly retained as a valid alternative candidate.

## Protected and editable material

Start with pinned Dafny-VMC commit
`e3631f8d335bf7ec3648b13976fa2a96a2a5406e`. All 91 upstream files remain immutable.
The additive files live at `repodisco-growth/MoveToFront.dfy` and
`repodisco-growth/PickPair.dfy`, outside the upstream `src/**` glob. The host must
explicitly register every current extension source in each verification command.
No upstream file or configuration needs editing.

The host fixes module names, public exports, imports, signatures, generic types,
preconditions, exact result/length/multiset postconditions and decreases clauses.
Only the marked function body of the current stage is eligible for model edits.
Stage two preserves the complete accepted stage-one source byte-for-byte. No new
assumptions, axioms, verification-disabling attributes or termination exemptions
are permitted. The existing upstream trust boundary remains disclosed unchanged.

For a future one-chain study, at most two model responses are needed: one per
stage, with no retry or repair round. This is a design count, **not execution
authorization**. Stage two is dispatched only after the actual stage-one candidate
passes the full augmented scope and is recorded as an accepted parent. Its prompt
must contain that accepted addition, not an analyst reference. If stage one fails,
the child is blocked/undispatched. No slot reassignment is allowed.

Prompts, dynamic-parent template, guard, policy and runner are not frozen here.
Analyst references, alternatives, counterexamples and negative-control labels
must remain outside model-visible context. The second operation's target behavior
can be fixed before collecting the first addition; its exact instantiated prompt
must bind the accepted parent hash before dispatch.

## Native qualification controls

`build_controls.py` creates twelve source overlays, with expected outcomes in
`controls-manifest.json`. Each native run must retain the original 267 required
units and the original three-warning profile, plus the named units for every
new declaration. Expected new labels are pending actual CSV confirmation:

- `FisherYates.GrowthShift.MoveToFront (well-formedness)`.
- `FisherYates.GrowthPick.PickPair (well-formedness)` once stage two is present.
- `QualificationGrowthDetached.Fails (correctness)` in coverage controls.

| Control | Intended observation |
| --- | --- |
| move-reference, move-alternative | Full scope passes for each different correct candidate |
| move-noop | Exact stable-movement postcondition fails |
| move-endpoint-swap | Length/multiset are preserved but stable order fails |
| pair-reference, pair-alternative | Full scope passes for two different call orders/index adjustments |
| pair-noop, pair-first-only | Exact two-element selection contract fails |
| pair-wrong-adjustment | Calling the second movement at `i` instead of `i+1` fails the output contract |
| pair-with-unproved-parent | Provider fails; client may pass under its assumed contract; full scope must reject |
| detached-explicit | Explicit new failing module produces an actual proof failure |
| detached-omitted | Native command can pass without that outside-glob file, but required-inventory gate must reject missing evidence |

The two detached controls have identical staged source bytes and intended
coverage; only one deliberately omits the detached file from the native command.
Staging or hashing the file cannot count as verification. The omitted run is an
intentional negative coverage experiment, never a successful repository result.

All native checks are pending. Run them only on a compute node, with the exact
pinned Dafny/Z3/container versions and fixed predeclared budgets. No automatic
reruns or budget escalation. Preserve unexpected proof/parser/resource outcomes
before making any deliberate versioned correction. Native units, warning sets,
whole-scope result, timing and resource observations must be archived separately.

## Offline evidence

Four offline test methods passed. They check exact protected-boundary rendering,
concrete counterexamples for each wrong algorithm, separate omitted-file coverage
expectations and finite reference/alternative semantics over all 363 sequences
of lengths one through five on the alphabet `{0,1,2}`. This is 1,641 movement
inputs and 3,006 ordered pair selections, with duplicate values included. These
are finite Python checks of the intended sequence transformations, not Dafny
parsing or proof evidence.

The builder also checked all 91 pinned upstream file hashes. Full offline output
is in [offline-checks-001.log](offline-checks-001.log). Templates, body variants and
the resulting overlays are retained separately so proposed edit boundaries and
counterexamples can be reviewed before native qualification.
