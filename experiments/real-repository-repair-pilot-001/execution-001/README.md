# Approved sixteen-call execution

The user approved **16 new Claude calls with no retries** for the existing
Dafny-VMC/Vest prompt freeze. This additive execution bundle leaves every
proposal payload, task, guard and qualification profile unchanged. Historical
proposal text records its earlier unauthorized state; the separate fresh
`authorization.json` binds the current approval to both manifest hashes.
The prior terminal paid session remains closed and supplies no slots here.

Four tasks × two feedback arms × two fresh responses = sixteen one-shot slots.
There are no iterative repairs, automatic retries, reassigned slots, availability
requests, or alternate clients. `collect.py` passes each exact Converse payload
through the existing durable single-owner request gate. SDK total attempts is
one. The compute process consumes the private handoff once and clears its key
environment on exit. A transport ambiguity closes the ledger; its missing answer
has no proof score. A rejected or truncated returned output consumes its slot.
The runner cannot resume an existing output directory or ledger.

## CPU and memory allocations

| Distinct stage | CPUs | Memory | Wall limit | Actual concurrency |
| --- | ---: | ---: | ---: | --- |
| Model collection | 1 | 2 GB | 60 min | One request at a time; no verifier |
| Dafny candidates | 1 | 2 GB | 30 min | One native command at a time |
| Vest candidates | 4 | 4 GB | 150 min | One native command; frozen three Verus threads and four Cargo build workers |

All stages use one node, one task, no requeue, and an explicit live check for a
nonpreemptible partition. The coordinator prefers `test` when its current time
limit is sufficient, otherwise `shared`. The collection and verifier stages have
different scopes and independent exclusive submission locks. They are not retries
of the same job. No cores are reserved for verification during provider waits.
The Vest allowance respects explicit parallelism; it is not a prediction of
100% utilization. Retain GNU time and Slurm allocation/TotalCPU/elapsed/RSS data
for actual efficiency reporting. No frozen verifier flags are changed.

## Evidence and acceptance

The collection review checks exact prompts, slot order, durable reservations,
native response metadata, request ID uniqueness, zero SDK retries, token totals,
and byte-exact guard replay. It binds every collected file and admitted candidate
in a separate `verification-gate.json` before either verifier job is submitted.

Each candidate gets a fresh copy of the pinned upstream tree and (for Vest) a
fresh build target. Only its registered body may differ. All upstream files and
build inputs are checked before and after verification; tool/image closures are
checked before work. The native command, entire required proof inventory,
source hashes, stdout, stderr, CSV/JSON and resources are preserved. The offline
review reconstructs each expected profile and reruns the frozen observer against
those saved bytes. A passing client cannot hide a failed provider.

Primary success is verification of the **qualified declared scope with only the
reviewed upstream warnings**. It is not whole Git-tree coverage or zero warnings.
Guard rejection, truncation, frontend/proof/resource/infrastructure failure,
missing coverage and new warnings remain separate. Success writes an acceptance
receipt, not a live upstream promotion. Accepted bodies still receive a manual
intent/specification review. These four induced development failures do not
establish held-out performance or a controlled language comparison.

`test_execution.py` uses fake transports and saved native evidence, including a
fake worker integration. Tests do not call an API or run Dafny/Verus. `preflight.py`
repeats those checks in the actual Python/SDK environment without creating a live
client. `ops.py` stages once, submits once per distinct stage, and fetches only
terminal job evidence. A timed-out submission requires read-only reconciliation;
it is never automatically repeated. Full result publication follows actual
collection and verification, not merely passing these offline tests.

## Operations

1. Validate and publish the runtime; stage it and pass the remote offline preflight.
2. Write a fresh approval record, bound to the proposal/runtime and expiring within
   24 hours. Upload it, confirm the private handoff exists without reading it, and
   submit `collect.sbatch` once through `ops.py submit collect`.
3. On terminal status, fetch and review collection evidence. Preserve any stop.
   Upload the reviewed verification gate; submit each admitted repository scope
   once using its separately sized script.
4. Fetch terminal verifier evidence, replay both scope reviews, inspect accepted
   bodies and publish all nonsecret results, logs and accounting. Never recover
   an ambiguous model request or rescore an analyst correction as model success.
