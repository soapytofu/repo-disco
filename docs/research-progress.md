# Research progress and next milestone

Status: October 28, 2026. Timeline source: Sophie Zeng's *HCRP Research Proposal F26*, “Time Frame” (page 5), with methodology on pages 2–4. Weeks below are proposal-relative; a calendar start date has not been established here.

| Proposal phase | Planned work | Current status / next action |
| --- | --- | --- |
| Weeks 1–2 | Set up Formal Disco and Dafny; reproduce baseline generation/evaluation; finalize repository representation and variables | Tooling, verified single-program generation, extension/repair pilots, and a 50-call format pilot are recorded. Published baseline evaluation is not reproduced. Finalize representation and metric definitions before claiming this phase complete. |
| Weeks 3–4 | Multi-module representation, repository-map/context infrastructure, whole-repository verification and repair; validate two-module repositories, begin scaling | **In progress:** multi-client fixtures, frozen edit guards, repository verification from real agenda snapshots, and immutable candidate preparation are validated. Automatic repository generation, context selection and transactional promotion/repair scheduling remain open. See the current evidence map below. |
| Weeks 5–6 | Controlled dependency depth, API reuse, shared proofs; matched baselines; primary synthetic corpus | Development families now cover composition, conditional preconditions and inductive helper synthesis. Composition pilots saturated; the latter two have verifier controls but no model trials. No frozen representative corpus or held-out family split yet. |
| Weeks 7–8 | Evaluate baseline model/agent configurations; construct training trajectories; fine-tune an open model | Requires a frozen task corpus and comparable evaluation budgets. Proposal targets four to five configurations where feasible. |
| Weeks 9–10 | Held-out evaluation of fine-tuned versus base model; robustness, quantitative and qualitative analysis; final report | Reserve held-out repository families before training-data construction. |

## Original implementation plan (retained for context)

The following was the initial implementation recommendation. The two-module fixture and repair milestones below are now complete; representation generalization and matched corpus work remain open. See dated progress entries for measured results.

1. **Freeze repository representation and measurement.** Define a manifest listing module/file IDs, imports/dependencies, exported APIs, specifications, reusable lemmas, and verification state. Record edits and verification output against an immutable source revision. Distinguish individual-specification success, module verification, and full-repository completion; do not substitute Dafny's aggregate verified-obligation count for a specification-level metric.
2. **Build a minimal verified two-module fixture.** Start with a lower-level arithmetic utility and an importing client that relies on its contract. Verify the complete repository through a defined entry point. Keep specifications fixed outside the worker's permitted edit scope.
3. **Create a controlled failure and demonstrate repair.** Introduce one implementation/proof failure whose effect reaches a dependent module. Give the worker local context plus the dependency/API map. Start with complete-file output for a bounded target file, informed by format-comparison-001; reverify the whole repository after every accepted edit. Preserve failed attempts, exact model context, and unaffected-module checks.
4. **Define a matched control before scaling.** Match module count, specification count, and approximate code size, while reducing cross-module dependence. Confirm the manifest and task generator can represent both structures. This establishes the design for Weeks 5–6 rather than prematurely claiming a controlled corpus.

### Acceptance criteria used for the initial milestone

- A small two-module repository verifies before mutation, with explicit dependency and API metadata.
- A documented mutation causes the intended verification failure.
- The repair loop records exact context, model response, edit validation, per-module diagnostics, whole-repository outcome, attempts, and token usage.
- The accepted repair preserves required specifications and unrelated code; a verified dependent client still checks the intended contract.
- A repeatable command reproduces verification from the archived sources, with pinned versions and no secrets.

The 50-call budget for format-comparison-001 is exhausted. Design, fixture implementation, and local verifier checks can proceed without additional paid model requests. The separately authorized two-module repair pilot used 1 of at most 5 Claude calls and stopped on first success. Four calls were not dispatched. This pilot is complete; define the next task and its budget before a new batch.

## Scope checkpoint for mentor discussion

Share the completed setup and repair-format evidence, and confirm the minimal repository task, controlled variables, and intended model/agent configurations with Nada. The central research question concerns dependency and shared-proof structure versus repository completion; additional single-file format trials should serve that goal rather than delay the two-module prototype. Fine-tuning remains a later milestone after there is a useful verified corpus and a defensible held-out split.

## Follow-up context task (October 21)

