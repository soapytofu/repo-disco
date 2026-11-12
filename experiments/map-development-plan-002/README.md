# Fresh balanced map pilot — frozen proposal

**Prepared November 12, 2026. Proposed: 16 NEW Claude requests. Execution is not authorized. No model calls, credentials, cluster jobs or live runner were used for this preparation.**

This is a fresh development calibration of fresh-key move composition and restriction over disjoint merge. It preserves the verified workspaces, model settings, parser, protected-source policy and measurements from [plan 001](../map-development-plan-001/README.md), while clarifying the accepted output syntax. The [previous interrupted pilot](../map-development-pilot-001/RESULTS.md) and [analyst ordering diagnostic](../map-order-diagnostic-001/RESULTS.md) remain unchanged.

## Scope and budget

| Task | Structural conditions | Fresh responses per condition | Proposed calls |
| --- | --- | --- | --- |
| D4-M1: two fresh-key moves compose | Shallow/shared, shallow/separate, deep/shared, deep/separate | 2 | 8 |
| D4-M2: restriction distributes over disjoint merge | Same four conditions | 2 | 8 |
| Total | 8 workspaces | 2 | **16** |

Eight unique [request payloads](frozen-001/requests) specify sixteen fresh-context trial slots, named `map-balanced-01` through `map-balanced-16`. Both requested bodies in a separate workspace belong to one response, not two calls. There is no feedback, automatic retry, SDK retry, requeue, resumption after an ambiguous request, or reassignment of unused slots. A transport or ambiguous-save failure must close the run and preserve the partial cohort; sixteen is a cap, not a guarantee of sixteen returned responses.

These are sixteen new proposed requests. The previous cohort dispatched ten requests, received nine responses and left six slots undispatched. Those unused slots and previous responses are not reused here. Do not pool the interrupted cohort into the fresh balanced score or replace its failures. With the other original corpus stages unchanged, the attempted-request forecast becomes 32 completed C1 + 10 interrupted map dispatches + 16 proposed fresh map + 48 other development + 48 reserved-family = **154**, rather than the original 144. This is accounting, not authorization or a billing claim about the ambiguous request.

The fixed settings are `global.anthropic.claude-opus-4-5-20251101-v1:0`, `us-east-1`, temperature 1.0 and 4,096 maximum output tokens per request (65,536 across sixteen). No dollar estimate is made without current provider pricing; prompt token counts are unmeasured, while exact UTF-8 sizes are [recorded](frozen-001/request-sizes.json).

## Clarified syntax; unchanged mathematics and parser

The [system](system.txt) and [syntax instructions](syntax.txt) now explicitly require one `ensures` clause per `forall` proof statement, joining multiple postconditions with `&&`. They distinguish that braced statement from an `assert forall ... :: ...;` expression, which ends with a semicolon. A generic trivial conjunction example illustrates the accepted grammar. The prohibition on new declarations now explicitly names modules, functions, lemmas and methods; inferred local variables remain allowed.

Repeated `ensures` is a restriction of this bounded parser, not a claim that the syntax is invalid in Dafny. We do not expand the grammar or rewrite generated proofs. The whole-workspace task, supplied facts and protected contracts are identical. No certificate-ordering advice, reference proofs, old responses or verifier diagnostics enter the prompts. [The exact delta audit](frozen-001/syntax-change-review.json) proves that each request differs only in its system and syntax-instruction sections; seeds, policies, metrics, inference settings and order are unchanged.

## Frozen order and evidence

[trials.json](frozen-001/trials.json) fixes two replicates: each workspace once per replicate. Task order alternates and reverses between replicates. The four task-by-replicate relative cell-position rows follow a Williams square. This balances relative cell positions; physical adjacent-trial transitions are not claimed perfectly balanced. Every request starts a fresh context, without sharing outputs between trials.

Freeze SHA-256:

`e50e4cea1d6e6c1a4dcbc8815b25f378854d9e80ae6e88aa31a0fcd881940f3d`

[freeze.json](frozen-001/freeze.json) pins 93 frozen files and 369 repository inputs, based on source commit `606ddaf34e793ba0ec912c06909738de072037c0`. The freeze includes exact tasks, guards, immutable seeds, requests, order, settings, measurement scope and prior-cohort provenance. Historical plan-001 freeze remains `84211b3fd2286cc0b6c8cb5b139c6856dc214270c09762c9dcc0f03f0fbe2097`.

The existing [76 verifier controls](frozen-001/reviewed-controls.json) are reused with exact source/hash checks: eight strict reference passes, sixty expected proof failures and eight expected hidden-export resolution failures. They are prior observations, not fresh independent trials. No unchanged Dafny jobs were rerun for this syntax-only proposal.

## Evaluation and interpretation

Primary: admitted proof bodies followed by whole-workspace verification, including all providers and both clients, strict exit zero and no warnings. Use pinned Dafny 4.11.0, Z3 4.12.1 and a 60-second verification limit on a compute node.

Report every cell's planned, dispatched, returned, extracted, admitted and strict-success counts. Keep envelope, body-policy, frontend, proof, warning-only, timeout and infrastructure failures distinct; undispatched and ambiguous requests are not mathematical failures. Report the accepted whole-workspace result separately from named editable-helper completion and supplied-client dependency closure, using the unchanged [target scope](frozen-001/target-scope.json). Locally verifying a client against an unproved helper contract is not a completed repository. Supplied providers and clients receive no model-edit credit. Record request IDs, retry count, tokens, response/extraction text, guarded sources, exact hashes, verifier output and copied separate bodies.

These are two related map development instances, with only two observations per cell. Shallow/deep describes bundled versus decomposed contracts, not proven minimum reasoning depth. Shared has one editable body and an immutable forwarding helper; separate has two bodies and copying is allowed, so output workload differs. Prompt clarification was informed by development outputs. This is neither held-out evaluation nor a controlled estimate of the prompt-change effect. Compare the prior partial cohort descriptively only; no general causal sharing/depth, statistical significance or minimal-proof claim follows.

## Offline validation and next gate

[Eleven offline test methods](offline-tests-001.log) pass: exact rebuild with network/process calls blocked; balanced budget/order; immutable source and metadata; admitted literal syntax examples; conjunction/form rejection boundaries; JSON ambiguity checks; fresh trial IDs; target denominators; overwrite refusal; and exact replay of all nine saved responses. Eight still admit byte-for-byte and the repeated-ensures response still rejects. The [provenance audit](frozen-001/prior-cohort-provenance.json) checks all 646 old model-archive files unchanged. These are parser/provenance checks, not new mathematical verifications or model results.

Reproduce offline from the repository root:

```sh
python3 -B -m unittest discover -s experiments/map-development-plan-002 -p test_plan.py -v
```

Before any future collection: obtain explicit approval of these sixteen new requests, prepare and test a separate bounded runtime binding this exact freeze and fresh trial IDs, confirm the immutable sources and output-ledger absence, and arrange private credentials and compute allocation. No authorization file, paid dispatcher or submission is part of this proposal. Preserve the old closed ledger and all original results.
