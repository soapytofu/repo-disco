# Research progress and next milestone

Status: October 23, 2026. Timeline source: Sophie Zeng's *HCRP Research Proposal F26*, “Time Frame” (page 5), with methodology on pages 2–4. Weeks below are proposal-relative; a calendar start date has not been established here.

| Proposal phase | Planned work | Current status / next action |
| --- | --- | --- |
| Weeks 1–2 | Set up Formal Disco and Dafny; reproduce baseline generation/evaluation; finalize repository representation and variables | Tooling, verified single-program generation, extension/repair pilots, and a 50-call format pilot are recorded. Published baseline evaluation is not reproduced. Finalize representation and metric definitions before claiming this phase complete. |
| Weeks 3–4 | Multi-module representation, repository-map/context infrastructure, whole-repository verification and repair; validate two-module repositories, begin scaling | **In progress:** two-module-001 implements a minimal manifest, API/client dependency, whole-repository verification, and protected edit policy. All 12 deterministic checks passed. Claude repaired the provider on its first call with the client unchanged and the whole repository verified. General context construction and generation are not yet implemented. |
| Weeks 5–6 | Controlled dependency depth, API reuse, shared proofs; matched baselines; primary synthetic corpus | Follow successful two-module validation; vary structure while matching size/specification counts. |
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
