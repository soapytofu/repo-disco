# Authorized eight-call execution: runner ready, awaiting private key

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
