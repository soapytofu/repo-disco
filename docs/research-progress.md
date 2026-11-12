# Research progress and next milestone

Status: November 12, 2026 (Eastern). Timeline source: Sophie Zeng's *HCRP Research Proposal F26*, “Time Frame” (page 5), with methodology on pages 2–4. Weeks below are proposal-relative; a calendar start date has not been established here.

| Proposal phase | Planned work | Current status / next action |
| --- | --- | --- |
| Weeks 1–2 | Set up Formal Disco and Dafny; reproduce baseline generation/evaluation; finalize repository representation and variables | **Initial milestone complete:** setup, bounded 20-call baseline evaluation, and consolidated representation/variable protocol. Full paper reproduction remains a separate claim. |
| Weeks 3–4 | Multi-module representation, repository-map/context infrastructure, whole-repository verification and repair; validate two-module repositories, begin scaling | **Initial milestone complete:** multi-module context/verification/repair validated; four live repository repairs and four verified new-client extensions across two seeds. Full-source context is fixed; broad/open-ended generation remains later work. |
| Weeks 5–6 | Controlled dependency depth, API reuse, shared proofs; matched baselines; primary synthetic corpus | Six of 12 development instances are now implemented and verified: four C1 cases plus fresh move and restriction/merge. C1 calibration remains 27/32 strict passes; the two new map tasks matched all 76 verifier-control expectations with no model calls. Target-level logging is validated separately. The first map cohort stopped after ten dispatches; the subsequent fresh sixteen-call cohort is complete: fresh move 8/8, restriction/merge 4/8, all outputs admitted. Remaining development and reserved-family evaluation are still unapproved. |
| Weeks 7–8 | Evaluate baseline model/agent configurations; construct training trajectories; fine-tune an open model | Requires a frozen task corpus and comparable evaluation budgets. Proposal targets four to five configurations where feasible. |
| Weeks 9–10 | Held-out evaluation of fine-tuned versus base model; robustness, quantitative and qualitative analysis; final report | Reserve held-out repository families before training-data construction. |

## November 12: fresh balanced map pilot completed — 12/16

[map-development-pilot-002](../experiments/map-development-pilot-002/RESULTS.md)
completed job 60073401 in 4m05s: sixteen unique responses, zero retries, twelve
strict passes and four precondition failures; all outputs were admitted.
Fresh move passed 8/8. Restriction/merge passed all four shallow responses and
failed all four deep responses, each requesting the restricted-map certificate
before its prerequisite key-set facts. Shared and separate each scored 6/8
across the two tasks; no general sharing advantage is established. Seven
separate body pairs are exact copies and the eighth differs only by a binder
rename. Failed workspaces have zero dependency-closed clients despite local
client passes against unproved helper contracts. Full 819-file transfer evidence,
812 model-file digests, 120 protected-file and 24 body-boundary comparisons are
reviewed; all original 646 model files remain unchanged. Usage: 70,333 tokens.
The sixteen-call budget is exhausted. Six of twelve development instances are
implemented; remaining development collection and reserved-family lineage/
evaluation gates remain open. This result does not certify held-out performance,
minimum proof depth or a causal syntax/depth/sharing effect.

## November 12: fresh balanced map pilot frozen — no new calls

[map-development-plan-002](../experiments/map-development-plan-002/README.md)
proposes **16 new requests**: two map instances × four structural cells × two
fresh responses. Eight exact payloads, sixteen fresh trial IDs, balanced relative
cell positions and all settings are frozen. Instructions explicitly require one
`ensures` per `forall` proof statement and `&&` for multiple conditions; task
sources, parser, metrics and semantic context are unchanged. Eleven offline test
methods pass, including a syntax-only delta audit and all nine saved-response
replays; all 646 old archive files are preserved. No old slots are reassigned,
no new calls are authorized, and no live runner is prepared. This is development
calibration, not held-out evaluation or a causal prompt-effect experiment. With
other corpus stages unchanged, the attempted-request forecast is now 154,
including ten prior interrupted dispatches; this is not a new budget approval.

## November 12: map development collection interrupted; mechanism evidence saved

The subsequently approved [16-call follow-up](../experiments/map-development-pilot-001/RESULTS.md)
stopped on a service-unavailable error at dispatch 10, with no retry. Nine unique
responses returned: six strict passes, two precondition failures and one policy
rejection. Six slots remain undispatched. Fresh move is 4/4 among returned cells;
restriction/merge is 2/5, with deep proofs requesting a restricted-domain
certificate before supplying its key-set facts. The incomplete cohort cannot
supply a completed balanced rate or general causal comparison. All raw logs and
fixed-contract audits are preserved. No partial editable-helper success was
observed; supplied-client local verification is explicitly excluded from model
credit. A separate verifier-only diagnostic examines the ordering issue (completed below).

