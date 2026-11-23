# November 24 meeting: real-repository repair and growth

Evidence checkpoint: November 23, 2026, Eastern. **Real-source repair results
are available. The first returned growth candidate is incorrect; the growth
cohort stopped before a complete lineage evaluation.** Job **63018923** returned
one admitted Dafny MoveToFront body, with one unique request ID, zero SDK retries
and 2,290 tokens. Its native check preserves all 267 upstream passes but exhausts
the new function's resource budget. A concrete input also demonstrates that its
output order violates the fixed specification.

The frozen runner stops on every verifier resource failure. Seven slots were
therefore undispatched; **0/1 observed additions were accepted**, with no full
8-slot or 4-lineage score. Vest and all second-stage tasks remain unattempted.
[Full evidence and counterexample](../experiments/real-repository-growth-001/execution-004/COLLECTION.md)
are saved. Earlier credential/access failures had no returned responses and
remain separate closed records. The latest invocation establishes working
access for that request only.

Sophie approved a total ceiling of **100 new calls**, with confirmation before
exceeding it. Eight are allocated, one used and seven unused in the closed
allocation; **92 remain unallocated**. The [budget snapshot](../experiments/real-repository-growth-001/research-budget-20261123-002.json)
records this. Next is a separately qualified policy that records complete,
source-bound resource failures as unaccepted and blocks their children while
continuing independent lineages. Missing evidence, process timeouts, integrity
or provider failures remain terminal; prompts and proof acceptance stay fixed.

## Main message

We moved from constructed Dafny tasks to pinned source from **Dafny-VMC and
Vest**, a Verus project. The system can make constrained repairs that preserve
contracts and pass the full declared verification scope. The next experiment
tests Nada's suggestion directly: start with a real repository, accept a new
verified addition, and extend that exact accepted revision again.

These are two research/library codebases, not a representative sample of
production software. They are inspected development projects, not held-out
families. The current extender is a controlled generation-and-verification
pipeline with one response per stage; it is not an unrestricted autonomous
repair agent.

## Results already available

| Evidence | Result | Defensible interpretation |
| --- | --- | --- |
| Original real-source repair pilot | **7/16 qualified accepts; 8/16 complete-proof outputs**. Seven guard rejections and one native type error. | Successful repairs on existing Dafny and Verus source. The two pass columns overlap. The primary result remains 7/16. |
| Feedback comparison within that pilot | Diagnostics **3/8** qualified accepts versus notice **4/8**; full-proof passes **4/8 in each arm**. | No demonstrated feedback advantage on these four task sites; guard admission and an operational warning affect the result. |
| Separate guard diagnostic | Seven saved rejected outputs admitted without body edits; three distinct candidate files checked. | The original exclusions were evaluation-interface problems, not seven established mathematical failures. Outcomes are reported separately, not used to rescore the original pilot. |
| Fixed-source verification-resource study | Saved Swap candidate **265/267** units at 20k; **267/267** at 100k. Upstream **267/267** at both limits. | A locally valid transparent implementation can raise downstream proof cost under unchanged contracts. This is one candidate, not a general structural effect. |
| Growth-task native controls | **25/25 expected outcomes:** 8 passing scopes, 14 intended proof failures, 3 missing-coverage rejections. | The new tasks are feasible and the harness rejects important false-success cases. These are analyst controls, not model-generated extensions. |
| Current growth runner preparation | **98/98 tests locally and on Cannon plus 5 intercepted-SDK scenarios**; frozen prompts/order unchanged. | Request accounting, parent preservation, SDK lifetime and redacted failure evidence are tested. These tests are not additional native proofs or model results. |
| First returned growth candidate | **0/1 observed accepts**, 267/267 upstream passes, new target out of resource; concrete order counterexample. Seven slots unattempted. | One incorrect model extension; incomplete cohort, not a 0/8 or 0/4 score. Earlier access failures remain separate. |

