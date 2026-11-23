# November 24 meeting: real-repository repair and growth

Reviewed November 23, 2026. **We now have two complete model-generated,
two-stage proof-extension trajectories on Vest.** Both second additions use
their own accepted first-stage proof. Neither Dafny lineage completed under
the fixed verification budget.

## Project overview and status

RepoDisco extends Formal Disco toward verified repositories with interacting
modules. The original research question asks how dependency depth, API reuse
and shared proofs affect whole-repository completion. Following Nada's feedback,
the current milestone tests progressive extension on pinned **Dafny-VMC and
Vest**, a Verus codebase.

The initial Weeks 1–4 setup, baseline and repository-infrastructure milestones
are complete. Current work is controlled corpus/evaluation and real-repository
growth. Broader independent-project evaluation, held-out testing and fine-tuning
remain unfinished. These growth results do not yet answer the causal structural
research question.

## New result: successive additions on real source

| Project and chain | First addition accepted | Second addition accepted | Complete lineages |
| --- | ---: | ---: | ---: |
| Dafny-VMC: stable MoveToFront → ordered PickPair | 0/2 | Both blocked; no calls | **0/2** |
| Vest: length-prefixed frame proof → counted-batch proof | 2/2 | 2/2 | **2/2** |
| Overall | 2/4 | 2/2 eligible children | **2/4 planned** |

**Four of six returned additions were accepted.** All six passed the parser and
edit guard. Six unique request IDs, zero SDK retries, no ambiguous requests;
two child slots remained unused. Usage was **244,001 tokens**. The job took
**1h10m26s on one CPU**, including preparation and full verification.

The frozen design uses Claude Opus 4.5, two fresh lineages per project, one
response per stage and no repair loop. A failed parent blocks its child.
Second-stage success is conditional on first-stage acceptance. These are two
repetitions of a selected chain per project, not four independent task families.

[Full results, code, responses and native logs](../experiments/real-repository-growth-001/execution-005/COLLECTION.md)
and [source/lineage/accounting audit](../experiments/real-repository-growth-001/execution-005/collection-review-001.json).

## One concrete extension trajectory

The host supplies a bounded length-prefixed frame specification: decoding
recovers the payload, consumes exactly the frame length, and preserves trailing
bytes. Claude supplies a proof body using Vest's existing serialization theorems.
That first proof passes the full declared repository scope.

The next prompt contains that **actual accepted source**. Claude then proves
the counted-batch property by applying the frame theorem to the encoded
remainder and proving the rest recursively:

```rust
frame_roundtrip(first, encode_batch(rest, tail));
batch_roundtrip(rest, tail);
```

This is an excerpt from the [accepted first batch proof](../experiments/real-repository-growth-001/execution-005/retrieved-001/model-001/slot-04/native/workspace/vest_dev/src/formats/growth_batch.rs).
Both completed children explicitly call their accepted frame theorem once;
both parent files are byte-identical between stages. The other lineage produces
different proof bodies.

**Scope:** the specifications, API declarations and edit boundaries are host
supplied. The model fills proof bodies. Vest demonstrates specification/proof
library growth, not executable parser generation or discovery of new requirements.
An observed API call shows reuse, not that every valid proof must use that API.

## What failed, and how to interpret it

Both Dafny first additions exhausted the fixed resource limit while all **267
upstream units still passed**. The new function was the sole unsuccessful unit.
There were no added warnings or native wall timeouts.

The first body has a concrete algorithmic error: on `[0,1,2]`, `k=2`, it
returns `[1,2,0]` instead of the required `[2,0,1]`. Its exact source repeats
the earlier candidate with a saved counterexample. The second body uses a
different swap; that counterexample does not apply. It remains **unproved at
the fixed budget**, rather than established mathematically wrong.

The current setup therefore succeeds at the selected Vest proof-composition
tasks and has no accepted Dafny algorithm extension in this small cohort.
This is not a controlled Dafny-versus-Verus comparison: tasks, context sizes,
toolchains and resource behavior differ. The next diagnostic should separate
the second Dafny candidate's proof/resource issue from the first one's semantic
bug before choosing a fixed-budget feedback intervention.

## Earlier results worth retaining

| Evidence | Result | Interpretation |
| --- | --- | --- |
| Real-source repair pilot | **7/16 qualified accepts; 8/16 full-proof outputs** | Successful constrained repairs on existing Dafny-VMC and Vest sites. Seven outputs were initially guard-rejected; later diagnostics remain separate. |
| Its feedback comparison | Diagnostics **3/8** vs notice **4/8** qualified; full-proof **4/8 each** | No demonstrated feedback advantage on these real-source task sites. |
| Fixed-source Swap resource diagnostic | Candidate **265/267** units at 20k, **267/267** at 100k; upstream passes at both | A changed transparent implementation can alter downstream proof cost without changing its contracts. |
| Growth qualification controls | **25/25 expected outcomes:** 8 passing scopes, 14 intended proof failures, 3 coverage rejections | Task feasibility and important false-success checks; these are analyst controls, not model successes. |

Sources: [repair pilot](../experiments/real-repository-repair-pilot-001/execution-001/RESULTS.md),
[separate guard diagnostic](../experiments/real-repository-guard-diagnostic-001/RESULTS.md),
[resource study](../experiments/real-repository-evaluation-stability-001/RESULTS.md),
[growth controls](../experiments/real-repository-growth-001/controls-001/RESULTS.md).
The earlier constructed-task repair result of **27/32**, including diagnostics
16/16 versus notice 11/16, is a separate cohort and not a matched real-world
generalization comparison. All original scores and stopped runs remain unchanged.

## Design choices to defend

- **Fixed contracts and body edits:** make success measurable and prevent
  weakening the requested behavior. This limits the claim to constrained completion.
- **Full declared verification scope:** check old code and every addition,
  including required proof inventory and warnings. A passing child cannot hide
  an unproved parent, and omitted registration cannot count as success.
- **Actual accepted parents:** preserve the model's first addition exactly
  before requesting its child; report observed API reuse separately.
- **One response per stage:** establish an auditable feasibility baseline and
  cost before evaluating feedback or additional tools.

Vest retained all **5,410 upstream timed occurrences**, passing 5,411 at stage
one and 5,416 at stage two. Those are timing records, not unique new obligations;
six fixed frame spec definitions are explicitly unlogged. Coverage is the
qualified default project scope, not every optional feature. Inherited trusted
code and warning profiles remain explicit. The two projects are inspected
development codebases, not held-out or representative production samples.

## Three questions for Nada

1. Does fixed-contract progressive growth capture the intended contribution,
   or should the next milestone include executable extensions or model-proposed APIs?
2. Which additional independent repositories or task types would make the
   evaluation convincing beyond these two selected chains?
3. After diagnosing the Dafny resource failures, should the next controlled
   comparison prioritize verifier/counterexample feedback, retrieval tools,
   or a fixed iterative repair budget?

**Takeaway to say aloud:** “We can now show two successive, fully checked model
proof additions on a real Vest repository, with actual parent reuse. The
Dafny attempts expose a semantic error and an unresolved proof/resource limit.
We have a working measurement pipeline and concrete results, with a narrow
feasibility claim and clear next experiments.”