That [four-case diagnostic](../experiments/map-order-diagnostic-001/RESULTS.md)
is now complete: job 60066865 matched all four expectations in 24 seconds.
Moving only the existing certificate call after both restriction-key facts makes
three analyst candidates strictly verify 20 obligations with no warnings. The
unchanged policy-rejected response also fails that certificate precondition:
it has a grammar-policy issue and a proof-ordering issue. All 646 original model
archive files remain unchanged. This confirms a concrete cross-module
prerequisite-ordering mechanism, not a model improvement or general depth/sharing
effect. Four offline tests passed locally and on Cannon; zero new model calls.

## November 12: two map collection tasks and target-level measurement verified

[Fresh-key move composition](../experiments/development-moves-001/RESULTS.md)
and [restriction over disjoint merge](../experiments/development-restriction-001/RESULTS.md)
each match 38/38 expected controls: four strict reference passes, 30 proof
failures and four hidden-export failures. All eight current references have zero
warnings. The restriction fixture's initial finite-comprehension frontend failure
is preserved; revision 002 changes only the equivalent explicit domain bound.
No original model score changes and no new model calls were made.

The [named-target diagnostic](../experiments/target-completion-diagnostic-001/RESULTS.md)
also completes five compute checks. Analyst partial repairs demonstrate that a
supplied client can verify locally against an unproved helper contract. It reports
editable helper completion, dependency-closed client completion and strict whole
completion separately. This validates a measurement method, not a model performance
effect. Eight move design tests, nine restriction revision tests, four runtime
tests per measurement collector and six interpretation tests passed.

Both new operations stay in the map development ancestry group. Separate mode
still permits copying two equivalent helper bodies, and interface factorization
does not establish necessary proof depth. A future bounded follow-up can test
whether missing value/domain facts recur across these operations, using the
separately versioned quantified-assertion policy and target-level logging. It
needs a frozen scope and new paid approval. The other six M1/M2 instances and
both reserved families remain unimplemented; reserved test solutions were not
developed during this work.

The [prospective 16-call map plan](../experiments/map-development-plan-001/README.md)
now freezes both instances × four structural cells × two fresh samples. Seven
offline tests pass, including exact regeneration and target-scope checks. These
would be the first 16 of the proposed 64 development-collection calls. None is
authorized or dispatched at the proposal freeze. The [bounded runtime](../experiments/map-development-pilot-001/README.md)
now passes 19 fake-transport/verifier tests and Cannon's offline environment
preflight. Subsequent explicit approval and execution are recorded in the entry
above; this historical proposal freeze and earlier model scores remain unchanged.

## November 10: varied calibration model pilot completed

[varied-calibration-pilot-001](../experiments/varied-calibration-pilot-001/RESULTS.md) completed all 32 approved requests on job 59517240 in 6m14s: 32 unique provider IDs, zero SDK retries, 119,194 tokens. Allocation, clamp distance and prefix splitting each scored 8/8; map swap scored 3/8. Four deep map responses repeat a proof that lacks the other swapped-key instantiation and fail a quantified postcondition. One shallow map response uses a quantified assertion outside the frozen body grammar; it was not verified. All 32 JSON envelopes extracted, 31 bodies admitted. Exact-source audits preserve 233 protected files and 46 body boundaries; all 16 separate responses copy identical helper bodies. This is development calibration, not a causal sharing/depth or held-out result. No budget remains. Next: separately diagnose the policy mismatch and map instantiation issue offline, then build distinct M1/M2 collection instances and review family lineage before any new paid scope.

The subsequent [separate diagnostic](../experiments/map-swap-diagnostic-001/README.md) now confirms both issues with zero model calls. Two missing original-map observations suffice for shared and separate repairs; either single observation alone leaves the tested shared proof unproved. The original policy-rejected proof verifies unchanged under a separate scoped quantifier-expression guard. All three positive diagnostics strictly verify 14 obligations with no warnings. A false quantified assertion fails as intended after correcting an analyst-created reserved-keyword binder; both the initial parse error and the corrected proof failure/trigger warning are preserved. Seven local tests and three correction tests also pass on Cannon, including all 32 saved-response and 126 fixture-control replays. All 1,846 original pilot files and score 27/32 remain unchanged. Next: review this policy for a future frozen protocol, and build distinct M1/M2 instances rather than counting diagnostics as model improvement; reserved families remain outside tuning.

## November 9: four calibration tasks verified

[varied-calibration-001](../experiments/varied-calibration-001/RESULTS.md) validates D3-C1 bounded allocation, D4-C1 map swap, D1-C1 clamp distance and D2-C1 prefix splitting across 16 workspaces. All 126 current controls matched: 16 strict reference passes, 90 proof failures, four termination failures and 16 hidden-export failures, with no parse errors or warnings. Revision 002 adds a necessary domain certificate to the chosen deep map reference interface; it does not establish minimum proof depth. Three jobs and all earlier sources/results are preserved. Current evidence reuses 24 unchanged original observations and includes eight revised map checks plus 94 targeted negatives. Nine construction/runtime and eight output-compatibility tests passed; protected bytes and exact parser reconstruction are audited. Per-family reference paths, recursive depth limits, shared forwarding and doubled separate output workload are explicit. No model calls; reserved test families remain untouched. Sixteen analyst alternative proofs subsequently passed on job 59355663 with unchanged contracts and policy. The [32-call calibration proposal](../experiments/varied-calibration-plan-001/README.md) now freezes 16 exact prompts, two balanced replicates, prior model settings and guarded seeds; seven offline tests pass. No calls are authorized or dispatched. Next is scope review and separate budget approval, followed by a tested bounded runner.

