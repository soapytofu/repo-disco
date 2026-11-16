# Harness control results — November 16, 2026

**All seven native/adapter comparisons agree, and the omitted-file control is
rejected correctly. Zero model calls. No online repository is qualified yet.**

Job **61247644** completed in 42 seconds on Cannon shared (`holy7c04202`). It was
submitted once, without requeue, and moved in place from test after the scheduler
reported unavailable nodes and inspection showed its nodes draining. Both
partition inspections reported `PreemptMode=OFF`. The original submission script,
receipts and scheduling adjustment are preserved; no verifier command was retried.

| Control | Direct native command | Adapter classification / decision |
| --- | --- | --- |
| Correct workspace | 5 verified, 0 errors, exit 0 | VERIFIED; all five required units pass |
| Unproved helper, passing client | Helper.Transfer Failed; Client.Target Passed, exit 4 | PROOF_FAILURE; reject whole-workspace success |
| Proved helper, failing client | Helper.Transfer Passed; Client.Target Failed, exit 4 | PROOF_FAILURE |
| Detached failing file, explicit all-file inputs | Detached.Broken Failed, exit 4 | PROOF_FAILURE; detached obligation is checked |
| Same files, entry-only native command | 5 verified, 0 errors, exit 0; detached file absent from results | Rejected as full-scope evidence: verification input command differs |
| Existing warning candidate | 16 verified, 0 errors, 4 warnings, exit 2 | WARNING_ONLY; complete proof-unit coverage, no strict success |
| Invalid top-level syntax | Parse errors, exit 2 | PARSE_FAILURE; no proof success inferred |
| Undefined member call | Resolution/type error, exit 2 | RESOLUTION_OR_TYPE_FAILURE; no proof success inferred |

The experiment has **15 native invocations**: seven pairs plus the entry-only
coverage control. `review-001.json` passes 22 assertions (14 outcome reviews,
seven agreements, one incomplete-command rejection). These counts are control
checks, not independent mathematical tasks or model-performance observations.
Named unit outcomes and warning counts match in each pair; raw text contains
distinct temporary paths and resource/timing measurements, as expected.

The omitted-file result directly demonstrates why staging/hashing alone is
insufficient. Explicit file arguments expose the failure, and the proof inventory
binds it to `Detached.Broken`. The helper control separately demonstrates why a
locally passing client cannot establish a fully verified workspace.

## Integrity, timing and evidence

Thirteen offline tests passed locally and on Cannon before dispatch. They cover
actual pinned method-policy rejection of changed headers and verification
bypasses, source/command/toolchain/run identity mismatches, missing/duplicate/
unknown units, missing streams, summary disagreement, warning categories and
fake-process timeout/resource/infrastructure failures. Synthetic categories are
not reported as actual cluster timeout observations.

The adapter observations took 0.56–2.73 seconds, with recorded peak RSS of
65,432–132,276 KiB. None timed out. The adapter timer includes staging and evidence
capture; the independent direct timer wraps process execution. Version probes
are outside both reported intervals. These are operational measurements on small
controls, not an overhead comparison or performance estimate for online projects.
CSV files separately retain per-unit duration and solver resource counts.

The 154-file transfer contains 148 source/raw/evidence files under
`verification-001`, plus scheduler logs, submission/preflight records and
accounting. Review checks every observation's exact source/profile and decoded
raw hashes, actual Dafny/Z3 versions, required named results and immutable bundle
manifests. The copied preexisting fixture/policy inputs remain byte-identical.
The saved warning candidate is unchanged; no historical model score is revised.

- Runtime manifest SHA-256: `71e73ee409c243dc37de9bcf2d045123d1b8be6fd54f37c615e98aac07cd1889`
- Fixture manifest SHA-256: `289a9d9194f638c8f5c156ec2fd2da4e7ca67ee6be8ca9367b3578d680893f1f`
- Review: [review-001.json](review-001.json)
- Full observations: [verification-001](verification-001)
- Transfer inventory: [transfer-001.json](transfer-001.json)

## Remaining prerequisite

This validates a limited Dafny 4.11.0 adapter on constructed development controls.
It does not qualify Dafny-VMC's 4.4.0 configuration, the standard-library build,
Vest or pmemlog. Each needs the real-source/toolchain/coverage/guard controls in
[README.md](README.md) before any model collection. The current adapter fails
closed for unsupported versions and Verus. No real-repository paid handler or
execution authorization exists, and the old terminal model ledger is unchanged.
