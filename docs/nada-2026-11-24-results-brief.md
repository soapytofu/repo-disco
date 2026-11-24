# November 24: real-source repository repair and growth

Reviewed November 24, 2026. **We have 12 verified executable Dafny additions
forming six two-stage chains, plus two Vest proof-extension chains. The fresh,
more varied balanced pilot accepted 3/8 additions and exposes API-visibility,
ghost/executable-boundary and solver-budget failures.** The earlier partial
pilot and failed Dafny-VMC growth attempts remain unchanged. The system can
extend selected real components, but its reliability on varied tasks is limited.

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

## Latest varied-task pilot: complete balanced sample

| Task | Accepted / responses | Failure or success evidence |
| --- | ---: | --- |
| Stable filtering | **0/2** | Both access the hidden `DynamicArray.data` field |
| Counted frame decoder | **1/2** | One passes all 81 units; one exhausts the fixed solver budget |
| Generic splice | **0/2** | Both pass ghost-derived sequences to executable code |
| Tagged/bounded frame pair | **2/2** | Both pass all 79 units, including 77 inherited |
| **Total** | **3/8** | **Four frontend failures; one resource failure** |

Eight fresh independent responses, eight unique request IDs, zero SDK retries,
**73,890 tokens**, **4m25s on one CPU**. Every response passed extraction and
the edit guard; only the three clean full-scope native successes were accepted.
No repair loop or extra feedback was used. The resource-limited decoder is
unproved, not established mathematically wrong. All three accepted additions
reuse saved generated APIs and also reveal definitions, so this is
source-assisted composition.

**Design change:** before this fresh cohort we tested and froze a policy that
records fully captured candidate frontend errors as failed trials and continues
independent collection. Same exact prompts, model settings, edit rules and
native proof limits; 113 tests passed before execution. Integrity failures,
provider ambiguity and unresolved execution still stop the runner. The
[550-file archive and review](../experiments/dafny-real-library-growth-002/execution-002/COLLECTION.md)
confirm all eight were evaluated. The change improves measurement completeness;
it does not make the failed outputs correct.

This contrasts with the earlier simpler 12/12 feasibility result, but tasks
and cohorts differ: it is not a matched causal difficulty comparison. A useful
next question is whether API/export-aware context and verifier feedback help
these observed failures under an equal budget.

## Earlier varied-task pilot: partial, preserved separately

| Task | Observed result |
| --- | --- |
| Stable filtering | 0/1 accepted; a loop invariant is false at entry for any nonempty input |
| Counted frame decoder | **1/1 accepted; all 81 units pass**, including 77 inherited |
| Generic splice | 0/1 accepted; directly accesses an unexported `data` field |
| Tagged/bounded pair | Unobserved |

All three responses passed JSON extraction and the edit guard. The frozen rule
to stop on frontend errors closed five undispatched slots after the splice
failure. **This is one accepted addition among three observed responses, not a
completed balanced eight-trial result.** There were zero SDK retries and
25,719 tokens. All sources and diagnostics are preserved.

The decoder reuses the actual saved `ReadU16Frame` and recursively handles an
arbitrary requested count, proving exact payload order, re-encoding and suffix
preservation. It also reveals the parent definition. The filter failure is a
bad proof annotation, not an established wrong-output example. The splice
failure shows that seeing implementation source did not make the model respect
the exported API. The harness correctly rejected both failed candidates.

That stopping policy motivated the prospective runner change used in the fresh
cohort above. This earlier run remains closed and unchanged, and its three
responses are not pooled into the new eight-trial score.
[Original results and full audit](../experiments/dafny-real-library-growth-002/execution-001/COLLECTION.md).

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
accepted code. The fresh balanced varied-task pilot accepted only 3/8: it
reveals concrete API-boundary, ghost/executable and resource limitations. The
pipeline rejects those failures. Next I want to test whether targeted feedback
or tools improve them under a controlled budget.”