## November 6: varied corpus and reserved family proposal

[The active task and evaluation plan](corpus-family-split-plan.md) now proposes 18 semantic instances: four development families with one calibration and two collection cases each, plus two reserved test families with three cases each. Four structural variants and two independent samples yield 144 proposed calls, staged as 32 calibration, 64 development collection and 48 reserved-family evaluation. This replaces the unexecuted older 224-call recommendation; no new requests, verifier runs or exact prompt freezes were made. All prior inspected artifacts remain development data. Tree and transition-system families are candidate author-visible holdouts, pending actual ancestry/protocol audits; no unseen-family performance claim exists. The next build starts with bounded allocation and map swap, then the conditional and sequence calibration cases.

## November 6: strengthened-task pilot completed

[The sixteen-call pilot](../experiments/witness-map-calibration-pilot-001/RESULTS.md) completed with 16 unique IDs, zero SDK retries and 64,085 tokens. All responses passed extraction and the proof guard; eight strictly verified, seven had proof failures, one had warning-only exit 2. Six witness failures incorrectly choose the first interval's lower endpoint without checking the second interval. One map proof omits an inner-update value fact. The warning-only output proves all obligations but keeps its original strict non-pass. All eight separate responses duplicate their helper bodies. This is useful development failure evidence, not a general sharing/depth result or held-out evaluation. The 16-call budget is exhausted and full logs are published.

[Two subsequent analyst diagnostics](../experiments/witness-map-diagnostic-001/README.md) passed on job 58545377 with no new model calls: adding the missing inner-update fact resolves the map proof failure; replacing concrete map comprehensions removes the trigger warnings without extra lemma calls. Each verifies 16 obligations with zero errors and warnings under the original strict flags. Original score remains 8/16; all 514 original model-archive files were checked unchanged. The successful fact ordering also reinforces that the annotated reference path is not a necessary-depth lower bound. Next: semantic diversity and a defensible family split, rather than crediting analyst repairs as new model success.

## November 6: tolerant extraction and stronger witness/map obligations

[JSON envelope validation](../experiments/reasoning-envelope-policy-001/README.md) admits exactly one complete JSON object with surrounding prose and preserves the unchanged bounded body guard. Nine adversarial tests and 40 exact saved-candidate replays passed, including the original mathematical failures. No old score changed.

[Separated-witness and overwrite/delete tasks](../experiments/witness-map-strengthening-001/README.md) add two development instances across shallow/deep and shared/separate cells. Job 58529512 passed all 64 declared outcomes: eight references, 48 proof failures and eight hidden-export failures; no parse errors or warnings. The interval target requires two common witnesses separated by a positive gap. The map target handles both equal and distinct updated keys before deletion. A separate registry passes five offline tests and reconstructs all 56 semantic controls exactly. Eight alternative strategies also verify after exact tolerant-envelope reconstruction: upper-endpoint witnesses and query-key map case splitting. Family-specific reference dependency stages and sharing/forwarding confounds are documented. Full raw sources and logs are archived. **Zero model calls** in this phase; greater model difficulty remains unmeasured. A [prospective 16-call development proposal](../experiments/witness-map-calibration-001/README.md) now freezes eight payloads/order/policies and passes five offline tests; it is not authorized or dispatched.

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
| Baseline evaluation run | Completed bounded 20-call run: 7 legacy successes, 6 strict zero-exit verifications; source fidelity separately audited; full paper reproduction remains outside this milestone |
| Repository representation and variables | File manifest, declared dependency map, fixed contracts/edit scope, revision hashes, task/attempt identity and whole-repository outcome implemented; source remains authoritative for APIs/specifications; consolidated protocol review completed in controlled-corpus-design.md |
| Multi-module context and verification | Previously validated; full source plus declared map is the initial policy, not automatic dependency selection |
| Whole-repository repair loop | New sequential engine preserves failed attempts, feeds back diagnostics and atomically promotes verified revisions; 28 offline tests pass; scripted real-Dafny control job 55802594 completed: 12 expected verifier outcomes, four contract rejections and intact original revisions |
| Live agent demonstration | Completed: four repositories repaired on first model attempt, four calls used; guarded sources and accepted revisions reviewed |
| Begin scaling generation | Completed initial collection: four actual model-generated client extensions across two seeds, all verified; primary corpus remains Weeks 5–6 |

New additive baseline request adapter has ten fake-transport tests; six smoke-runner
and three agent-adapter tests pass. Existing frozen protocols are unchanged. Neither
queued controls nor fake transport tests are model findings. All newly prepared
live settings and scope are documented in the respective experiment directories.

