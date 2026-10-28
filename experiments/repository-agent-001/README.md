# Sequential repository repair agent: control validation

The agent now connects deterministic full-source/map context, a bounded injected
request interface, task-specific parsers and guards, real whole-repository
verification, failure feedback and immutable revision promotion.

`repository_agent.py` stores complete revisions and atomically replaces a single
HEAD pointer under a POSIX advisory lock. Failed edits/proofs leave HEAD unchanged;
stale base revisions and mismatched verification hashes cannot be promoted. A
crash before HEAD publication may leave an unreferenced revision but exposes no
partially updated repository. This is a local cooperating-writer contract, not a
distributed transaction or in-place update of Formal Disco's agenda objects.

The base is verified first. Already-verified inputs use no requests; non-proof
execution errors stop. Subsequent attempts use the original base plus the latest
failure feedback. Accepted candidates preserve protected files and contracts.
The declared dependency map is supplied task metadata, not inferred semantics.

## Current validation

28 related offline test methods pass, including nine agent methods. These cover
failure-feedback-success, rejected contracts, timeout/budget stops, stale updates,
source corruption, verified-source hash mismatch and simulated HEAD-write failure.

The submitted compute controls use **saved scripted responses**, not a model:
for each of two families × two sharing conditions, try a contract-changing edit,
a known incorrect proof, then the reference proof. Expected: edit rejection,
proof failure, successful atomic promotion; original revision remains intact.
Twelve scripted requests and twelve verifier calls (including four initial
checks), zero model/API calls. Real model-driven behavior is still unvalidated.
The fixture/guard/API source snapshots are pinned alongside the runner.

The agent deliberately starts with repository repair. Autonomous creation of new
modules, extension task scheduling, context selection and growing generated
repositories remain needed to demonstrate the proposal's beginning-to-scale
component. Existing controlled variants do not constitute autonomous generation.

## Prepared live pilot (authorized continuation; not yet run)

Verifier-only job **55802594** completed on test in 75 seconds, with no requeue.
`repository_agent_pilot.py` and frozen-model-001 pin four development tasks:
branch/shared, inductive/separate, branch/separate, inductive/shared. Each gets at
most two feedback-driven attempts, stopping on success; unused calls are not
reassigned. **At most eight additional requests**, separate from the baseline,
were subsequently authorized by the request for automatic wrap-up while asleep.
Compute controls must still pass; no requests made yet. See
[combined continuation](../weeks1-4-continuation-001/README.md).

Opus 4.5 via Bedrock, temperature 1.0, 4,096 output tokens, complete source plus
declared dependency map and explicit permitted grammar. Three adapter tests pass:
all four reference repairs survive the frozen parsers byte-exactly, all contract
changes are rejected, and final chat messages preserve context and identity.
Actual messages enter the durable request ledger. Failed revisions, diagnostics,
responses and final accepted HEAD are saved. No automatic retries or resume.
This tests integration, not a powered sharing effect or independent pass@2.

## Scheduling adjustment (October 28)

At the user's request, pending job 55802594 was updated in place from
shared/sapphire to **test alone**. No duplicate submission, cancellation, resource
reduction, or time-limit change. Requeue remains disabled. Live cluster inspection
confirmed test PreemptMode=OFF, PriorityTier=5 and 12-hour maximum; both small
verifier-only jobs fit its limits. Original submission files are preserved; the
update command and before/after scheduler state are in scheduling-adjustment-001.json.
Harvard forbids combining test with other partitions. The paid continuation still
targets shared/sapphire.

Reference: [FASRC running jobs](https://docs.rc.fas.harvard.edu/kb/running-jobs/#test).

## Reviewed compute results

All **four cases** passed the intended sequence: contract edit rejected before
verification, incorrect proof rejected by Dafny, exact reference repair accepted
as a complete revision. **Twelve verifier checks** matched expectations (four
initial failures, four candidate proof failures, four successes), plus four edit
rejections. Original revisions remained byte-exact and final HEADs pointed only
to verified reference bytes. Twelve scripted responses, **zero model calls**.

`review_controls.py` checked 66 pinned source/guard/fixture files, every candidate
hash against its verifier record, request/context/response correspondence,
proof-error categories and accepted/original revisions. Full evidence is in
verification-001; control-review.json and verification-001-sha256.json record the
review and archive integrity. model-preflight-gate.json now permits the prepared
agent pilot after the baseline gate; it does not itself submit or spend calls.

## Completed live model pilot

Job 55807561 repaired all four frozen development repositories on the first
model attempt (four requests, no retries; four unused calls not reassigned).
Both branching and inductive tasks succeeded under shared and separate views.
The reviewed full model-001 archive includes prompts, raw responses, guarded
candidates, whole-repository diagnostics and original/accepted revisions.
Contract guards were replayed offline and source hashes match the accepted HEADs.
This demonstrates the live agent integration; it does not estimate a sharing effect.
