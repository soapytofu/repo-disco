# Revised calibration pilot: completed 32-call execution

The user explicitly authorized the revised 32-call calibration on October 29,
2026, with the frozen prompts, no retries, and publication of results/full logs.
**Submitted once as Slurm job 56205855 on test, October 29 at 18:55:32 UTC.**
Inputs, authorization and the private handoff were checked before submission.
The partition reported PreemptMode=OFF; no requeue or retries. The job completed
in 3m26s: **1/32 strictly verified, 31 body-syntax rejections**, with 32 unique
request IDs and zero SDK retries. All 32 authorized calls are exhausted.
See [RESULTS.md](RESULTS.md) for cell counts and interpretation, and
[output-syntax-audit.json](output-syntax-audit.json) for the separate offline diagnosis.
This is the only submitted execution for the 32-call budget.

## Immutable scope

`frozen-001` is an exact copy of the reviewed proposal in
[monorepo-calibration-v2-001](../monorepo-calibration-v2-001/README.md).
Freeze SHA-256: `c37781be6014e0b5ba53ae99b28a90bf7a5bf05be2cd15650098dadc3ac0a590`.
32 independent trials, 16 variants, two fresh responses per variant; four families
and the exact counterbalanced order, source, prompts, model/settings and
body-json-v2.1 grammar remain unchanged. No feedback, replacement samples,
automatic recovery, retry or unused-call reassignment. The main 192-call corpus
is not authorized. One semantic instance per family is a development diagnostic;
tasks and output policy both changed, so before/after results cannot isolate one.

## Bounded runner

`run_pilot.py` is additive to the completed first calibration. Its only protocol
adaptation loads the pinned v2.1 grammar/body parser and lets the host assemble
immutable files. The loader isolates the grammar import from other experiments.
`bounded_requests.py` is byte-identical to the previously used durable single-owner
request gate: reserve before dispatch, one SDK attempt, stop on ambiguous transport
or response persistence, and check the deadline before every actual request.
Each request records exact messages, response, request ID, retry metadata and usage.
Each admitted candidate records extraction/AST, immutable parent/candidate hashes,
full sources, verifier stdout/stderr, and acceptance evidence. Parser/proof errors
are completed outcomes; infrastructure errors stop the batch without reassignment.
The CLI refuses an existing output directory or ledger and cannot resume.

The private handoff is loaded and immediately deleted only by the compute process;
the key stays in memory for the run and is never archived. Slurm uses a live-checked
non-preemptible partition, no requeue, 2 CPUs/8 GB, with a two-hour job limit.
Dafny runs only on compute nodes. No extra connectivity/token API probes are used.

Fourteen offline runner tests pass with fake transport and verifier, including
32 exact messages in order, quota exhaustion, ambiguous-request stop, deadline,
existing-ledger refusal, seed drift, invalid metadata, guarded body assembly,
full-file/bypass rejection, frozen grammar isolation and exact SDK no-retry setup.
These tests are not live model or Dafny results. Three additional remote SDK and
body-parser environment checks pass (environment-tests.log); stage-review.json
records pinned input validation and no previous run/submission. The single exclusive
submission is recorded in submission.json and submission.lock; no resubmission occurred.

`runtime-freeze.json` binds the runner, gate, tests/log, Slurm script, audit scripts
and verifier code to the immutable proposal. `authorization.json` separately binds
the user's 32-call authorization to both freezes. The proposal's historical
NO_MODEL_AUTHORIZATION status is preserved; it is superseded only for this bounded
execution by the separate authorization, not edited in place.

## Reviewed evidence

The full raw archive is in model-001, with Slurm stdout/stderr and accounting
alongside it. results-review.json reports no integrity issues; model-001-sha256.json
binds every raw file. Frozen prompts/order/settings and all protected source and
contracts were checked, including the accepted trial-28 workspace. The temporary
credential handoff was deleted by the compute process and is not in the archive.

All responses contain valid JSON with the exact filename/body schema. In all 31
rejected trials the first syntax mismatch is `then` where a statement `{` was
required. audit_output_syntax.py traces the frozen parser without changing its
acceptance rules, repairing bodies, rerunning Dafny, or making model calls. The
strict score remains 1/32; no conclusion about reasoning difficulty or sharing
effects follows from this syntax-dominated run.

A subsequent [offline prompt revision](../monorepo-calibration-syntax-001/README.md)
clarifies statement syntax with the same parser. It preserves this archive and
score and makes no new model or verifier calls.