Source reports: [repair results](../experiments/real-repository-repair-pilot-001/execution-001/RESULTS.md),
[guard diagnostic](../experiments/real-repository-guard-diagnostic-001/RESULTS.md),
[resource study](../experiments/real-repository-evaluation-stability-001/RESULTS.md),
[growth controls](../experiments/real-repository-growth-001/controls-001/RESULTS.md),
[current runner preparation](../experiments/real-repository-growth-001/execution-004/RESULTS.md),
[first stopped execution](../experiments/real-repository-growth-001/execution-001/RESULTS.md),
[earlier access-denied execution](../experiments/real-repository-growth-001/execution-003/RESULTS.md).

Original repair results by site:

| Site | Qualified accepts / returned responses | Full-proof outputs / returned responses |
| --- | ---: | ---: |
| Dafny-VMC sequence swap | 0/4 | 0/4 |
| Dafny-VMC small shuffle | 3/4 | 3/4 |
| Vest blanket roundtrip | 3/4 | 4/4 |
| Vest Pair roundtrip | 1/4 | 1/4 |

The swap row records four **guard rejections before verification**, not four
native proof failures. Later guard/resource diagnostics are separate evidence.
One full-proof Vest result was excluded by the original policy because of a
Cargo cleanup warning. All sixteen requests had unique IDs and zero SDK retries.

## One concrete cross-module example to show

In the accepted Vest Pair repair, the first component was serialized using an
intermediate buffer, but the starting proof applied its roundtrip theorem to
the original buffer. The model aligned the theorem call with the actual state:

```rust
// Induced starting proof
self.0.theorem_serialize_dps_parse_roundtrip(v.0, obuf);

// Accepted model repair
self.0.theorem_serialize_dps_parse_roundtrip(v.0, serialized1);
```

This is an excerpt, not the entire repair or a minimality claim. The accepted
body also establishes the relevant length and remainder facts. It connects
Pair's specifications with child-format theorems and core trait contracts while
leaving signatures and other source fixed. Show the
[actual candidate](../experiments/real-repository-repair-pilot-001/execution-001/model-001/slot-09/candidate.txt)
and its [native observation](../experiments/real-repository-repair-pilot-001/execution-001/verification-vest-001/slot-09/observation.json)
if asked. The starting failure was deliberately introduced; it was not a newly
discovered upstream bug.

## The frozen extension experiment

| Real seed | First addition | Second addition, only after its parent passes |
| --- | --- | --- |
| Dafny-VMC | Stable MoveToFront, preserving order of the remaining elements, length and multiset | Ordered PickPair from two original indices, with the actual accepted MoveToFront source protected |
| Vest | U16-length frame roundtrip proof with exact consumption and suffix preservation | Recursive counted-batch proof over the actual accepted frame API |

Two independent lineages per repository, at most two stages each: **eight calls
maximum**, one fresh response per stage, no retries or reassignment. Model and
settings are fixed by the [pilot freeze](../experiments/real-repository-growth-001/pilot/README.md).
The model is Claude Opus 4.5 through Bedrock; this pilot has no iterative feedback
repair loop. Vest adds a specification/proof library, not executable parser
generation. A successful direct second-stage proof is admissible; actual calls
to the first-stage API are recorded separately.

Report the four prespecified lineages individually: first-stage outcome,
second-stage outcome or blocked reason, source/parent hashes, complete proof
coverage, observed API use, model tokens and native time/resources. Report both
stage acceptance among returned responses and completion of both additions per
lineage. A blocked child is undispatched, not a failed model response. If an
infrastructure error stops collection, show the partial cohort and unattempted
slots; do not fabricate a complete eight-call score.

