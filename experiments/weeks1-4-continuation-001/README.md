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