The user requested automatic continuation while asleep. The new combined driver
keeps one private key handoff in compute-process memory across the 20-call
baseline and at-most-eight-call agent pilot. Four orchestration tests pass;
agent controls are complete and reviewed; baseline preflight is complete and reviewed. No additional generation budget inferred.

## Completed live milestones (October 28, job 55807561)

Baseline and live repository-agent gates now have reviewed model evidence.
[Combined results](../experiments/weeks1-4-continuation-001/README.md) include full
logs, 24 unique requests without retries, frozen-input checks and manual baseline
specification audit. Earlier preparation sections above describe historical state.
Consolidated representation/experimental-variable protocol review is complete.
Still open: initial generation/extension across multiple repositories. Four unused agent calls
are not a generation budget. This earlier pending checkpoint is superseded by the completed acceptance review below.

Repository-extension-001 now prepares four new-client extensions across two verified
seed repositories, with immutable seed checks and separate guards. Four offline
tests passed; compute preflight job 55810726 matched all14 expectations (six passes,
eight proof failures), and four exact prompts/settings are frozen. Bounded runner
integration now has ten passing fake-transport tests; separate four-call approval
and a new private key handoff remain required. No new model calls.

## Weeks 1–4 completion (October 28)

[Acceptance review](weeks1-4-acceptance.md): **the initial proposal milestones are
complete**. Repository-extension-001 job 55813370 finished in 1m48s: four requests,
four whole-repository passes, zero retries, 4,613 tokens. Frozen prompts/runtime,
new-file guards, immutable seed bytes and accepted evidence hashes were reviewed.
Full logs and generated sources are archived. This closes the initial-generation
gate; it does not claim completion of the primary corpus or open-ended generation.
The next phase is a matched, more diverse Weeks 5–6 corpus with a declared family
split and a separately approved budget. Historical dated checkpoints above are
retained, including their then-pending status.

## Weeks 5–6 planning (October 28; no execution authorization)

The [larger matched-corpus plan](weeks5-6-corpus-plan.md) recommends a 32-call
calibration gate followed by a separately approved 192-call main stage: 24
underlying instances, 96 structural variants and two independent samples each.
Four development families vary depth and shared/duplicated helper proof workload;
reserved-family evaluation is separate. Proposed total 224, optional balanced
map study +64. Templates, guard preflight and exact prompt freeze come first.
No model requests, new verifier jobs or corpus generation were launched in planning.

## Monorepo calibration verified and frozen

Nada's monorepo scope is implemented in all four development families: conditional
preconditions, sequence induction, relational join and map-frame preservation.
Sixteen shallow/deep × shared/separate variants have 118 reviewed expected verifier
outcomes. The initial sequence well-formedness failure and all logs remain saved;
a one-line corrected revision passes. No model calls were made.

Eight output-guard tests, four freeze tests, two four-test design suites and an
exact source/evidence audit support the [frozen 32-trial proposal](../experiments/monorepo-calibration-001/README.md).
Two independent samples per variant are counterbalanced with fixed prompts,
settings and guarded edit scope. Per-family contract depth and differing shared
versus separate workloads are disclosed, not presented as equal-work matches.

Week 5's calibration construction/preflight gate is complete. Calibration execution
requires new 32-call approval and a bounded dispatcher bound to this freeze. The
main 192-call corpus, calibration findings and held-out evaluation remain open.

## Calibration collected and audited (October 28 Eastern)

[Full results](../experiments/monorepo-calibration-pilot-001/RESULTS.md): all 32 authorized
requests completed without retries. Original strict score 18/32; fourteen output
rejections, no verifier failures among admitted candidates. A separate zero-call
diagnostic verified11/11 newline/inline-expression cases; original results remain
unchanged. Three wrapper failures remain unevaluated. All logs are published.

Week 5 calibration has exposed output-protocol confounding and task-ceiling risk,
so Week 6 main collection is **not ready**. Next gates are a revised body-only
output protocol, explicit pure-expression support and harder verified obligations,
followed by a separately approved calibration. No model budget remains.

## October 29: revised calibration preparation (no model calls)

[Calibration v2 preparation](../experiments/monorepo-calibration-v2-001/README.md)
adds a separately versioned body-only JSON protocol: host-owned immutable file
assembly and bounded pure inline conditional expressions. Nine offline test
methods pass, including exact replay of 16 verified references and 11 diagnostic
workspaces. The original 32-call archive and 18/32 score remain unchanged.

Four matched alias-aware map-transfer configurations are built and verified, with
38 controls (4 passes, 32 proof failures, 2 hidden-name failures). They add
self-transfer semantics, balance conservation, exact balances, domain and frame
preservation, and an opposite-direction second client. These are development
tasks; no measured model-difficulty improvement is claimed. After reconnection,
verifier job **56196595** completed on non-preemptible test in **2m23s** with all
**38/38 expected outcomes** (4 reference passes, 32 proof failures, 2 hidden-name
failures). Full source/hash/diagnostic review and four body-only assembly records
are published. The complete revised pilot is not frozen, and no new model budget
is authorized.

