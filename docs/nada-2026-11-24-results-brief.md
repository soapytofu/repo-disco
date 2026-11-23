# November 24: real-source repository repair and growth

Reviewed November 23, 2026. **We now have 12 verified executable Dafny additions
forming six complete two-stage chains on selected real library components,
plus two complete Vest proof-extension chains.** The earlier Dafny-VMC growth
attempts still failed; their results are unchanged.

## Project overview and timeline

RepoDisco extends Formal Disco toward verified repositories with interacting
modules. The original question is how dependency depth, API reuse and shared
proofs affect whole-repository completion. Following Nada's feedback, we now
start from pinned online codebases and test successive additions that use an
actual accepted model-generated parent.

Weeks 1–4's initial baseline and repository-infrastructure milestones are
complete. Current work is corpus construction, controlled evaluation and
real-source growth. Broader independent-family evaluation, model/agent
comparisons and fine-tuning remain unfinished. These feasibility results do
not yet answer the causal structural research question.

## Main results to show

| Source and task chain | First addition | Second addition | Complete chains |
| --- | ---: | ---: | ---: |
| **Dafny Standard Library:** append a sequence → append its rotation | **3/3** | **3/3** | **3/3** |
| **AWS MPL UInt component:** read one length-prefixed field → read two fields | **3/3** | **3/3** | **3/3** |
| **Vest / Verus:** frame round-trip proof → counted-batch proof | **2/2** | **2/2** | **2/2** |
| **Dafny-VMC:** stable MoveToFront → ordered PickPair | **0/2** | Blocked; no calls | **0/2** |

The first two rows are a new **12-call collection**: four pilot additions passed,
then all eight declared expansion additions passed. Every response passed the
parser and edit guard and verified with zero errors or warnings. Twelve unique
request IDs, zero SDK retries, **102,737 tokens**, **4m27s on one CPU**. All six
children preserve and call their own accepted first addition.

The last two rows are the earlier separate six-response collection: four
accepted additions, two blocked children, 244,001 tokens and 1h10m26s. They are
not a controlled language comparison. Each row repeats one selected two-stage
task chain, not several independent task families.

[New Dafny collection and full logs](../experiments/dafny-real-library-growth-001/execution-001/COLLECTION.md),
[new source/request/native audit](../experiments/dafny-real-library-growth-001/execution-001/collection-review-001.json),
[earlier Vest/Dafny-VMC collection](../experiments/real-repository-growth-001/execution-005/COLLECTION.md).

## Concrete executable extension example

The host supplies the contract for `AppendAll`: append a sequence to the
upstream dynamic array while preserving validity, size, capacity and allocation
freshness. Claude produces a recursive body using the existing `a.Push` API;
the entire declared component verifies.

The next prompt includes that **actual accepted parent source**. Claude then
implements rotation by composing the new API twice:

```dafny
start := a.size;
Append.AppendAll(a, values[pivot..]);
Append.AppendAll(a, values[..pivot]);
end := a.size;
```

The fixed contract checks the final sequence and the exact appended interval.
Both new methods and all upstream obligations pass: 58 logged units at stage
one and 60 at stage two.
[Actual accepted parent and child](../experiments/dafny-real-library-growth-001/execution-001/retrieved-001/model-001/slots/slot-03/candidate/growth/).

The AWS children likewise call the accepted field reader twice, with 75/77
logged units passing at stages one/two. They also use a `reveal` directive, so
this is source-assisted API reuse, not evidence of opaque-contract-only reasoning.
Vest adds verified proof bodies rather than executable parser functionality.

## What the results establish—and their limits

- **Working progressive extension:** the harness accepts new executable Dafny
  bodies and Vest proof bodies, then uses the accepted source in a later request.
  Each stage has one response; there is no repair loop or post-response feedback.
- **Reliable acceptance checks on these scopes:** exact protected sources,
  complete native inventories and warnings are checked. A passing child cannot
  hide an unproved parent; omitted modules cannot count as full-scope success.
- **A calibration ceiling:** all three standard-library bodies at each stage
  repeat exactly. AWS variants differ in bytes but solve the same small tasks.
  The 12/12 result does not establish difficulty or broad generalization.
- **Explicit project boundaries:** each new Dafny scope contains three unchanged
  upstream files plus additions. The broader 102-file AWS baseline failed
  qualification and is preserved. These components share library ancestry;
  this is not full AWS MPL verification or a cryptographic security result.
- **Fixed specifications:** the host supplies contracts, APIs and edit boundaries.
  We have not tested unrestricted requirements/API discovery. Generated binaries
  were not benchmarked; verification time is not application runtime.

The earlier Dafny-VMC parents exhausted their fixed proof-resource limit while
all 267 upstream units passed. One has a concrete semantic counterexample:
`[0,1,2], k=2` yields `[1,2,0]` instead of `[2,0,1]`. The second remains unproved
at the fixed limit; it has no established counterexample. Those failures should
remain visible beside the new successes.

## Earlier repair evidence

| Study | Result | Meaning |
| --- | --- | --- |
| Real-source Dafny-VMC/Vest repair | **7/16 qualified accepts; 8/16 full-proof outputs** | Some constrained repairs succeed; parser/guard and proof outcomes must stay distinct. |
| Its feedback comparison | Diagnostics **3/8** vs notice **4/8** qualified; full-proof **4/8 each** | No demonstrated feedback advantage on those real-source sites. |
| Constructed-task repair | **27/32**, diagnostics **16/16** vs notice **11/16** | A separate selected development cohort, not a matched generalization comparison. |

[Real-source repair results](../experiments/real-repository-repair-pilot-001/execution-001/RESULTS.md)
and [separate parser/guard diagnostics](../experiments/real-repository-guard-diagnostic-001/RESULTS.md).
All original scores and stopped-run evidence are preserved.

## Three questions for Nada

1. Does this fixed-contract progressive-extension setup capture the contribution,
   or should the next milestone let the model propose new APIs/specifications?
2. Which harder, independent real-repository tasks would make the evaluation
   convincing beyond these repeated, selected component chains?
3. Should the next controlled experiment prioritize verifier/counterexample
   feedback on failures, source-retrieval tools, or an equal-budget repair loop?

**Takeaway:** “We can show verified successive executable additions on real
Dafny library components and successive proofs on Vest, using the model's own
accepted code. The pipeline works on these tasks; the next research question is
how far it generalizes and which feedback or tools help when it fails.”
