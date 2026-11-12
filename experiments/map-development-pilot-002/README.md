# Fresh balanced map pilot — approved runtime

November 12, 2026. Sophie explicitly approved **16 new Claude requests, no retries** for the [syntax-clarified frozen proposal](../map-development-plan-002/README.md), and subsequently confirmed the private key handoff ready. This is a separate run with fresh `map-balanced-01` through `map-balanced-16` IDs. The old interrupted run remains closed and unchanged; none of its unused slots or responses is reassigned.

## Frozen scope

- Proposal SHA-256: `e50e4cea1d6e6c1a4dcbc8815b25f378854d9e80ae6e88aa31a0fcd881940f3d`.
- Runtime SHA-256: `2923c413d110e8ff31d1b2c4b3a056c6f80562ae9a895fbc4758d3a9a3f3ebff`.
- Two map development instances × four structural conditions × two independent fresh-context responses: **16 calls maximum**. Same model, settings, seeds, parser, task contracts, target metrics and frozen order; prompts clarify syntax only.
- [readiness-gate.json](readiness-gate.json) binds the prior 76 reviewed controls, five measurement controls, exact syntax-only delta audit and historical cohort provenance. No unchanged verifier controls are rerun.
- [stage-001.json](stage-001.json) records the exclusive staged runtime at `~/formal-disco/outputs/map-development-pilot-002`.

## Safety and evidence protocol

The separate runner pins every request and runtime file, requires fresh human authorization bound to both freezes, and checks hashes before each request. Its durable gate reserves before dispatch, refuses restart or a reused ledger and uses exactly one SDK attempt. Calls are sequential to preserve the frozen order. No retries, feedback, replacement calls, reassignment or Slurm requeue. An ambiguous service/transport/save failure stops the run; ordinary invalid/proof/warning outputs consume their slots and remain evaluation outcomes.

The submission tool checks existing outputs, lock, queue and live `test PreemptMode=OFF`, then creates an exclusive submission lock and submits once. Prepared resources: two CPUs, 8 GB, one hour. The compute entry point checks pinned Dafny/Z3 versions before consuming and deleting the private handoff, retains the token in memory/environment only and clears it on exit. Credentials are never archived. No API connectivity test is used.

The existing durable gate, transport, logged verifier and target interpreter are byte-identical to the tested prior runtime. The new runner changes the freeze identity, trial namespace and output directory, and additionally checks the new syntax/provenance gates. The reviewer requires a terminal ledger and independently replays frozen prompts, request IDs, retry metadata, exact candidate bytes, protected source boundaries, verification diagnostics and named-target metrics. Full raw responses, extraction decisions, source hashes, stdout/stderr, CSV, tokens and scheduler/accounting records are retained, including failures.

## Validation and status

[Twenty offline tests](runner-tests.log) pass, including a fake complete sixteen-request collection, exact frozen order, fresh contexts, ambiguity/restart refusal, persistence failure, deadlines, strict warning handling, measurement failure, reference reconstruction, protected edits, metadata errors, archive tampering and the clarified single-ensures grammar. These tests make zero provider requests and run no Dafny process.

[Cannon's environment preflight](environment-preflight.log) passed with installed boto3/botocore 1.43.115, an injected fake client and fake verifier. [authorization.json](authorization.json) records the explicit approval, exact freeze bindings and three-hour dispatch deadline. Job **60073401** was submitted once at 20:28:45 UTC on live-confirmed `test PreemptMode=OFF`; [submission.json](submission.json) records the exact scheduler state and authorization/runtime hashes. Its results are pending review. No second job or alternate runner was submitted. The proposal and runtime remain unchanged.

Primary scoring remains guarded whole-workspace strict exit-zero verification with no warnings. Editable helper completion and dependency-closed supplied-client status are secondary; local client verification against an unproved helper contract is not repository completion. This is a small development calibration of two related map instances, not held-out performance or a causal prompt/depth/sharing result. Separate bodies can be copied and require more output. Keep the original partial cohort and analyst diagnostics separate; no rescoring.
