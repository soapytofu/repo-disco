# Authorized eight-call execution: submitted once

**Job 56210087 submitted October 29 at 19:47:24 UTC** on test with live
PreemptMode=OFF. authorization.json binds eight calls and no retries to the frozen
scope/runtime; submission.json records the sole submission. Results are pending.
The preparation history below is retained. No additional job or calls are authorized.

The user explicitly approved the eight-call pilot with no retries. This execution
record supersedes the original preparation-only authorization status in README.md
and the frozen proposal; those historical files remain unchanged.

## Ready

- Exact scope: eight fixed deep shared/separate trials across four families, with
  unchanged clarified prompts, parser and inference settings.
- run_pilot.py has a hard eight-call limit, durable reserve-before-dispatch ledger,
  one SDK attempt, per-request deadline/integrity checks, fresh contexts and no
  resume, feedback, replacement samples or automatic expansion.
- Fifteen local tests pass with fake transport/verifier. The runtime snapshot
  pins runner, request gate, tests/log, Slurm script, audit/report code and verifier.
- Three additional fake SDK/parser tests passed in the real Cannon environment.
  No provider request or Dafny verification occurred in these environment tests.
- Runtime staged once at ~/formal-disco/outputs/monorepo-syntax-smoke-001.
  No model output, submission or credential consumption has occurred yet.

The existing repodisco-codex-8.sock connection was reachable. The private handoff
was absent, so the user was asked to recreate it with the existing prepare_key.py
helper. Never put the key in chat, logs or Git. The compute process will consume
and delete the temporary handoff and clear the key from its environment on exit.

## Before submission

After key readiness, inspect remote output/ledger/submission/queue state, recheck
all hashes and the live nonpreemptible partition, and write an authorization record
binding the explicit eight-call approval to the scope and runtime hashes with a
fresh expiry. Create a unique submission lock and submit model.sbatch once.
The proposed job has two CPUs, 8 GB, a 30-minute limit and no requeue. No connectivity
model calls. Never submit a separate alternative runner or automatically recover.

## Evidence and acceptance

After completion or failure, preserve all responses and errors, request IDs,
retry metadata, usage, extraction decisions, admitted source and raw verifier logs.
review_results.py replays exact messages/guard assembly, validates protected bytes,
accepted hashes and verifier exit categories, then evaluates the predeclared syntax
readiness gate. summarize.py produces the report. Publish full non-secret evidence.
No future 32-call batch follows automatically; unused calls cannot be reassigned.

Two local submission-command attempts failed on disk space before reaching SSH
or sbatch. A redundant temporary dataset download was removed only after all 1,625
files were matched byte-for-byte to existing local copies. The subsequent command
rechecked remote state and submitted once; these local failures caused no requests
or Slurm jobs. No experimental evidence was removed.

## Scheduler adjustment and local disk limitation

The mixed test/shared/sapphire update failed. A subsequent in-place change to
sapphire succeeded, with live PreemptMode=OFF; job 56210087 retained 2 CPUs,
8 GB, 30 minutes, no requeue and the eight-call cap. Both attempts are archived
in scheduling-adjustment-001.json and scheduling-adjustment-002.json. No new job
was submitted. The latest observed state is pending, without a start estimate.

The local Mac disk filled again and prevented Git from creating its lock file.
Submission and scheduling evidence were therefore published through the GitHub
connection after verifying the account's author/committer identity. The local
checkout is behind the remote API commits and needs synchronization after space
is available; preserve local edits and compare them with the remote before syncing.
Cluster outputs remain independent of the local disk. No model results yet.

## Local checkout synchronized

At 2026-10-29T20:14:44.691511+00:00, sufficient space was
available to fetch and fast-forward the local checkout. All four local submission
edits were first verified byte-for-byte against published commit 2337a72; no
unpublished edits were discarded. The checkout is synchronized with the GitHub
evidence through 59304b4. Disk space remains limited (about 131 MiB at the check).
Job 56210087 was still pending on sapphire; no result is claimed.
