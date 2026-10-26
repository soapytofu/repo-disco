# Subsequent execution authorization

The user authorized running the eight frozen prompts and monitoring for two hours, ending 2026-10-24 04:28:24 UTC. The preparation README/protocol retain their historical zero-authorization state because they are frozen. `authorization.json` supersedes that status only. No prompts, parser, trial order, sources or model settings changed.

The bounded adapter uses one fixed `model-001` directory, refuses restart, persists dispatch state before each API request, checks frozen hashes before every trial, and stops on API errors or verifier infrastructure failures. SDK retries and Slurm requeue are disabled. Credentials are loaded from the private handoff, deleted from disk, and cleared from the process environment on exit; they are never logged. The adapter checks the execution deadline before starting. A submitted run can finish beyond the monitoring deadline.

`preflight-gate.json` records the prior 76-control compute verification and exact equality between the frozen task inputs and those verified fixtures. Three adapter tests use mocked transport only and cover the eight-call cap, exact prompt order, durable logging, restart prevention, API-error stop, and verifier-timeout stop. Frozen bundle tests are rerun unchanged.

Status at preparation: awaiting private credential handoff. No live requests dispatched or job submitted yet. Subsequent `submission.json` and `model-001/ledger.json` are authoritative for actual execution state. The five-minute chat follow-up monitors this experiment until completion or the deadline, without authorizing extra calls.

## Renewed window

On 2026-10-26 at 02:32:41 UTC the user confirmed the new socket and credential handoff, and renewed the eight-call run plus three hours of monitoring and non-paid follow-up through 05:32:41 UTC. Queue and fixed model-001 path were checked before submission: no prior job or ledger existed. The prior window dispatched no calls. Frozen inputs and adapter settings remain unchanged.

## Completed batch

Job 55298220 completed with exactly eight requests and eight successes. See RESULTS.md and model-review.json. The call budget is exhausted; remaining authorized work in the three-hour window is non-paid only.
