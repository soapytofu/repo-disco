# Window-wide request gate

`window_budget.py` is an **offline-tested accounting library**, not a model runner or credential service. It contains no SDK, provider client, API configuration, key handling, network code, Slurm submission or Dafny execution. All tests use fake transports. No real requests have been sent by this component.

The parent coordinator must route **every** new request through **one canonical ledger directory** for this research window. The library enforces a maximum of 128 calls and a deadline no later than **2026-11-16 04:05:12 UTC**. A smaller scope is permitted. The explicit scope is stored and bound by its canonical JSON SHA-256; changing the cap, deadline or any other scope field prevents reopening that ledger.

## Ownership and reservations

An atomic `owner.lock` directory admits one process. A second process, another instance, a reentrant call or an inherited object after `fork` cannot dispatch. No method clears an abandoned lock. Crashes, ambiguous transport, persistence errors, missing/duplicate provider request IDs or nonzero SDK retry counts leave the window closed and the ownership evidence in place. A saved response remains on disk even if a subsequent ledger commit fails; the reserved call is never refunded.

Each batch must first register an immutable manifest containing:

- `batch_id`, `freeze_sha256`, `runtime_sha256`;
- `slots`: the ordered list of `{trial_id, request_sha256}`;
- `max_calls`: exactly the number of slots;
- `sdk_total_max_attempts: 1`.

Batch IDs, freeze hashes and global trial IDs cannot be registered twice. The sum of declared batch capacities cannot exceed the window cap. Dispatch follows registration order and each batch's frozen slot order. Exact original request bytes must match the slot hash; the transport receives a JSON copy of those bytes. The gate durably reserves a slot before dispatch, records dispatch intent, and checks the deadline both before and after persistence work. Expiry after reservation consumes that slot without sending it. Calls started before expiry may finish afterward, but no later request can start.

Clean `close()` allows an **explicit** later `open_existing()` only after checking scope, all completed reservations, exact request/response bytes, provider IDs and evidence inventory. Remaining slots stay bound to their original batch; they cannot be skipped, replaced, reassigned or resent. An interrupted or ambiguous owner is never automatically reopened. `finish()` terminally closes the window. Uncaught exceptions leaving a context-managed owner also stop it.

## Integration contract

Required authorization keys are `window_id`, `authorized: true`, `no_retries: true`, `max_calls`, `deadline_epoch`, and a nonempty `authorization_basis`. Extra scope fields are also hash-bound.

```python
from pathlib import Path
import json
from window_budget import WindowBudget

scope = json.loads(Path("scope.json").read_text())
# Use one coordinator-chosen absolute shared directory, never a per-batch path.
with WindowBudget.create(shared_budget_directory, scope) as budget:
    manifest_hash = budget.register_batch(reviewed_frozen_manifest)
    response = budget.invoke(
        batch_id=reviewed_frozen_manifest["batch_id"],
        trial_id=slot["trial_id"],
        manifest_sha256=manifest_hash,
        request_bytes=frozen_request_path.read_bytes(),
        transport=already_reviewed_no_retry_transport,
    )
```

The returned transport mapping must provide a unique nonempty string `request_id` and integer `retry_attempts: 0`; the complete JSON-serializable mapping is archived. The coordinator remains responsible for validating each freeze/runtime against actual files, checking that the model/settings match the authorized study, and disabling **all** transport-internal retries. The library can limit callback invocations, not hidden network requests inside an arbitrary callback.

An existing per-batch gate can remain outside this window gate. Its transport adapter must compare the incoming payload with the exact frozen request bytes, then invoke the window gate for that same slot. Any infrastructure/verification/logging ambiguity in the enclosing experiment must stop the coordinator; do not catch it and silently proceed to another paid batch. Failed mathematical proofs or admitted output-policy failures are ordinary recorded evaluation outcomes, not authorization to retry.

The canonical ledger directory and its ownership marker must be visible to all competing processes on a filesystem supporting atomic `mkdir`, atomic replacement and durable `fsync`. Tests exercise actual competing OS processes on the test filesystem; they do **not** certify every network filesystem or a distributed service. Deliberate deletion/rollback of the authority files, creating a second ledger directory, changing the library or invoking a provider directly is outside this trusted-coordinator boundary.

## Validation

Run `python3 -B -m unittest discover -s experiments/research-window-20261114/runtime -p test_window_budget.py -v` from the repository. Tests cover aggregate spending across batches and owners, fixed remaining slots, concurrency/fork/reentrancy, deadlines across disk work, caught timeout, request/response/ledger persistence failures, duplicate provider IDs and retry metadata, scope/manifest/order/hash drift, tampered/unaccounted saved evidence, and terminal finish. They use neither provider nor verifier calls. `offline-tests.log` records the observed local run; a real compute integration still needs separate review before paid dispatch.
