# Automatic baseline → repository agent continuation

The user requested automatic Weeks 3–4 wrap-up after the baseline while asleep.
This includes the already prepared eight-call agent pilot: **at most 20 baseline
calls + 8 agent calls total**, with no retries or reassignment. Historical calls
are unrelated and exhausted. No additional model generation budget is inferred.

`weeks14_continuation.py` executes both stages in one compute process after both
queued verifier jobs finish and their evidence is reviewed. It consumes/deletes
the private handoff once, retains the credential only in process memory, and
clears the environment on exit. There is no secret in this repository or script.
The prior baseline and agent freeze mechanisms, prompts, task order, parsers,
guards and budget gates are unchanged. The orchestration itself is additionally
pinned by SHA-256 in authorization.json before submission.

The exact baseline prompt freeze is still pending the dataset preflight.
Authorization binds its hash, the frozen agent plan hash and this driver hash.
Submit run.sbatch once only after checking remote state and recording submission.
Do not submit the standalone baseline or standalone agent runner as well.

An incomplete baseline, API ambiguity, timeout or storage exception prevents
starting the agent stage. Failed baseline proofs or rejected patches are valid
completed evaluation outcomes and do not by themselves prevent the independent
agent pilot. Within the agent, already verified tasks use no requests, each task
has at most two feedback-driven attempts, and failures never promote revisions.
No existing run is resumed automatically. Four offline orchestration tests pass,
including execution of the actual task guards/repair loop with saved responses
and fake verifier; those are not model or real-Dafny results.

After completion review and publish all non-secret ledgers, raw responses,
source edits, specification audits and verifier evidence. Baseline verification
alone must not be labeled faithful annotation repair. Summarize integration
results and remaining Weeks 3–4 work, including generation across multiple repos.
Do not mark all milestones complete from this pilot alone.

Submitted Slurm work survives laptop disconnection. Local monitoring, review and
GitHub publication still require the Mac/app/network and authenticated SSH. A
sleeping laptop may delay submission of this combined job until it wakes.

## Submission

Both verifier gates completed and were reviewed; exact baseline prompts and full
preflight evidence were published in d3602c2 before dispatch. Combined job
**55807561** is submitted to shared/sapphire, two CPUs, 8 GiB, two-hour wall limit,
no requeue. It is the only created paid job. The first submission was rejected
because the completed agent-control job had expired from the Slurm controller;
no job was created and its job-ID file is empty. Both success states were then
confirmed in accounting, and one deliberate corrected submission omitted the
expired scheduler dependency. The in-process reviewed freeze gates remain active.
Both submission attempts and the original remote lock are preserved.

Do not submit either standalone runner, restart this job, or reuse the budget.
Inspect job55807561 and all ledgers before any recovery action. The private key
handoff is deleted when the combined process loads it; no second handoff is needed
for the agent stage during the same successful process.

## Scheduling update

At the user's request, existing job55807561 was moved in place to test alone on
October28 at 02:19 Eastern. It started immediately on holy8a24101. Live partition
configuration confirms PreemptMode=OFF. Two CPUs, 8GiB, two-hour wall limit,
no-requeue and the maximum28 requests are unchanged. No new job or requests were
created by the scheduling update. Preserve the original submission script and
before/after evidence in scheduling-adjustment-001.json.

## Completed and reviewed

Job 55807561 completed on test in 3m58s, exit 0. Exactly **24 requests** completed:
20 baseline and four agent requests, all with unique request IDs and zero SDK
retries. Four unused agent calls remain unused and cannot be reassigned. Total
usage: 38,916 input + 10,214 output = 49,130 tokens.

Baseline: **7/20 legacy successes**, **6/20 zero-exit verifications**, nine rejected
patches, three proof failures and two exit-2 outcomes. One exit-2 outcome is a
warning-only verification success; the other is a front-end failure. The separate
[specification audit](../baseline-reproduction-001/specification-review.md) explains
contract fidelity and inherited weak specifications. This bounded smoke run meets
the initial baseline-run gate; it is not a reproduction of all paper results.

Agent: **4/4 repositories repaired on their first model attempt**. Frozen guards
replayed successfully, original snapshots remain exact, and accepted revisions
match whole-repository verifier hashes. This validates the live integration on
four development tasks, not a causal sharing advantage or an independent pass@2.

review_results.py checks both freezes, archived code/input hashes, actual prompts,
request/response correspondence, patches, guards, immutable originals, accepted
HEADs and verifier evidence without invoking models or Dafny. results-review.json
records that audit. Full raw evidence is in baseline smoke-001, agent model-001
and run-001. Earlier failures and original submissions remain unchanged.

Weeks 3–4 wrap-up still requires the consolidated protocol review and beginning
controlled generation/extension across multiple repositories. No additional model
calls are authorized by this result or by unused per-task allowances.
