# Varied calibration: frozen proposal, not authorized

**32 proposed Claude requests; zero dispatched.** This is the calibration stage
of the existing [144-call staged corpus proposal](../../docs/corpus-family-split-plan.md),
not an additional collection or a reuse of an exhausted budget. No runner,
Slurm submission, credential handoff or authorization file is created.

| Scope | Count |
| --- | ---: |
| Development semantic instances | 4 |
| Shallow/deep × shared/separate workspaces per instance | 4 |
| Independent fresh-context responses per workspace | 2 |
| **Proposed requests** | **32** |
| Maximum generated tokens per request | 4,096 |
| Aggregate output-token ceiling | 131,072 |

The active bundle is [frozen-001](frozen-001). It pins **16 exact request
payloads**, 32 ordered trial slots, all empty seed files, current output policies,
settings and input/evidence hashes. No reference helper solution or negative
control is placed in a model prompt. Reviewed reference sources are used only by
the offline preparation gate. The request context includes full empty-workspace
source plus a source-derived include/import map in every condition; context
presentation itself is not an experimental variable here.

## Ordering and settings

Each 16-slot replicate visits every workspace once. Each four-slot block contains
all four families and all four structural cells. Each family and cell also occurs
once in every within-block position across the four blocks. The second replicate
reverses block and position order, then rotates one block; no adjacent slots use
the identical workspace. [trials.json](frozen-001/trials.json) is authoritative.
Repeated samples use identical request hashes and fresh conversations, with no
feedback, previous responses or repair attempts. They are not new semantic tasks.

For continuity, the proposed configuration copies the preceding witness/map pilot:
`global.anthropic.claude-opus-4-5-20251101-v1:0`, region `us-east-1`, temperature 1.0,
maxTokens 4096. This is a pinned prior model configuration, not a claim that it is
the newest model or a current availability check. No provider request was made.
Input sizes are recorded in [request-sizes.json](frozen-001/request-sizes.json);
byte counts are not model token counts or a dollar-price estimate.

Any later authorized runner must enforce a global 32-reservation cap, one SDK
attempt, no automatic retry/requeue, no unused-slot reassignment and a fresh
absolute execution deadline. A reserved ambiguous request consumes its slot and
stops the run; it must never be resent blindly. Transport/credential failures stop
the batch. A completed parse/guard/proof/warning failure is an evaluation outcome,
not a reason to spend another request. No extra connectivity calls are budgeted.
The user must approve this exact scope before any paid execution.

## Evaluation and research limits

Primary success requires the fixed output policy to admit the candidate, every
protected byte to remain intact and whole-repository Dafny verification to finish
with strict exit zero and no warnings. Log envelope extraction, body admission,
parse/name failures, proof/precondition/assertion failures, termination failures,
warning-only outcomes and infrastructure failures separately. Keep raw prompts,
responses, request IDs, SDK retry metadata, usage, guarded sources and all verifier
logs. Analyst diagnostics, if later requested, cannot change the original score.

Report each of the 16 workspace cells with its two individual outcomes, plus
per-instance summaries. Report editable-body duplication, generated tokens and
prompt size as descriptive workload measures. There is one semantic instance per
family, so these results cannot establish a family-wide effect, proof minimality
or a general causal depth/sharing advantage. Shared mode has a fixed forwarding
helper and one editable body; separate mode has two copyable bodies. Import depth,
reference contract-path length and recursion are distinct; see the
[verified structural audit](../varied-calibration-001/RESULTS.md).

Allocation is an existential feasibility proof with supplied witness values,
not an executable method returning the pair. Other concrete client contracts and
their differences from the initial proposal are documented in the task results.
All four tasks descend from inspected development families. No tree/transition
reserved instance or later M1/M2 collection task is included.

## Preparation checks

The [primary fixture gate](../varied-calibration-001/current-evidence.json) has
126/126 expected outcomes and exact source matching. Seven plan tests pass,
including a full deterministic rebuild while network and process dispatch are
blocked, all task/cell/position counts, refusal of budget/retry mutations, exact
seed/payload checks and literal printed syntax examples under every registry.
The current freeze SHA256 is
`db299e947d4a5b62fcc7f57d1a8dd374dfcef027789352d88eabded7072eb7b8`.

[rejected-draft-001](rejected-draft-001/README.md) preserves an unexecuted draft
whose displayed quantifier binder conflicted with a map parameter. The final
example uses fresh `key0`, and the tests now extract the actual printed snippets.
No mathematical fixture or old result changed. A separate verifier-only
[alternative-proof check](../varied-calibration-001/alternative-proof-001/README.md)
completed as job 59355663 with 16/16 strict passes and no errors/warnings. Its [readiness review](../varied-calibration-001/alternative-proof-001/readiness-review.json) binds the unchanged proposal freeze. It does not change request bytes or authorize execution.

Reproduce offline:

```bash
python3 -B experiments/varied-calibration-plan-001/prepare.py
python3 -B experiments/varied-calibration-plan-001/test_plan.py
```

The alternative-proof review is complete. The next execution gate is separate user budget
approval and a tested, hash-bound bounded runner. None is currently authorized.