## October 29: strengthened sequence/relational tasks and revised freeze

[Calibration v2](../experiments/monorepo-calibration-v2-001/README.md) now includes
42 validated weighted-sequence controls and 30 corrected interval-witness controls.
Sequence proofs must generalize the recursive offset; relational proofs construct
a common witness instead of receiving one as a parameter. Two failed trusted
provider revisions (existential proof, then non-ghost compilation) and all raw logs
remain archived. They are excluded from the selected validation evidence.

The revised 16-variant / **32-request proposal is frozen**, with **136/136 selected
expected outcomes** across the four families, one common body-only guard, fixed
settings, counterbalanced order and independent contexts. Six freeze tests pass.
No new model calls were made or authorized. This is development calibration, not
measured difficulty improvement or a causal shared-proof effect; main collection
remains deferred until a separately authorized calibration has been analyzed.

## October 29: revised calibration execution authorized and prepared

The user authorized the frozen revised 32-call pilot with no retries. The additive
[execution runner](../experiments/monorepo-calibration-v2-pilot-001/README.md)
passes 14 fake-transport/verifier tests and is hash-bound to the unchanged proposal
and a separate 32-call authorization. No job has been submitted or model requests
made yet. Cannon is reconnected, all staged inputs match their pins, and three
fake SDK/parser checks pass in the actual repodisco environment. The private key
handoff is still absent and was requested. No main-corpus or diagnostic model budget is
authorized. Historical preparation statuses in the frozen proposal are unchanged.

The revised calibration was subsequently submitted once as **56205855** on test
(PreemptMode=OFF), 18:55:32 UTC October 29. The 32-call frozen scope and no-retry
policy remain unchanged. Results pending; no duplicate or standalone job.

## October 29: revised calibration completed and audited

Job **56205855** completed on test in 3m26s. The frozen 32 trials produced
**1 strict whole-workspace pass and 31 output-syntax rejections**, with 32 unique
request IDs, zero SDK retries and 86,878 tokens. Full raw responses, source,
verifier evidence and reproducible audits are in
[the completed report](../experiments/monorepo-calibration-v2-pilot-001/RESULTS.md).
All JSON schemas were valid; each rejected trial first used `then` instead of the
required braced statement block. No rejected proof was repaired or rescored.
Protected sources/contracts and exact frozen messages passed integrity review.

The budget is exhausted. Next is non-paid prompt syntax clarification and offline
protocol validation before another frozen proposal; neither a sharing/depth effect
nor increased reasoning difficulty is established. The earlier preparation and
submission entries above are historical; main collection remains deferred.

## October 29: prompt syntax clarified and validated offline

[statement-syntax-v1](../experiments/monorepo-calibration-syntax-001/README.md)
updates all 16 prompts and the system message with explicit braced statement
syntax, required semicolons, single JSON escaping and neutral examples. The
parser, protected sources, contracts, model settings and 32-slot order are
unchanged. Nine test methods passed, including exact replay of 16 previously
verified references and all 32 saved responses; the prior 1/32 score is unchanged.
There were no new model or Dafny calls. A future model benefit remains unmeasured;
any execution needs separate authorization bound to the new prompt freeze.

## October 29: small syntax pilot scoped before another full calibration

The [eight-call smoke proposal](../experiments/monorepo-syntax-smoke-001/README.md)
selects every deep shared/separate task across four families, one fresh sample
each. Exact clarified prompts and parser are unchanged; two families begin shared
and two separate. Four offline scope checks pass. The gate is 8/8 guard admission,
intact protected source and completed verifier outcomes, followed by manual proof
outcome review. No calls are authorized or made by this preparation; a later full
32-call evaluation is not automatic and will not pool these deep-only samples.

## October 29: eight-call smoke runner prepared after approval

The user approved eight requests with no retries. The [bounded runner](../experiments/monorepo-syntax-smoke-001/EXECUTION.md)
passed 15 local fake-transport/verifier tests and three remote SDK/parser checks.
Exact inputs/runtime are staged in a fresh Cannon directory; the existing socket
works. The private handoff is absent and was requested. No model calls, submission
or key consumption yet; runtime-bound authorization and a fresh state check precede
the single job submission after key readiness. No automatic larger run.

After private key readiness, smoke job **56210087** was submitted once at 19:47:24
UTC October 29 on live-confirmed nonpreemptible test. The exact eight-call scope
and runtime are bound by authorization.json; no retries, requeue or reassignment.
Results are pending. Earlier local disk-space failures occurred before submission.

The same pending smoke job was subsequently moved in place to sapphire after
live PreemptMode=OFF verification. A mixed-partition update failed first; both
attempts are archived. No duplicate job was created. Local disk exhaustion
blocks checkout synchronization, so evidence publication uses GitHub directly.

## October 29: queued smoke pilot scheduling diagnosis

