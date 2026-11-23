# Research assessment for the November 24 meeting

Independent evidence review, November 22, 2026 (Eastern). This assessment uses
saved source-bound results; it launches no tests, model calls or verifier runs.

**Recommendation:** prioritize an audited sequential-growth result on the two
qualified real seeds before expanding the corpus or claiming broader agent
ability. The existing repair results are tangible. The original repair protocol
also had a substantial admission bottleneck. The current extender's ability to
grow a repository through successive accepted additions remains unmeasured.

## What the evidence supports

| Evidence | Observation | Supported conclusion |
| --- | --- | --- |
| [Original real-source repair pilot](../experiments/real-repository-repair-pilot-001/execution-001/RESULTS.md) | 7/16 qualified accepts; 8/16 complete-proof outputs; 7 guard rejections; 1 native type error. | Constrained repairs can succeed at existing Dafny-VMC and Vest sites. The primary end-to-end score remains 7/16; the overlapping pass columns must not be added. |
| Same pilot, feedback arms | Diagnostics 3/8 versus notice 4/8 qualified accepts; complete-proof outputs 4/8 in each arm. | This real-source pilot shows no feedback advantage. Admission and an operational warning confound the acceptance difference. |
| [Separate syntax diagnostic](../experiments/real-repository-guard-diagnostic-001/RESULTS.md) | Seven excluded outputs, unchanged, form three distinct candidates: one qualified pass, one full-proof result with an added cleanup warning, one resource-limited result. | The guard rejected legitimate language syntax. These are three native observations, not seven independent new trials or a revised original model score. |
| [Fixed-source resource study](../experiments/real-repository-evaluation-stability-001/RESULTS.md) | Saved Swap candidate: 265/267 units at 20k, 267/267 at 100k. Upstream passes at both. One downstream lemma uses about 15.5 times the upstream resource count in the passing candidate run. | A local transparent implementation can change downstream proof cost while declared contracts remain fixed. This is a concrete cross-module phenomenon, not a general depth effect. |
| [Growth controls](../experiments/real-repository-growth-001/controls-001/RESULTS.md) | 25/25 expected outcomes: 8 passing scopes, 14 intended proof failures, 3 coverage rejections. | The two task chains are feasible and the harness rejects omitted additions and locally passing children with unproved parents. These are analyst controls. |
| [Stopped growth run](../experiments/real-repository-growth-001/execution-001/retrieved-001/model-001/summary.json) | Job 62928981: one reserved request, zero returned responses, zero native invocations, `NoCredentialsError`; ledger closed. | Execution failed before producing evaluable model output. This is **not 0/8 model success or 0/4 lineage completion**. Seven slots remain undispatched and cannot be reassigned. |

The clearest model success to show Nada is the accepted Vest Pair repair: the
model applied the child theorem to the actual intermediate `serialized1`
buffer, then established length/remainder facts using existing APIs. The
[complete accepted source](../experiments/real-repository-repair-pilot-001/execution-001/model-001/slot-09/candidate.txt)
is stronger evidence than an isolated edited line. The starting defect was
deliberately induced, not a newly discovered upstream bug.

## Is the setup performing badly on real repositories?

The original **end-to-end repair protocol lost seven of sixteen outputs at its
own guard**, so its practical completion rate had an avoidable interface problem.
That is a reason to improve and prospectively validate the evaluation system.
It is not evidence of seven failed mathematical arguments. The later native
diagnostics distinguish legitimate syntax, solver-resource exhaustion and an
operational Cargo warning. The admitted Vest type error is a model-side failure
to respect the fixed trait's available capabilities. Conversely, computing
8/9 proof completion only among admitted candidates would select a favorable
subset and would not estimate overall model performance.

Comparing this 7/16 with the [earlier constructed-task repair result of 27/32](../experiments/repair-diversity-pilot-002/RESULTS.md)
does not measure a clean real-world generalization drop. The cohorts differ in tasks, language/toolchain,
edit policy, context selection, warning/resource rules and task selection.
Repeated responses are clustered within four sites from two inspected projects.
Public-code pretraining exposure is unknown. Neither cohort is a held-out sample,
and Dafny-versus-Verus totals are not a controlled language comparison.

The latest execution failure exposes an integration gap despite passing fake
tests. A [separate exact-SDK offline diagnostic](../experiments/real-repository-growth-001/credential-diagnostic-001/README.md)
now reproduces the token-lifetime bug and checks corrected handling with all
network connections blocked. This provides no evidence about model reasoning.
Preserve the terminal run
and require a separately reviewed execution decision rather than automatically
reopening its ledger.

