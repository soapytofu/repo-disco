# Independent collection reviewer

The new review_collection.py adapts the prior twelve-response retrospective
reviewer to the frozen eight-slot independent scope. It performs only offline
replay. It cannot call a model/verifier, inspect credentials, issue acceptance,
resume a ledger or replace earlier results.

Production API:

    authority = CollectionAuthority(
        authorization_raw, expected_authorization_sha256,
        claim_raw, expected_claim_sha256,
        budget_raw, expected_budget_sha256,
        expected_slurm_job_id, expected_partition)
    result = review_collection(
        package, model_output,
        expected_runtime_sha256=reviewed_runtime_hash,
        authority=authority)

The host supplies exact artifact bytes and independently reviewed expected
hashes. The reviewer validates the frozen runtime and local dependency bytes,
scope, cumulative allocation, authorization and permanently consumed claim.
Optional archive_root, archive_manifest_raw and expected_archive_sha256 bind
the full transfer inventory too. Without these optional inputs the report
explicitly says full_archive_reviewed=false. The CLI exposes these inputs and
writes a new report exclusively.

Trust is the root-owned collection and reviewed pins. A self-consistent set
of third-party JSON artifacts is not authenticated merely by hashing it.
Changing only an origin label cannot make recorded analyst evidence eligible;
known run/raw exclusions, source/profile pins, fresh request/event binding and
native replay all remain mandatory.

Every completed response must have a unique matching provider request ID,
HTTP 200, zero SDK retries, exact raw content/usage and a frozen prompt replay.
The reviewer reconstructs the body envelope and protected candidate, rechecks
the exact source inventory, native invocation, tool versions, CSV obligations,
warnings, resources and the source-bound native profile. Independent trials
cannot contain parent receipts, child payloads or adaptive continuation files.

Whole-workspace score is emitted only for a complete eight-response collection.
Terminal runs retain accepted/outcome counts but have score=null. Ambiguous
requests without a response have no invented usage or candidate. A response
saved before a failed ledger commit is reported as saved-but-uncommitted and
is never scored. A returned response interrupted before a recorded outcome is
also unscored. Undispatched slots remain separate.

Complete verifier resource exhaustion, mathematical proof failure,
envelope/body rejection and terminal warning/frontend/outer-timeout outcomes
remain distinct. The review follows the frozen host's continuation policy
rather than retrospectively changing it. A partially written native record
cannot earn acceptance; its dispatch/observation boundary is explicit.

All tests use the existing marked synthetic Runner fixtures plus fake
provider-shaped responses and fake native capture records. The private replay
core has an explicit synthetic opt-in; the production API and default core
reject them. Tests cover complete/mixed outcomes, partial/ambiguous accounting,
source/prompt/request/native/summary tampering, omissions, stale analyst runs,
and closed-ledger enforcement. They establish reviewer behavior, not native
proof, provider connectivity or model performance. Full test transcripts and
tested hashes are preserved in the numbered test directories.

The final focused run, tests-003, passed all 21 tests. This includes the
production entry point rejecting a marked synthetic collection after actual
manifest construction, frozen-package validation and exact authority checks.
The test uses the existing explicitly synthetic package/budget fixtures; it
does not mock the reviewer, create a live allocation or claim real acceptance.
Earlier 18- and 20-test transcripts remain preserved. preparation-002.json
records the final sources and dependency hashes for root's integrated freeze.
