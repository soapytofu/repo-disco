# Balanced 32-call calibration execution

**Current status: job 57099049 submitted once on nonpreemptible test.**
Results pending; no requeue, retries or duplicate submission.

Preparation history: user authorized **at most 32 new requests, no retries** on November 2,
2026. Runner preparation and 18 fake-transport/verifier tests are complete.
Staging and three real-environment offline checks passed; hashes and the installed
SDK's single-attempt configuration match. `preflight-review.json` records the
review and `authorization.json` binds the approved 32-call limit to the runtime
with a six-hour dispatch expiry. No model requests or job submission at this
preparation checkpoint. Submission/results updates follow below.

## Bound scope

Uses the unchanged [reviewed proposal](../monorepo-balanced-calibration-001/README.md)
and exact copied freeze
`df6771bf7ac6e81d2201811a84888ca01156eb6974bee4af85d6e2eb67e49c6f`.
Thirty-two fresh contexts cover 16 task configurations twice, preserving all
clarified prompts, source/contracts, parser, model settings and order. Reviewer
analysis and earlier responses never enter messages. No old trial is resumed,
repaired, pooled, replaced or assigned unused quota from a prior budget.

One compute process uses a fresh durable reservation ledger, checks source/runtime
hashes before every request and enforces the authorization deadline before and
after reservation. The SDK has total_max_attempts=1; no connectivity model call,
streaming retry, repair feedback or automatic recovery is permitted. A lost or
ambiguous response closes the gate. Ordinary guard/proof failures consume their
slots and remain outcomes. Metadata errors, persistence/hash drift or verifier
infrastructure failures stop collection for manual review.

The batch requests 2 CPUs, 8 GB and three hours on live-confirmed nonpreemptible
test, without requeue. Three hours allows headroom for 32 bounded request and
verification timeouts; it is not a queue or expected-duration prediction. All
Dafny verification occurs on compute, including verification of included files.
The account-private credential handoff is consumed/unlinked once by the compute
process, kept in its environment only for the run and cleared on normal exit.
Credentials are excluded from snapshots and logs.

## Validation and provenance

`run_pilot.py`/`test_runner.py`/`summarize.py` derive from the completed revised
32-call runner; the request gate, verifier code snapshot and strict outcome audit
derive from the completed eight-call smoke. These earlier files are unchanged.
The new runner binds the new freeze and `balanced-*` trial IDs, enforces the
two-sample policy and adds runtime-budget validation. The audit reports guard
admission, raw proof-diagnostic labels and family floor/ceiling flags.

[runner-tests.log](runner-tests.log) records 18 tests with fake transport/verifier:
exact 32 messages/order, no retry after ambiguous failure, guard/proof/frontend
outcomes, timeout/hash stops, duplicate IDs/retry metadata, exhausted/deadline/
existing ledgers, frozen/runtime drift, authorization pins, SDK request payload,
guarded body boundaries, import isolation, reservation disk failure, deadline
crossing during persistence and scale-up flags. They are not model findings.
`environment_preflight.py` additionally imports the real installed SDK Config
but injects a fake client and runs three parser/transport tests; it never reads
credentials, sends a provider request or invokes Dafny.

`runtime-freeze.json` pins executable code, tests, logs and the submission script.
`authorization.json` will bind the user's explicit approval to this runtime and
scope, with a finite expiry. A fresh submission lock plus job/ledger checks must
precede sbatch. Never issue a second submission or restart after ambiguity.

## Completion review and publication

`review_results.py` replays exact frozen messages and guarded responses, checks
candidate/accepted hashes against raw verifier evidence, and reconciles IDs and
reservations. `summarize.py` reports per-family four-cell outcomes, admission,
failure categories and token usage. Preserve originals and all failed attempts.
Archive raw logs, messages, responses, sources, extraction decisions and metadata
to GitHub, followed by manual proof/contract review. Whole-workspace success uses
strict exit zero. Shared and separate output workloads differ, and this remains
development calibration on four semantic instances. Review floors, ceilings,
protocol issues and strategies before any scale-up. The main 192-call corpus
and extra diagnostic model requests remain unauthorized.

## Submission

Job **57099049** was submitted once on November 2 at 19:49:40 UTC.
`submission.json` and `submission.lock/intent.json` record live PreemptMode=OFF,
empty prior job/run state and scope/runtime/authorization hashes. No duplicated
submission or model connectivity request was made. The approved cap is 32 total
requests for this run, with no reassignment or automatic restart.