## Design choices worth defending precisely

- **Fixed contracts and protected bodies** keep the requested behavior constant
  and prohibit weakening a specification to obtain a pass. This measures
  contract-guided implementation/proof completion, not discovery of requirements
  or reusable abstractions. There is one response per stage, not an iterative
  verifier-feedback agent.
- **Full declared scope** is essential: the native controls actually show a
  passing caller alongside a failed provider and clean exits with omitted
  required targets. Hashing source files alone is insufficient.
- **Actual accepted parents** distinguish sequential growth from independent
  completion against analyst references. A second stage may still implement a
  valid direct solution. Observed parent-API use and verification success are
  separate outcomes; neither establishes necessary proof dependence.
- **Curated model context and broader native verification** are explicit design
  choices. Selected existing upstream files are legitimate context, but omitted
  transitive context can affect performance. No retrieval-method evaluation has
  been performed.

“Full scope” has limits. The [baseline qualification](../experiments/real-repository-qualification-001/RESULTS.md)
checks 28 declared Dafny inputs and 267 mapped units across 26 files, not all 91
staged upstream files as separate verified units. Existing `{:verify false}`
bodies, axioms, extern declarations and termination exemptions remain trusted.
Vest covers default-feature `vest_dev` with `vest_lib` and `vstd`, not every
workspace crate or optional feature; existing external proof bodies remain
trusted. Its 5,410 original timed occurrences are not 5,410 unique logical
obligations. Growth additionally preserves six explicitly unlogged frame spec
definitions. The [trust inventory](../experiments/real-repository-qualification-001/trust-inventory.json)
is a lexical review aid, not a soundness certificate.

Vest growth is a specification/proof-library extension, **not executable parser
generation**. Both projects are real research/library codebases, not a
representative production-software benchmark.

## When to reevaluate after a future valid growth collection

These are qualitative decision rules for the small pilot, not significance
thresholds or permission to alter a frozen cohort after seeing results.

| Observed pattern | Reevaluate | Avoid concluding |
| --- | --- | --- |
| Legitimate source is again rejected by the guard | Language-specific admission and output instructions; preserve old outcomes and version any correction. | That the rejected output is mathematically wrong. |
| Admitted bodies consistently use unavailable APIs or wrong types | Whether the fixed prompt exposes the relevant contracts/bounds; then consider a controlled context/tool intervention. | That merely adding tokens or analyst hints demonstrates a general agent improvement. |
| Ordinary proof failures persist with adequate context and verified controls | The limits of the one-shot completion design; inspect missing facts, instantiations and induction before selecting a feedback/tool comparison. | That repeated hidden retries establish reliable extension. |
| First additions pass but second additions fail | Composition and parent-context handling, with exact failure sites. | A causal dependency-depth effect: the stages differ in task content and successful-parent selection. |
| Complete chains pass but bypass the parent API | Task alignment with Nada's reuse question. Report verified growth and absent observed reuse separately. | That required cross-module reuse has been demonstrated. |
| Resource exhaustion, warnings or execution failures dominate | Evaluation budgets, classification or integration, separately from the model. | Model proof failure, or permission to adaptively relax the original score. |
| A missing module or unproved provider is ever accepted | Stop performance claims and audit coverage/integrity before further collection. | That the affected success rate remains trustworthy. |
| All small-pilot chains succeed | Broader independent task/project coverage and ceiling effects. | Broad capability, generalization or training-data readiness from two task chains. |

For a valid collection, report each planned lineage, stage outcome, exact parent,
coverage, actual API use and cost. Conditional second-stage rates must state
their successful-parent denominator. Blocked children are undispatched; an
infrastructure-stopped cohort is incomplete. Do not pool repair and growth
scores or retrofit the new policy into historical results.

## Research priority for the meeting

First obtain and audit model growth evidence under a reliable, fixed execution
path. Then choose the next intervention from the observed failure category,
rather than building more tasks merely to find a success. Broader project
coverage and a defensible family split should precede generalization or
fine-tuning claims. If collection remains blocked, present the real repair and
resource findings and state plainly that sequential growth is still unmeasured.

The useful question for Nada is whether **contract-guided progressive growth**
is the intended contribution, and whether proof-library growth is sufficient
for Vest. Her answer should guide the next task class and tool/baseline
comparison; the current evidence does not justify claiming an autonomous
general repository extender.
