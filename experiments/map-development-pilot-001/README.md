# Bounded map-development pilot — submitted

November 12, 2026. Prepared for the [frozen 16-call proposal](../map-development-plan-001/README.md).
Sophie explicitly approved **16 new calls, no retries**, then reported the private
key handoff ready. Job **60045391** was submitted once on live-confirmed
nonpreemptible test at 18:48:58 UTC. Results are pending review.
All 19 offline runner tests pass. Cannon's real environment preflight also passes
with fake transport and a fake verifier: zero API requests and zero Dafny runs.
The existing authenticated socket 14 worked; no reconnection was needed.
[authorization.json](authorization.json) binds the exact scope and deadline;
[submission.json](submission.json) records the live partition and exclusive job.

## Scope and pins

- Two inspected map instances × four structural cells × two fresh samples:
  **16 proposed requests total**, no retries, feedback, reassignment or requeue.
- Proposal SHA256:
  `84211b3fd2286cc0b6c8cb5b139c6856dc214270c09762c9dcc0f03f0fbe2097`.
- Runtime SHA256:
  `dec461e6057ba6ded5a34cc020ac3c90e134789e37d96d2a0bd62f7676542f99`.
- [readiness-gate.json](readiness-gate.json) binds 76 reviewed fixture outcomes
  and five analyst measurement controls. Exact frozen sources, policy, order and
  payloads are copied without changes.
- [stage-001.json](stage-001.json) records the exclusive staged runtime at
  `~/formal-disco/outputs/map-development-pilot-001`.

These calls would use 16 of the previously proposed 64 development-collection
slots. Old budgets cannot be reused. Execution is authorized by the subsequent explicit human approval recorded
here, not by staging or testing.

## Runtime behavior

`run_pilot.py` requires a fresh human authorization bound to both hashes with a
finite expiry no more than 24 hours ahead. It verifies frozen inputs and runtime
before every request. The unchanged durable request gate reserves before dispatch,
uses exactly one SDK attempt, and refuses restart or a reused ledger. Live calls
are sequential to preserve order. Ambiguous transport, disk or infrastructure
failures stop collection without replacement calls.

The compute entry point requires Slurm, checks the pinned Dafny/Z3 versions, and
only then consumes/deletes a private key handoff. It clears the process token at
exit and never includes it in archives. The submission tool checks existing
outputs/locks/jobs and live `test PreemptMode=OFF`, creates an exclusive lock and
submits once. The prepared job requests two CPUs, 8 GB and one hour, no requeue.
The one authorized submission is recorded above; no alternate runner was launched.

The verifier function is copied exactly from the measured logging diagnostic.
The interpreter is a byte-identical copy of its reviewed source. All includes
are verified, with the same 60-second bound and strict exit-zero/no-warning rule.
Raw CSV, stdout/stderr, guarded source bytes and hashes are archived. Each named
helper's obligations are grouped; supplied clients/providers receive no edit
credit. Missing or misattributed logger data stops further dispatch while
preserving the actual strict verifier outcome separately.

Model responses preserve request IDs, retry metadata, usage, exact content,
extraction decisions and candidate hashes. `review_results.py` independently
replays edits and target metrics, checks raw CSV bytes, source protection,
dispatch order and unique IDs. Ordinary guard/proof/warning failures remain
completed outcomes, not opportunities for retries.

## Validation and limitations

[19 passing tests](runner-tests.log) cover fake 16-request collection, cap,
deadlines, timeout ambiguity, persistence failures, metadata errors, immutability,
reference reconstruction, measurement failures and full archive review/tampering.
The [initial test run](runner-tests-001.log) caught CRLF normalization during CSV
review. Saving/comparing UTF-8 bytes fixed that mismatch; the failed test evidence
is retained. Frozen task/prompt/parser bytes were unchanged.

[Cannon environment preflight](environment-preflight.log) uses installed
boto3/botocore 1.43.115 with an injected fake client and fake process. It confirms
one SDK attempt and exact staged files/logger capture. It does not test live
provider availability or claim model performance.

Only the two development instances are included. Their shared/separate workloads
differ, proofs can be copied, and interface labels are not minimum proof depths.
The earlier 27/32 swap calibration and analyst diagnostics remain unchanged.
A future completed batch can test recurrence and descriptive contrasts; it
cannot alone establish a general causal sharing/depth result.