User-requested investigation found stale job evaluation, an old in-progress
backfill cycle and heavy controller/queue load. No hold, dependency or account-limit
reason was reported for job 56210087. Moved that same job back to live-confirmed
nonpreemptible test (higher tier and substantially fewer higher-priority queue
rows), without changing its resources, 30-minute limit or eight-call/no-retry cap.
It was still pending immediately afterward; zero calls reserved. Evidence and
limitations are in the [execution log](../experiments/monorepo-syntax-smoke-001/EXECUTION.md).

## October 29: eight-call syntax smoke completed

After the in-place return to test, job 56210087 completed in 2m04s. The reviewed
[results](../experiments/monorepo-syntax-smoke-001/RESULTS.md) are **8/8 parser/guard
admission and 7/8 whole-workspace verification**, eight unique requests, zero SDK
retries and 25,704 tokens. Protected contracts/source passed audit. The failed
deep/shared interval proof chooses c without establishing its membership in the
other interval. All original evidence is preserved; no repair or rerun was made.
The eight-call budget is exhausted. The syntax gate passed, but full calibration
and main collection still require review and separate authorization.

## November 2: difficulty reviewed and balanced calibration frozen

[New preparation](../experiments/monorepo-balanced-calibration-001/README.md)
retains the clarified prompts, all 16 task configurations, parser, settings and
counterbalanced order for 32 fresh samples. Nine offline tests pass, including
replay of 16 reference workspaces and all eight smoke responses, integrity checks
for the 136 selected prior verifier controls, and matched client/provider/contract
checks. No model requests, SSH access or new Dafny runs were made.

The interval-witness failure chose c without establishing a <= c; a concrete
counterexample and the already verified branch strategy are documented only for
reviewers. Other families remain ceiling risks: providers discharge much of the
underlying mathematics, and all separate smoke responses copied one proof into
both bodies. This is contract-composition and output-workload calibration, not an
equal-work causal sharing experiment or a held-out evaluation. New trial IDs and
separate ledgers prevent mixing prior samples. The 32 calls are a proposal only;
a separately tested runner/runtime freeze and explicit authorization are needed.
The 192-call main stage remains deferred pending protocol and difficulty review.

## November 2: balanced calibration approved and runner ready

The user approved the frozen 32-call plan with no retries. The isolated
[execution runner](../experiments/monorepo-balanced-calibration-pilot-001/README.md)
passed 18 fake-transport/verifier tests and three real-environment offline checks
on Cannon. Exact frozen inputs and runtime hashes match; the private handoff is
ready. Authorization pins the unchanged scope/runtime, 32-request cap, no retry
or reassignment, and a finite dispatch deadline. Single submission is next; no
model requests at this checkpoint. The main corpus remains unauthorized.

The approved balanced pilot was submitted once as **57099049** on test, with live
PreemptMode=OFF checked, at 19:49:40 UTC November 2. Results are pending; no retries,
requeue or duplicate jobs. Submission/authorization/lock records are archived.

## November 2: balanced calibration completed and reviewed

[Full results](../experiments/monorepo-balanced-calibration-pilot-001/RESULTS.md)
and [source review](../experiments/monorepo-balanced-calibration-pilot-001/MANUAL_REVIEW.md):
job 57099049 completed on test in 4m29s. Exactly 32 distinct requests, zero SDK
retries, 100,376 tokens, 32/32 output admission and 29/32 strict workspace passes.
All three failures are deep interval-witness preconditions (two shared, one
separate); all protected contracts and source passed review. Full raw evidence
and failed attempts are archived, with no repair/rescoring or further calls.

Conditional, sequence and map families each reached 8/8; interval witness reached
5/8. All 16 separate trials duplicate body syntax across their two helpers; 14/16
configurations repeat the same body syntax in both samples. The syntax protocol
worked in this run, but these small development results establish no general
sharing/depth effect. Main collection remains deferred: next build more varied
reasoning obligations with matched semantics and verifier controls before spending
on a larger corpus. All 32 approved calls are exhausted; no further model budget.

## November 2: richer obligations built; verifier gate pending

[Reasoning expansion](../experiments/monorepo-reasoning-expansion-001/README.md)
adds six authored development instances: nested clamping, clamp stability,
reverse over concatenation, nested filtering, commuting map updates and deletion
after update. Across 24 shallow/deep × shared/separate variants, clients,
provider files and helper contracts remain matched within each semantic instance.
Reference proofs construct relationships among primitive operations; providers
do not expose the target law. Six offline construction tests pass.

The first verifier-only phase (job 57104220) is queued for 24 reference and 24
empty-proof checks. The 116 targeted-negative checks remain gated on reviewing
that phase. The existing job was updated in place to nonpreemptible shared/sapphire;
Harvard reports scheduler maintenance through 23:00 UTC November 2. Sources,
tests, submission records and scheduling evidence are published. No new model
calls, measured difficulty claim or completed-verification claim. This remains
Weeks 5–6 development/calibration work; larger collection is still deferred.

During the user-authorized two-hour verifier-only continuation, a separate
reasoning-body output guard passed nine offline tests. It supports bounded locals,
recursion and universal pointwise proof blocks while preserving imports, helper
contracts and immutable sources. All 24 reference workspaces and 104 semantic
negative-control bodies reconstruct exactly. This is output admission, not
Dafny success; reference semantics are still pending. Old frozen protocols and
the running/queued verifier inputs are unchanged. No model pilot or calls added.