The primary numerical result will be completed two-addition lineages, separated
as **Dafny-VMC /2** and **Vest /2**, and **/4 overall** only for a fully accounted
cohort without an unresolved infrastructure stop. Secondary counts will show
first-stage acceptance among its returned responses, second-stage acceptance
among responses with an accepted parent, and observed parent-API calls among
completed children. Report guard/type/proof/resource/operational outcomes and
undispatched children separately, plus total input/output tokens and native time.
Those denominators are fixed before seeing the model outputs. Two repetitions
per project remain descriptive feasibility evidence, not independent task families.

The full-scope success rule checks old code as well as each addition. Dafny uses
28 explicit upstream inputs and 267 original named units, plus registered new
targets. Vest verifies the qualified default vest_dev/vest_lib/vstd scope and
preserves the 5,410 original timed occurrences with their multiplicities; native
crate totals are a separate measure. Neither claim means every optional feature
or file in the upstream Git repository is verified. Existing trust assumptions
and unlogged specification definitions remain explicit.

## Design choices and how to defend them

| Choice | Reason | Limit to acknowledge |
| --- | --- | --- |
| Start from pinned real repositories | Test existing APIs, language syntax, dependencies and verification tooling beyond constructed snippets. | Two selected projects and public-code exposure limit generalization. |
| Host fixes contracts; model changes declared bodies | Keep the requested behavior measurable and prevent weakening the task to obtain a pass. | Tests contract-guided implementation/proof completion, not discovery of requirements or abstractions. |
| Preserve and verify the old scope | Local proof success can conceal a failed helper or missing module. Coverage controls exercise both cases. | Coverage is the explicitly declared scope under inherited trust assumptions. |
| Child uses the actual accepted parent | Establish a real growing trajectory rather than replacing the parent with an analyst solution. | A call to the parent API is evidence of use, not proof that every valid solution needs it. |
| Curated source context, full-scope verification | Give complete selected APIs within a bounded prompt while checking all required dependencies afterward. | This context policy may affect performance; it is not an evaluated retrieval method. |
| One response per stage, fixed order and no retries | Obtain interpretable initial feasibility with auditable cost and no hidden repair budget. | This is not the best attainable performance of a tool-using agent. |
| Separate guard, type, proof, warning and resource outcomes | Avoid treating infrastructure or admission problems as mathematical reasoning failures. | The original evaluation policy remains part of the original result; later improvements are versioned. |
| One CPU for the qualified serial execution | Matches the measured workload and addresses the cluster allocation warning. | Runtime remains toolchain-, source- and machine-dependent. |

## What should be ready by Tuesday afternoon

1. Audited growth results with every attempted/blocked stage accounted for and
   full responses, source lineage and native logs on GitHub.
2. One inspected extension trajectory or failure case per project, including
   whether the second addition actually uses its accepted parent API.
3. This compact results table and a clear separation between measured repair,
   analyst feasibility controls and newly measured extension performance.

These growth deliverables depend on a successful, audited fresh collection;
the eight-call allocation is now approved, while job 62950853 remains terminal
and fully reviewed. Its seven
unused slots and the older scope remain closed. If access is unresolved by the
meeting, present the existing repair results, downstream proof-cost example
and coverage controls, and say plainly that model-generated growth was not
measured. An access failure does not answer whether the extender can solve the
tasks; do not replace that missing result with analyst references or retries.

The 100-call ceiling is not a target. Further batches should answer a specific
question raised by the evidence, with their tasks, comparison and budget fixed
before dispatch. Retain unsuccessful cohorts; do not keep sampling the same
tasks until the displayed success rate improves.

The [independent research assessment](nada-research-assessment-2026-11-24.md)
sets out when to revise the guard, context, one-shot design or task choice based
on actual failure categories, rather than repeatedly sampling until success.

Questions for Nada:

1. Should the main contribution now be progressive contract-guided growth on
   real repositories, with verifier-guided repair as a later tool ablation?
2. Which additional independent projects or task types would best challenge the
   limitations of these two selected seeds?
3. For the next comparison, should we prioritize richer verifier/counterexample
   feedback, retrieval tools, or an iterative repair budget—and which baseline
   would make that comparison most informative?