[context-pilot-001](../experiments/context-pilot-001/README.md) now supplies a verified opaque-function/helper-lemma fixture. All 12 expected control outcomes were confirmed on Cannon. Seven offline checks protect the proof boundary and confirm that the provider API appendix is the only prompt difference. The eight-call paired pilot completed October 22: API context 4/4 whole-repository passes, local-only 0/4. All local-only failures were guessed nonexistent helper names, not failed mathematical proofs. This tests exported-lemma information access on one designed task; broader dependency reasoning and matched controls remain future work.

## Three-task composition pilot (October 22)

[composition-pilot-001](../experiments/composition-pilot-001/README.md) builds range/precondition chaining, relation lifting, and sequence-property composition tasks. Both conditions receive complete source/contracts; one adds only a structural import map. Six offline checks passed. All 15 corrected verifier controls matched expectations on October 23 after fixing export aliases; the original failed run is preserved. The replacement 12-call pilot completed on shared with no requeue or SDK retries: full context 6/6 and full context plus map 6/6, with all protected source preserved. All proofs matched reference bodies ignoring whitespace. This ceiling result establishes basic composition on the three designed tasks, but supplies no evidence of a map advantage. The 12-call budget is exhausted. This work targets basic composition with known APIs rather than hidden-helper-name discovery.

## Preparation for controlled scaling (October 23)

The [matched-control design](controlled-corpus-design.md) separates import depth, intended proof-prerequisite depth, and observed call/reuse metrics. A [non-paid map audit](../experiments/map-audit-001/README.md) and reusable validator confirm that all three current maps have import depth two; they do not infer proof depth. Six graph validation tests passed. Next: build harder, matched verified fixtures and a versioned corpus manifest before requesting a new paid evaluation budget.

## Multi-client shared-proof validation (October 23)

[shared-proof-001](../experiments/shared-proof-001/README.md) adds two distinct client targets using one provider lemma. All 16 deterministic checks matched: both references pass, removing one client call affects only that client, and weakening the shared guarantee breaks both client postconditions while the provider still verifies. This validates shared-proof dependence for the designed fixture, not model reuse performance. Zero new model calls were made. A matched unshared control and more difficult compositions remain next steps.

## Matched reference-sharing control completed (October 23)

[sharing-control-001](../experiments/sharing-control-001/README.md) passed all 22 expected verifier outcomes on the authorized shared-partition rerun. Provider source and client specifications match across conditions; one same-length helper call name differs. Weakening the used shared helper breaks both fixed client proofs; weakening a separately used helper breaks only its client. Equivalent helpers remain available, so this validates reference dependency footprints rather than forcing different reasoning difficulty for a future model. No model calls were made; the preempted partial run is preserved.

## Reasoning-sensitive sharing controls

[sharing-reasoning-001](../experiments/sharing-reasoning-001/README.md) confirms 46 intended verifier outcomes: reference proofs pass; omitted steps, wrong arguments, and unavailable preconditions fail; hidden alternate helpers produce separately classified resolution errors. The batch reported failure because of a four-case diagnostic wording mismatch (raw 42/46); offline review with a corrected matcher confirms 46/46 without rerunning Dafny. Raw evidence is preserved. No model calls. This validates the fixture, not a model reasoning or sharing-performance claim.

## Eight-call sharing pilot preparation and completion

[sharing-model-pilot-001](../experiments/sharing-model-pilot-001/README.md) freezes eight proposed independent two-client trials (four shared, four separate), exact prompts and alternating order. Nine offline tests and 12 compute preflight checks pass; reference JSON repairs verify and both exact empty-proof inputs fail as expected. Full preflight logs are archived. The user later authorized eight calls; the bounded adapter completed exactly eight without retries. Both conditions had 0/4 accepted responses: all eight included prose before JSON and were rejected before verification. This is a format failure, not a proof-correctness result. Raw responses and the dispatch ledger are archived alongside the unchanged frozen plan.

## Depth × sharing pilot completed (October 25 Eastern)

[Eight-trial pilot](../experiments/sharing-depth-pilot-001/RESULTS.md): diamond shared 2/2, diamond separate 2/2, nested shared 2/2 and nested separate 2/2. All 24 verifier checks passed using the frozen tolerant parser, with protected source unchanged. Eight distinct requests, no retries, 15,843 total tokens. This is another ceiling result, not evidence of a sharing advantage. Current work remains Weeks 3–4 repository infrastructure and Weeks 5–6 controlled-corpus preparation; published-baseline reproduction, broader held-out evaluation and multi-model comparisons remain outstanding. Next non-paid work should introduce different proof obligations rather than only longer versions of this template.

## Conditional-contract family (verifier only)

