# Guarded repository candidate preparation

`language/dafny/candidate.py` adds a pure candidate stage before repository
verification. It binds the base to expected file hashes, rejects file additions
and unguarded edits, runs a trusted task-specific guard on every replacement, and
returns a read-only candidate snapshot. Files outside the edit set retain their
exact bytes. Base snapshots and agenda objects are never updated, including when
a later replacement fails its guard. This avoids partial multi-file agenda writes.

`verify_candidate` invokes the existing repository verifier once and records the
base hashes, changed files and `promoted: false`. Promotion to a live agenda,
concurrent transactions, paid requests and repair scheduling remain out of scope.
Expected hashes detect a mismatched supplied base, not concurrent changes to live
agenda objects. Callers must quiesce source writers before snapshotting.

Guards are trusted code, supplied by the caller, and must raise `ValueError` for
invalid changes. There is no generic contract parser or default permissive guard.
The prepared object is an application API, not a security boundary against callers
forging Python objects. Existing frozen guards and worker behavior are unchanged.

## Offline evidence

The combined repository test suite passes 19 methods (seven candidate tests,
six verifier integration tests and six existing repository-map tests). Candidate checks use the frozen inductive
provider-v1 guard and real revision-003 empty/reference source. They cover protected
contract rejection, unchanged dependencies, stale hashes, immutable/additional
files, all-or-nothing multi-file preparation, and single-attempt verification
without promotion on success, proof failure or timeout. Verification is mocked in
these offline tests; no new Dafny or model calls were made.

During test development, the adapter incorrectly treated the provider guard's
returned source string as a dictionary; three tests errored. Correcting the
adapter to consume the documented string return resolved these errors. The frozen
guard and sources were not changed. This was a test-adapter bug, not a proof result.

The compute gate below now validates this orchestration path with accepted proof
replacements and rejected contract edits.

## Submitted integration

Job **55310512** runs eight verifier checks and four contract-rejection checks
on shared/sapphire, with no requeue. It snapshots real LocalAgenda objects and
applies either one provider-file replacement or two client-file replacements,
using frozen provider-v1/branch-v1 guards. Both shared and separate fixtures are
covered, with reference and known incomplete/incorrect proofs. Expected results:
four verifier successes, four proof failures, four rejected contract edits with
no verifier invocation. Source objects must remain unchanged after every check.
Job completed on shared in 47 seconds. All eight verifier outcomes and four
contract rejections matched. `code/`, `guards/` and `fixtures/` pin all inputs.

Both families passed their reference proofs in both sharing conditions. Missing
inductive steps caused provider postcondition failures; wrong branch boundaries
caused client call-precondition failures. No syntax/name-resolution failures
occurred. All source, code and guard bytes match the submitted and original
fixtures; base hashes, changed-file sets and unchanged agenda objects were checked.
No candidate was promoted to the agenda.

Full logs and exact snapshots are in `verification-001/`; `review.json` records
the audit, reproducible with `review_results.py`. The initial offline review
matcher omitted Dafny’s words “for this call” in a precondition diagnostic; it
was corrected after inspecting the raw log. No source or verifier rerun was needed.
These are integration controls, not evidence of model repair performance.
