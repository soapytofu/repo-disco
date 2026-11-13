# Broader verifier-feedback repair pilot — frozen proposal

**24 new model calls proposed; zero authorized or made.** The six workspaces are verified and the exact prompts, trial order, settings, diagnostics and output policy are frozen in [frozen-001](frozen-001). This expands the prior [map repair comparison](../map-feedback-repair-pilot-001/RESULTS.md) to three new development instances and different fault mechanisms.

| New task | Constructed failing seed | Verifier diagnosis |
|---|---|---|
| Soft-threshold composition (D1-M1) | Omits the intermediate saturation case | Unmet precondition for an above-threshold fact |
| Excluded-value interval witness (D3-M2) | Always picks the lower endpoint, even when it is excluded | Failed disequality assertion |
| Weave/unweave reconstruction (D2-M2) | Omits the recursive proof for paired tails | Unproved reconstruction postconditions |

These are **analyst-constructed faults**, not newly observed model mistakes. They are fresh semantic instances within familiar development ancestry. They do not consume or certify the reserved tree/transition test families, and their repair results must stay separate from the earlier natural-failure pilot and original generation scores.

## Proposed design and budget

**3 tasks × 2 sharing conditions × 2 feedback conditions × 2 fresh responses = 24 calls.**

- Shared: one editable proof and a protected forwarding helper. Separate: two editable bodies; copying is allowed. Both have two immutable clients.
- Detailed-feedback arm: the actual verified failing seed's exit code, stdout and stderr, with only the incidental CSV `Results File` line removed.
- Control arm: the same full failing source, contracts, syntax, symbol registry and failure notice, with no detailed diagnostic.
- Twelve distinct payloads, two requests each. The second block reverses the first block's twelve-cell order, giving every cell the same mean ordinal position. This does not supply matched sampling seeds or perfect transition balance.
- One repair request per trial, fresh context/store each time. No feedback updates, retries, replacements, resumed runs or reassigned calls. A transport ambiguity stops the batch and consumes its reserved slot.
- Same pinned model as the prior pilot: `global.anthropic.claude-opus-4-5-20251101-v1:0`, `us-east-1`, temperature 1.0, maximum 4,096 output tokens per request (**98,304 maximum output tokens total**). Input tokens and actual cost are not estimated here.

There is no varied depth factor in this pilot. The interface is fixed per family; task metadata describes the reference proof structure without claiming necessary minimum depth. Separate conditions also change output/edit workload, so this small pilot cannot isolate a pure sharing effect.

## Verification and output policy

[36/36 current verifier controls](../diverse-repair-tasks-001/RESULTS.md) matched expectations: 12 reference/alternative passes, 22 ordinary proof failures and two termination failures. The final gate reuses 24 byte-identical arithmetic/sequence observations and adds 12 corrected witness observations. Both earlier witness-provider failures are preserved. All current positives have zero errors/warnings; all six primary seeds fail in editable helper proofs while providers verify.

The copied parser uses the existing bounded grammar with a new task registry. It preserves providers, clients, imports, signatures, contracts and decreases clauses; rejects assumptions/reveals/declarations/attributes/alias shadowing/cross-helper delegation; and tolerantly extracts one unambiguous JSON body object. Six planning tests pass, including exact offline regeneration, feedback-only differences, budgets/order, diagnostic fidelity, protected edits and lineages. Eighteen primary/reference/alternative bodies replay exactly. No positive proof, counterexample, failure-type label or analyst repair advice is included in the model messages.

Primary success is guard-admitted **whole-workspace** verification: strict exit 0, nonzero obligations, zero errors and warnings. Rejected, truncated and proof-failing responses count as unsuccessful repairs. Report all reserved calls and execution failures separately; never retry to fill the table. Report each family and sharing/feedback cell separately, without pooling with historical results or asserting statistical significance from two responses per cell.

Secondary reporting includes named editable-helper completion, dependency-closed supplied clients, diagnostic categories, concrete edit descriptions, copied separate bodies and tokens. [Measurement scope](frozen-001/measurement-scope.json) pins the existing interpreter and replays 18 control states. Client verification against an unproved helper does not earn repository success credit. Self-recursive obligations belong to the helper's verification, not a cyclic cross-target dependency edge.

## Frozen artifacts and next execution gate

[Plan](plan.json), [trial order](frozen-001/trials.json), [12 exact requests](frozen-001/requests), [six failing parents](frozen-001/parents), [freeze manifest](frozen-001/freeze.json), [offline review](frozen-001/offline-review.json), [tests](offline-tests.log). The freeze binds 132 files and 239 repository inputs to the published verifier evidence. The preparation script can reproduce it offline with `python3 -B prepare.py check`.

A future run still needs **separate explicit 24-call approval** and a tested bounded adapter for these tasks, including the pinned CSV target scope and atomic revision promotion. No live runner, submission, credential handoff or model invocation is created by this planning work. Once approved, immutable originals and failed evidence must be preserved, and only strictly verified revisions may be promoted in each isolated trial store.

After collection, retain both easy and hard outcomes. Use the per-family contrast to decide whether feedback-assisted repair extends beyond the single inspected map failure. A larger, independently specified evaluation would be needed for general causal or held-out claims.
