# Approved 24-call reasoning calibration

The user approved **24 new Claude requests with no retries** for the six-task
[frozen proposal](../monorepo-reasoning-calibration-001/README.md), then requested
two hours of follow-up through November 3, 2026, 02:44:13 UTC (November 2,
9:44 PM Eastern). This approval does not expand the model budget.

Status: **job 57162314 completed in 4m39s: 24 requests, 18 verified, five body-guard
rejections and one assertion failure, zero SDK retries.** Read the
[results and failure analysis](RESULTS.md) and [per-trial log](TRIALS.md).
It started on `test` at 00:48 UTC November 3 after local/remote preflight passed
and the runner was published in `77625c8`.
[Submission and live preemption evidence](submission.json) record one submission,
`PreemptMode=OFF`, no requeue and the exact authorization/runtime hashes.
The full request budget is exhausted. Original results and frozen sources are preserved.

The proposal copy is byte-identical: SHA-256
`56dc93326ba4ebaa7ba6d5787207665c3ed89f81cf2f5703362b2815640d0afc`.
The [runtime freeze](runtime-freeze.json) SHA-256 is
`5870c0a91c9ec8cfd43a8fd445935b438c0c3d2fb0ae59dbcb817cec60af66ee`.
Every model request uses the exact frozen `request.json` payload; no prompt,
order, inference setting, guard or source changes. Six tasks × two depths × two
sharing conditions × one sample = 24 requests; no pooling earlier responses.

The [runner](run_pilot.py) uses a [durable request gate](bounded_requests.py),
one SDK attempt and one fresh ledger. It checks source/runtime hashes before
each dispatch and enforces the authorization deadline both before and after
reservation persistence. Existing output, ledger or submission lock prevents
automatic restart. A reserved ambiguous request cannot be retried or replaced.
Returned malformed, truncated, frontend or proof-failure responses consume their
trial; infrastructure/transport/hash/persistence problems stop the run. Complete
provider responses and request IDs are preserved, including failures.

Guarded outputs are inserted only into permitted helper bodies and verified as
whole repositories with unchanged contracts/clients/providers and all included
files, strict exit categories and a 60-second timeout. A provider `max_tokens`
stop is recorded as truncation without attempted completion or repair. This is
an explicit implementation of the frozen truncation-failure category. The raw
response remains available for any separately labeled later diagnostic.

**21 local tests passed** ([full fake-only log](runner-tests.log)), including exact
24-request order, ambiguous-error stopping, before/after-reservation deadlines,
disk-write failures, exhausted/reopened ledger refusal, no SDK retries, input
hash changes, protected bodies, truncation accounting, and saved-evidence audit
with tamper rejection. These tests use fake providers/verifiers, not model or
Dafny results. The [environment preflight](environment_preflight.py) additionally
checks real SDK configuration, isolated imports and exact staging with fake
transports/processes on Cannon before submission. It passed all three selected
tests plus SDK/import/staging checks ([Cannon log](environment-preflight.log)).

The [Slurm script](model.sbatch) requests two CPUs, 8 GB and two hours, no requeue.
The live `test` partition must report `PreemptMode=OFF` before submission. The
private credential handoff is consumed/deleted once by the compute process and
kept only in that process's environment, cleared on normal/error exit; it is not
copied into evidence. No provider connectivity request is made. Cluster jobs
can finish independently of local monitoring.

After completion, [the offline reviewer](review_results.py) checked exact frozen
payloads/order, request counts and IDs, deadlines, original response metadata,
guard reconstruction, protected files, candidate hashes, verifier commands and
accepted records. All sources, raw responses, extraction decisions, stdout/stderr,
ledger, environment and accounting are archived in [model-001](model-001) and
linked from the results. Failed evidence is retained; no silent repair or rescoring.

Analysis reports every task's four cells and each family's eight distinct
configuration outcomes, alongside reserved/dispatched/returned/admitted/verified
denominators and copied separate bodies. All instances are development tasks;
one sample per variant does not estimate sampling variance. Shared/separate
output workloads differ and copying is allowed; reference depth is not proved
minimal. No causal sharing/depth or held-out claim, and no larger collection is
authorized by this pilot.