[sharing-branching-001](../experiments/sharing-branching-001/README.md) adds sign-case reasoning for two client expressions, with matched shared/separate export views. All 34 controls pass their intended outcomes: six positive reference checks and 28 proof failures. Zero model calls. This diversifies proof structure beyond the saturated straight-line composition family; the separate branch-v1 guard now has seven offline tests and 12 semantic preflight passes. A future paid protocol still needs explicit freezing and authorization.

## Contract-ablation dependence measured

[Branch contract ablations](../experiments/branch-contract-ablation-001/README.md) completed 22/22 expected controls without model calls. Weakening either used shared guarantee breaks both fixed clients; weakening each separately used guarantee breaks only its client. Unused-helper controls remain valid. A per-condition sensitivity matrix links distinct targets to raw evidence; this is fixed-proof dependence, not a model sharing advantage.

## Inductive helper synthesis fixture validated

[Inductive sharing](../experiments/inductive-sharing-001/README.md) revision-003 passes 16/16 expected controls with zero model calls. Immutable clients depend on one shared or two duplicated sequence-sum helper proofs; automatic lemma induction is disabled. The two earlier failed revisions are preserved and classified. This is a new proof-synthesis family, not evidence of model difficulty; the separate provider-v1 guard now passes six offline tests and exact replay of 12 verified fixtures. Cross-helper delegation is disallowed by this guard and must be disclosed in future prompts.

## Current evidence map and coverage audit (October 26 UTC)

| Development family / integration | Measured evidence | Remaining limitation |
| --- | --- | --- |
| [Contract composition](../experiments/composition-pilot-001/README.md) | 15 verifier controls; full source 6/6 and source plus map 6/6 model successes | Three designed tasks, ceiling; no map benefit shown |
| [Depth × sharing](../experiments/sharing-depth-pilot-001/RESULTS.md) | Four cells each 2/2; 24 verifier passes | Two related Lift/Join shapes, repeated trials; not eight independent tasks |
| [Conditional contracts](../experiments/sharing-branching-001/README.md) | 34 controls, branch guard with 12 semantic checks | No model results; hand-developed family |
| [Inductive helper synthesis](../experiments/inductive-sharing-001/README.md) | Revision-003: 16 expected outcomes; provider guard validated | No model results; one versus two editable helper bodies changes workload/source size; copied proofs remain possible |
| [Multi-client metrics](../experiments/multiclient-metrics-001/README.md) | Distinct-target call usage and separately linked ablation dependence | Call reuse is not proof minimality or a causal model effect |
| [Agenda → repository verifier](../experiments/repository-backend-001/README.md) | Four expected real compute outcomes; source bytes/hashes retained | Explicit, quiescent snapshot only; no automatic context selection |
| [Guarded candidate → verifier](../experiments/repository-candidate-001/README.md) | Eight expected compute outcomes plus four contract rejections; original agenda objects unchanged | No candidate promotion, concurrency transaction or model repair worker |

All these inspected families belong to development. Renaming helpers or generating
more instances from them would not establish a new held-out family. Counts above
mix different types of evidence intentionally labeled in each row; do not sum
control checks, repeated requests and distinct tasks into a benchmark sample size.
The [offline extraction diagnostic](../experiments/sharing-extraction-diagnostic-001/README.md)
recovers proofs from the earlier strict-parser pilot; those post-hoc results do
not replace that pilot's original format failures.

## Baseline reproduction audit: concrete open gates

This is a local workflow/configuration audit, not a paper reproduction or a claim
that current upstream defaults exactly match the paper's experimental setup.

- The first RepoDisco pilot uses one custom seed, no sampled documentation, one
  attempt and an OpenAI model ([config](../config/repodisco_pilot.yaml)). It proves
  setup and generation, not reproduction of the discovery/evaluation baseline.
- The checked-in [discovery config](../config/scheduler/disco_opus.yaml) uses three
  workers and `data/gh-readmes-100k.jsonl`. That data directory is absent from this
  publishing checkout. Availability on other machines has not been audited here.
- The [monolithic config](../config/scheduler/monolithic_claude_opus.yaml) leaves
  its README source commented out, unlike discovery; token limits also differ in
  explicitness. An apples-to-apples new comparison needs resolved seed/context,
  token, call and repair budgets, not simply launching both defaults.
- The default [evaluation config](../config/eval.yaml) uses the
  [DafnyBench path](../config/data/dafnybench.yaml) and a
  [32-attempt fixer](../config/task/fixer.yaml). Dataset revision/content hashes,
  task selection, trivial-task filtering and budgets must be pinned first.
