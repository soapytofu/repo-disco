# Frozen 32-call monorepo calibration — bounded execution

The user authorized the 32-call pilot on October 28, 2026, with frozen prompts and
no retries, plus two hours of monitoring/analysis through October 29 01:47:35 UTC
(October 28 9:47 PM Eastern). This budget is **32 total**, not per follow-up.
It does not authorize feedback repair, replacements, or the later main corpus.

The exact prior proposal is copied byte-for-byte into frozen-001; its freeze hash
is `85166dc676861ac7288006668bf5b9eef6c137e01c1daeda6c95946d4995da81`
(published in 48cc75a). Prompts, source, guard, trial order, model/settings and
scoring policy are unchanged. The original proposal record remains labeled as a
proposal; execution permission is separately recorded in hash-bound authorization.

run_pilot.py uses the previously tested durable request gate with an explicit
one-attempt Bedrock SDK configuration. It validates frozen/runtime hashes before
every dispatch, logs exact system/user messages, reserves each request before
transport, and preserves raw response text/content, request IDs, usage and retries.
Each trial has fresh seed files and fresh context, no feedback from any other trial.
The CLI refuses an existing output directory; the request gate refuses an existing
ledger. No automatic retry, restart, requeue or reassignment is supported.

Normal output/guard, frontend and proof failures remain completed trial outcomes.
A transport ambiguity, duplicated/missing request ID, nonzero SDK retry count,
source drift, verifier timeout or execution error stops the batch. An interrupted
or reserved request is not replaced. The fixed 32-trial denominator and completed
responses/reservations are reported separately.

The key is consumed from the private handoff only inside the compute process,
deleted immediately and held in memory; it is never archived. Guarded candidate
files are staged and verified once with --verify-included-files, timeout 30s,
Dafny 4.11.0 / Z3 4.12.1. Only strict exit zero with intact sources is accepted.

Twelve local fake-transport/verifier tests passed: exact 32-dispatch order/payloads,
no retry after timeout, normal failure continuation, infrastructure stop, hash and
metadata checks, deadline/restart refusal, authorization binding, and SDK retry
configuration. These tests make zero model requests and run no Dafny processes.
The same twelve tests also passed in Cannon’s actual repodisco environment
(137.806s on its network filesystem). A local SSH wait expired while those tests
continued; their completed log was retrieved without rerunning them. No provider
or Dafny calls occurred. The private handoff is confirmed ready, and a separate
32-call authorization is bound to both freeze hashes and the two-hour deadline.
Submission is the next step; output/ledger and queue must be checked first.

Artifacts on completion: model-001 contains a copy of the frozen inputs/runtime,
authorization/environment, durable ledger, every raw response and per-trial
extraction/candidate/verifier/accepted records. Full non-secret logs and a grouped
family × depth × sharing analysis will be published without dropping failures.

## Submission

Job **56019657** submitted once at 2026-10-28 23:57:26 UTC on test, confirmed
PreemptMode=OFF, 2 CPUs / 8 GiB / 2 hours, no requeue. The exclusive submission
lock and saved job ID prevent duplicate dispatch. Maximum 32 calls; every dispatch
is also bounded by the 2026-10-29 01:47:35 UTC authorization deadline.
Results pending. Do not resubmit or launch a standalone runner.

## Completed original pilot

Job56019657 completed in **7m20s**, exit0: all32requests,32uniqueIDs,zeroSDKretries,
101,595tokens. Full frozen/runtime/source/guard/request evidence reviewed.
[Results](RESULTS.md): **18/32** strict successes;14output rejections and no
verifier failures among admitted candidates. Family totals: conditional0/8,
sequence3/8,relational7/8,map8/8. This is output-policy-confounded calibration,
not evidence of a reasoning-depth effect. Raw failures remain in model-001.
A separate non-paid diagnostic is pending; the frozen score stays unchanged.
