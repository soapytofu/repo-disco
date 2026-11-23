# AWS error-logging runner preparation

Subsequent authorized collection: [one returned candidate and a terminal
resource failure, with full evidence](COLLECTION.md). The preparation record
below describes the earlier offline-only checkpoint.

Prepared November 23, 2026. This is **offline runner qualification**, with no
model requests, native verifier runs, authorization file or job submission.
The private key handoff was not inspected or consumed. No live AWS access test
has established that the replacement key can invoke the frozen model.

The new execution-004 runtime preserves the eight-slot growth proposal and adds
bounded, redacted AWS failure evidence. The prior execution-001 and execution-003
ledgers remain closed, with their original unscored reservations and zero returned
responses. This preparation does not resume them or produce a growth score.

## Validation evidence

| Check | Observed outcome | Full evidence |
| --- | --- | --- |
| Final local fake-transport/process suite | 98/98 passed in 128.365 seconds | [Local log](reviews/local-draft-003/unit-tests.log), [complete result](reviews/local-draft-003/result.json) |
| Local installed-SDK checks | Explicitly skipped: boto3/botocore unavailable locally | [SDK record](reviews/local-draft-003/sdk-auth-regression.json) |
| Cannon installed-SDK regression | Five scenarios passed; boto3/botocore 1.43.115; zero socket connection attempts, provider requests or real credential reads | [Complete SDK record](reviews/cannon-preflight-001/sdk-auth-regression.json) |
| Cannon frozen-package suite | 98/98 passed in 539.715 seconds; no timeout; process group reaped | [Cannon log](reviews/cannon-preflight-001/unit-tests.log), [raw preflight](remote-preflight-001.json) |

The SDK tests use empty temporary configuration, dummy tokens, intercepted HTTP
responses and forbidden socket connections. They reproduce the old token-lifetime
defect, exercise two synthetic successful responses, and check terminal connection,
403 access-denied and 429 throttling errors. Both service-error cases retain the
bounded metadata, redact the dummy token and make exactly one intercepted attempt.
These are SDK behavior tests, not a key check or model-generation result.
Cannon used Python 3.11.17; the complete preflight, including its final source
recheck, recorded 575.010 seconds. Local and Cannon stdout/stderr, package
versions and exact test source hashes are preserved. The
[final preparation review](preparation-review-001.json) binds these records.

The 98-test suite includes 13 new integration tests plus the nine previously
reviewed pure-extractor tests. It checks source/request/reservation binding,
literal token redaction, null missing metadata, terminal behavior after logging
failures, partial-file handling and rejection of missing or relabelled evidence.
Existing parent provenance, protected edits, native coverage, no-retry and
single-submission checks remain in the suite. Synthetic proof/model fixtures are
explicit and never counted as native or model observations.

## What changed

The transport now retains only error code, a message of at most 512 characters,
request ID, HTTP status and SDK retry metadata. It redacts the loaded bearer token
and previously visible bearer token before truncation; it never emits exception
representations, headers or environment dumps. Unknown fields remain null. This
is literal redaction of supplied strings, not detection of arbitrary secrets.

After the unchanged request gate closes, the host can save
`slot-NN/transport-error.json`. The record is bound to the exact runtime, run,
slot, request and terminal reservation. Its persistence status distinguishes
saved, unavailable, capture-failed and write-failed diagnostics. Extraction or
disk errors preserve the original failure and cannot trigger another request.
The reviewer validates the record without turning it into a model response,
accepted revision or proof score. The earlier denial's missing metadata cannot
be recovered by this change.

## Preservation and scope

- Runtime freeze: `09766d4b2808caa567f31e18fbb50f599e02efb901ec7ccdc11b96e25572a266`.
- Prompt freeze remains `9f2e4c9602b4ce98740f2a3fa1dcf7bbef07d2b0693db8d92d9cc55546820f0c`.
- Parent protocol remains `9cf8cc81bd55f83a591c04c2877ab9a0ece3927fcddc31f6f3d42d7953d42057`.
- All 4,170 new runtime pins and 4,164 prior execution-003 pins were checked before staging and after qualification. The request gate, native adapter and pure metadata extractor are byte-identical to their recorded origins.
- Model settings, frozen prompts/order, protected contracts, native coverage, actual accepted-parent requirements and resource limits are unchanged. A failed parent blocks its child; no unused slot transfers to another task.
- Prospective resources remain one CPU, 8 GB, four hours and no requeue; Dafny uses limit 100,000/wall 300 seconds, and Vest one Cargo worker/one Verus thread/wall 900 seconds. SDK total attempts remain one.

The exact package was [staged once](stage-001.json) in the separate execution-004
directory. Its exclusive fake-only preflight passed without reading the handoff,
authorizing execution or submitting Slurm work. Future collection needs a separate explicit
decision bound to this runtime; no new paid scope is created here.

## Preserved preparation history

The first local invocation used macOS's symlinked `/tmp` alias and was rejected
before tests; the canonical `/private/tmp` path was used thereafter. The first
full suite had one inherited preservation-test failure: it still required the
logging files to be unchanged, as appropriate for the previous namespace-only
revision. The test now requires exact unchanged gate/native/extractor copies,
declares the intentional logging changes and binds their old hashes and unchanged
prompt/protocol identities. No production code changed in that correction.
All 98 final tests passed. Original logs and the original test are retained in
[local-draft-001](reviews/local-draft-001/),
[local-draft-002](reviews/local-draft-002/) and the
[correction record](reviews/correction-001.json).

See the [source diff](reviews/source-diff-001.patch) and
[pre-staging review](reviews/source-review-before-stage-001.json). Historical
scores and source archives are unchanged. Sequential model growth remains
unmeasured until a separately approved collection returns and verifies additions.