- Agenda `max_attempts` is not a universal API-request cap: the iterative worker
  can perform several repair requests within one unit of fuel. Reuse the bounded
  request ledger before any future paid baseline run; no such run is authorized
  by these non-paid audits.

### Bounded-adapter reuse audit

The [completed depth pilot adapter](../experiments/sharing-depth-pilot-001/dispatch.py)
is a fixed eight-request sequential dispatcher, not a drop-in model wrapper for
baseline workers. It durably records dispatch before transport, refuses an
existing output directory and stops on an ambiguous API error. Its live transport
sets SDK total attempts to one. Preserve this frozen implementation and its logs.

A future worker-compatible adapter must enforce a shared request budget at every
`invoke`, including internal repairs, while recording the actual dynamically
constructed prompt and task/attempt identity. It must latch closed after an
ambiguous transport error even if a worker catches the exception. Distributed
workers additionally need one coordinated reservation mechanism; independent
per-process counters cannot enforce a global cap. The existing fixed-batch tests
do not validate that future wrapper or concurrent dispatch.

The existing adapter checks its authorization deadline before starting the batch,
not at each request. Any future long-running worker adapter should check the
execution window before each dispatch. This observation does not invalidate the
completed pilot, whose recorded requests finished within its authorized window.
The monolithic worker also initializes its own unseeded `random.Random()` for
README sampling; the evaluation script's shuffle seed does not freeze that stream.
For a controlled new comparison, freeze explicit input order or separately seed
and record all sampling streams. No workers or provider clients were instantiated
during this source audit, and no live requests were made.

Next experimental decision: prioritize either a small frozen conditional/inductive
pilot to test whether the new obligations avoid the ceiling, or a precisely
specified baseline reproduction. Neither requires more near-duplicate fixture
variants now. Before training or broad evaluation, agree on family-level splits,
a matched model/agent comparison and a separately authorized request budget.

## Baseline preparation (October 28)

[Baseline reproduction preparation](../experiments/baseline-reproduction-001/README.md)
pins the public DafnyBench revision and all 1,567 source-file hashes, provides a
zero-model compute preflight and separates the Opus annotation evaluation from
open-ended generation reproduction. The paper reports 555 eligible annotation
problems: at most 2,220 calls for four attempts, with a proposed 20-call smoke
subset counted within that cap if settings remain unchanged. Neither stage is
authorized to make model calls yet. Exact paper problem IDs, source/tool versions
and evaluation inference settings still need confirmation. Three offline tests
pass; verifier-only preflight job 55802277 is queued. No paid baseline requests made.

## Weeks 1–4 completion gates (October 28 update)

The proposal asks for **a baseline generation/evaluation run**, not every paper
result. Earlier references to full published reproduction were too broad for this
milestone. A documented bounded baseline run can satisfy the initial requirement;
exact paper reproduction remains separately labeled.

| Gate | Current evidence / remaining work |
| --- | --- |
| Formal Disco/Dafny setup | Completed with saved generation, repair and verifier evidence |
| Baseline evaluation run | Dataset pinned; preflight 55802277 queued; tested 20-call runner prepared; no model results yet |
| Repository representation and variables | File manifest, declared dependency map, fixed contracts/edit scope, revision hashes, task/attempt identity and whole-repository outcome implemented; source remains authoritative for APIs/specifications; finish a consolidated protocol review |
| Multi-module context and verification | Previously validated; full source plus declared map is the initial policy, not automatic dependency selection |
| Whole-repository repair loop | New sequential engine preserves failed attempts, feeds back diagnostics and atomically promotes verified revisions; 28 offline tests pass; scripted real-Dafny control job 55802594 completed: 12 expected verifier outcomes, four contract rejections and intact original revisions |
| Live agent demonstration | Frozen four-task pilot prepared, up to eight calls; authorized as automatic continuation; requires successful controls |
| Begin scaling generation | Still open: schedule generation/extension across multiple repositories, rather than count hand-built controls as generated corpus |

New additive baseline request adapter has ten fake-transport tests; six smoke-runner
and three agent-adapter tests pass. Existing frozen protocols are unchanged. Neither
queued controls nor fake transport tests are model findings. All newly prepared
live settings and scope are documented in the respective experiment directories.

The user requested automatic continuation while asleep. The new combined driver
keeps one private key handoff in compute-process memory across the 20-call
baseline and at-most-eight-call agent pilot. Four orchestration tests pass;
agent controls are complete and reviewed; baseline preflight is running. No additional generation budget inferred.