The original reference job 57104220 then started and failed before any Dafny check:
two transitive package dependencies were omitted from the staged runtime. Full
startup logs/accounting are preserved. Deliberate `runtime-002` adds those imports
with all 1,476 fixture files unchanged; two import/fake-process tests pass locally
and in Cannon's environment. Corrected reference job 57106124 was submitted once
on nonpreemptible shared. This is an infrastructure correction, not a proof
finding. Semantic validation is still pending; no model calls.

Corrected runtime job 57106124 finished: 20/24 reference workspaces passed and
24/24 empty-proof controls failed as intended, with exact source/hash/diagnostic
review and full logs archived. The four reverse-concatenation references fail
their final equality assertion. This is a reference-proof issue requiring a
versioned repair, not a model result. Targeted negatives remain gated. No calls.

Revision 003 now makes the reverse proof steps explicit while preserving all
contracts, clients and providers. Eleven offline checks pass. Job 57111126 was
submitted once for just four changed references; the 44 byte-identical successful
control outcomes are reused with hashes. All first-run failures remain published.

Job 57111126 verified all four revised reverse references. The audited reference
gate now covers all 24 reference workspaces and all 24 expected empty-proof failures,
reusing 44 byte-identical prior outcomes without creating new trials. Full logs
and original failures are preserved. Distinct targeted-negative job 57112358 is
submitted on nonpreemptible shared for 116 checks; no model requests.

## November 2: richer task validation complete

[Final results](../experiments/monorepo-reasoning-expansion-001/RESULTS.md) now cover
all 164 final fixture conditions: 24 reference passes, 120 ordinary proof failures,
8 explicit termination failures and 12 hidden-export name-resolution failures.
Job 57112358 completed all 116 targeted controls in 6m32s on shared. Exact source
hashes, diagnostic categories and protected-source consistency were reviewed;
no parse error was credited as a reasoning failure. Full raw code/log archives
and acceptance evidence are published, including the initial import failure and
four original reverse-proof failures. Zero model calls.

This completes the requested verifier-only strengthening of the three saturated
families: six semantic instances, 24 matched workspace variants, and a tested
separate body-output guard. Forty-four unchanged earlier outcomes are reused with
exact hashes, not counted as new independent trials. There were 168 actual Dafny
invocations across history. Model difficulty remains unmeasured; all families are
development tasks, and separate conditions still permit duplicated proofs.

Weeks 5–6 next gate: separately review/freeze prompts and output policy for these
final sources and approve a bounded model calibration before any larger corpus
collection. No such new pilot is frozen or authorized by this verifier work.

## November 2: six-task calibration proposal frozen

[New plan and prompts](../experiments/monorepo-reasoning-calibration-001/README.md)
propose 24 fresh requests: six semantic instances × two depths × two sharing
conditions × one sample. This covers all 24 verified configurations, eight calls
per family and six per cell. Exact prompt/request bytes, source/guard/settings
hashes and counterbalanced order are frozen. Twelve offline tests pass, including
24 reference and 104 semantic-negative reconstructions, prompt isolation and
deterministic regeneration. The 164 prior verifier outcomes were audited without
rerunning Dafny. Zero new model calls; no runtime submission or execution approval.

This small run is intended to detect difficulty and output-policy problems before
larger collection. One sample per configuration cannot measure sampling variance
or establish causal depth/sharing effects; separate conditions have two editable
bodies and allow copying. All instances remain development data. Any floor,
ceiling or output-policy problem requires review before scale-up. The next gate
is explicit approval of 24 new requests and a separately tested bounded runner;
no historical unused budget is reassigned and no main corpus is launched.

## November 2 Eastern: approved reasoning pilot started

The user approved 24 new requests, no retries, and two hours of follow-up.
[The bounded runner](../experiments/monorepo-reasoning-calibration-pilot-001/README.md)
passed 21 local fake-transport/verifier tests and three selected fake-only checks
in Cannon's actual package environment. Exact proposal/prompt bytes remain pinned.
Job 57162314 started at 00:48 UTC November 3 on live-confirmed nonpreemptible
`test`, with no requeue. It reserves each request durably, uses one SDK attempt,
stops on ambiguity/infrastructure failure and cannot reopen an existing ledger.
Full raw responses, candidates, verifier logs and request-count audit will be
published after completion. No result or larger-corpus authorization is implied
by startup. Follow-up and dispatch authorization end at 02:44:13 UTC.

## November 2 Eastern: reasoning pilot completed and audited

[Full results and logs](../experiments/monorepo-reasoning-calibration-pilot-001/RESULTS.md):
job 57162314 completed in 4m39s with exactly 24 requests, unique request IDs,
zero SDK retries and 83,777 tokens. Nineteen bodies were admitted; 18 whole
repositories verified and one commuting-update proof failed an assertion.
The other five responses had valid JSON but used body syntax outside the guard:
two primed local identifiers and three set/map-expression cases. They were not
sent to Dafny and are not established reasoning failures. All 19 candidate source
hashes and protected contracts were checked; 18 accepted bodies manually reviewed.

