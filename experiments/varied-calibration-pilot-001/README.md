# Varied calibration: authorized 32-call pilot

The user approved **32 new Claude requests, no retries**, on November 10, 2026.
The runner is tested and staged on Cannon; no live request has been dispatched
at this publication. A fresh hash-bound authorization and one compute submission
are the remaining execution steps.

This executes the existing [frozen proposal](../varied-calibration-plan-001/README.md):
bounded allocation, map swap, clamp distance and prefix splitting, each in
shallow/deep × shared/separate workspaces, with two fresh-context responses per
workspace. The original proposal's authorization flag remains historical;
execution authorization is recorded separately here. No reserved test family is
included.

## Frozen inputs and prerequisites

- Proposal freeze SHA256: `db299e947d4a5b62fcc7f57d1a8dd374dfcef027789352d88eabded7072eb7b8`.
- Runtime freeze SHA256: `a4d80fb8a97ba2881278c6c51193db754eb82e7d39920bbccf9ea162e33058ff`.
- [readiness-gate.json](readiness-gate.json) binds the published 126 expected
  fixture outcomes and 16 strict alternative-proof successes, with exact source,
  policy and verifier hashes. Alternative proofs are analyst-authored controls.
- [frozen-001/trials.json](frozen-001/trials.json) fixes all 32 slots and request
  hashes. The 16 exact payloads, seed sources and output policies are unchanged.
- [stage-001.json](stage-001.json) records the verified remote copy;
  [environment-preflight.log](environment-preflight.log) records successful real
  package imports with fake transport and fake verifier processes: zero API
  requests and zero Dafny invocations.

The pinned model is `global.anthropic.claude-opus-4-5-20251101-v1:0`, region
`us-east-1`, temperature 1.0, maximum 4,096 generated tokens per request. This
inherits the reviewed proposal; it is not a current-model recommendation.

## Execution and logging

[run_pilot.py](run_pilot.py) uses the existing [bounded request gate](bounded_requests.py).
It reserves each call durably before dispatch, checks the absolute deadline at
every reservation, permits one SDK attempt and stops on ambiguous or unsaved
responses. The cap is 32 total requests; unused slots cannot be reassigned.
There is no restart, retry, feedback or automatic requeue. Completed extraction,
guard, proof or warning failures consume their original slots.

Independent offline test groups ran concurrently; live requests remain sequential
to preserve the frozen trial order and single-owner ledger. [runner-tests.log](runner-tests.log)
contains all 16 passing test methods, including full fake 32-request collection
and review, timeouts, metadata failures, duplicate IDs, persistence failures,
deadline boundaries, protected sources and exact parsed reference reconstruction.
All transports and verifier processes in these tests were fake.

[model.sbatch](model.sbatch) requests one non-requeued compute job with two CPUs,
8 GB RAM and three hours. Submission checks the live partition's
`PreemptMode=OFF`, existing submission/output records and matching job name before
creating an exclusive lock and calling `sbatch` once. The runner consumes and
deletes the private key handoff; credentials are never written to the archive.

Every response retains its provider request ID, SDK retry metadata, usage, raw
content, extraction decision and guarded candidate. Dafny runs only on the
compute node, with the pinned 4.11.0/Z3 4.12.1 toolchain, a 60-second limit and
`--verify-included-files`. Primary success requires strict exit zero, zero errors
and no warnings. [review_results.py](review_results.py) independently replays
extraction and checks frozen bytes, dispatch order, IDs, candidates and evidence.

## Interpretation

Report all 16 workspace cells and their individual outcomes. Two responses per
cell are calibration observations, not a general causal depth or sharing result.
Separate mode permits copied proofs and requires two editable bodies; shared
mode requires one. Reference contract paths do not establish minimum necessary
reasoning depth. All four instances belong to inspected development families.
Any later analyst repair must remain separate from the original model score.
