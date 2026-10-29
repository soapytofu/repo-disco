# Revised calibration pilot: authorized 32-call execution preparation

The user explicitly authorized the revised 32-call calibration on October 29,
2026, with the frozen prompts, no retries, and publication of results/full logs.
**No model calls have been made and no Slurm job has been submitted yet.**
The new Cannon connection works and the runtime is staged. All staged hashes
match; three SDK/body-parser checks passed in the repodisco environment using
fake transport/verifier. The private key handoff is still absent and has been
requested. No credential contents were accessed during preparation.

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
records pinned input validation and no previous run/submission. One exclusive
submission will follow the private key handoff.

`runtime-freeze.json` binds the runner, gate, tests/log, Slurm script, audit scripts
and verifier code to the immutable proposal. `authorization.json` separately binds
the user's 32-call authorization to both freezes. The proposal's historical
NO_MODEL_AUTHORIZATION status is preserved; it is superseded only for this bounded
execution by the separate authorization, not edited in place.