Conditional 8/8, sequence 6/8 and maps 4/8, with one request per configuration.
All 12 separate responses duplicate helper-body strings. The two conditional
instances and nested filtering remain at four-cell ceiling. Differences across
sharing/depth cells are descriptive and confounded by output-policy rejection;
no causal effect or held-out result is claimed. Original scores and raw evidence
remain unchanged. All 24 calls are exhausted. Next gate: separately labeled
offline/compute-only diagnosis of rejected syntax and the failed assertion,
then a versioned protocol/difficulty decision before any larger paid collection.

## November 2 Eastern: saved-response semantic diagnostic

[Separate verifier-only evidence](../experiments/reasoning-response-diagnostic-001/RESULTS.md)
now distinguishes the five body-guard rejections: three exact original bodies
verify, one fails the same map-value assertion in both copied helpers, and one
finishes proof verification but exits 2 because missing-trigger warnings are
disallowed. The originally admitted failing proof verifies after adding exactly
one missing inner-update observation. This repair is analyst-authored, not another
model response. Job 57167108 ran all six checks in 25 seconds with zero model
calls; exact protected source and original response hashes were audited.

The original 18/24 result is unchanged. These findings establish concrete protocol
exclusions alongside a real missing-fact failure, not a revised success rate.
The next gate is a separately versioned output-language decision with boundary
tests and continued difficulty review; conditional and nested-filtering ceilings
persist. All requested model calls and the additional non-paid diagnosis are now
complete and documented. No further model budget or main collection is authorized.

## November 2 Eastern: separately versioned output policy

[Policy v2](../experiments/reasoning-output-policy-002/README.md) now admits the
primed identifiers, set displays, functional updates and one-binder map
comprehensions observed in the saved outputs. Twenty-five offline test methods
passed, including unchanged legacy tests, scope/bypass/complexity cases and
evidence checks. All 24 saved responses reconstruct exact prior candidate bytes;
24 references and 104 semantic negative controls also reconstruct unchanged.
The audit links prior verifier records and distinguishes the warning-only exit
from assertion failure. It invokes neither a model nor Dafny.

This is post-hoc protocol development, not a revised 21/24 score or a prospective
evaluation. Original score remains 18/24; all frozen files and source/diagnostic
archives are unchanged. Strict warnings remain non-success. The syntax contract
and code are versioned separately; no new pilot prompts or model budget are
authorized. Task difficulty and a future task-set decision remain open.

A [single compute-only follow-up](../experiments/reasoning-output-policy-002/warning-preflight/README.md)
then confirmed a permitted warning-free formulation for trial 24: substitute the
proof's existing `lhs`/`rhs` aliases in 15 expressions from the first quantifier
onward. No new lemma calls, attributes, contracts or warning-policy changes.
Job 57178004 returned 16 verified, zero errors and warnings, exit 0. This is an
analyst-authored repair of one body, not model credit or a general guarantee.

## November 2 Eastern: guarded conditional monotonicity

[conditional-monotonicity-001](../experiments/conditional-monotonicity-001/RESULTS.md)
adds a different conditional obligation: show clamping preserves order by selecting
guarded below/within/above facts for two inputs. All four matched reference
workspaces pass; 24 targeted bodies fail proof obligations and four hidden-view
calls fail resolution. Job 57180678 completed all 32 checks in 1m27s, with zero
model calls and full byte/diagnostic review. Five offline construction tests pass.

Unlike unconditional clamp observations, wrong-region and equality-boundary calls
now fail preconditions. This establishes fixture behavior, not model difficulty.
The deep reference has two independent facts followed by assembly (three calls,
two application stages, one edge between applications); separate mode still permits copied helper bodies and has
greater edit workload. A separate monotonicity API registry now passes 25 offline
methods on the unchanged v2 grammar, including old-registry equality, protected
boundaries and exact replay of the 28 admitted new control bodies. Four hidden
views are rejected. Future prompts/order/settings still need a coherent freeze;
no model budget is inferred.

## November 2 Eastern: four-family grammar compatibility

[monorepo-policy-integration-001](../experiments/monorepo-policy-integration-001/README.md)
adds the existing interval-witness registry on the common bounded grammar and
protects its module aliases from local shadowing. Twenty-seven offline methods
pass. Four witness references and 20 admissible negative bodies reconstruct
exactly; two hidden calls and four contract edits are rejected. All eight saved
witness candidates, including three precondition failures, retain their bytes
and prior verifier evidence. No new verification or model calls.

The compatibility catalog covers eight inspected semantic instances and 32
workspace variants across four families. It is not a new pilot or the main
corpus. Existing scores 29/32 and 18/24 stay separate and unchanged. Technical
family compatibility is now addressed; task selection/difficulty, per-family
depth annotations and a complete prospective request freeze remain before any
new model-budget decision.
