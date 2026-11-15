# In-memory research session coordinator, revision 002

`coordinator.py` is a separate orchestration library with **38 passing offline tests**. It has no SDK, provider configuration, credential reading, shell commands, SSH, Slurm, Dafny, live CLI or background daemon. All transports and clocks in validation are fake. The existing window gate, original `session-runtime/` freeze and all parser policies are unchanged. This deliberate sibling revision resolves two independent-review findings described in `review-findings.json`.

A reviewed caller may supply an already-created, no-retry transport once and keep that callable in one compute process while independently reviewed batches are prepared. This library never obtains or saves a key. Actual one-time handoff consumption, client creation, environment cleanup and final client disposal remain the parent runner's responsibility. This bundle is not itself a reviewed live runner or authorization to dispatch.

## Concrete integration API

Load the pinned `runtime/window_budget.py` and this module from a separately reviewed runner, using `python3 -B` to avoid adding bytecode to frozen input trees. After validating their manifest hashes, the caller constructs:

```python
handler = ReviewedHandler(
    validator=validate_reviewed_batch,
    executor=execute_reviewed_batch,
    code_sha256={"reviewed_batch.py": reviewed_callback_source_sha256},
)
session = ResearchSession.create(
    fresh_session_directory,
    budget=already_owned_canonical_window_budget,
    transport=already_created_no_retry_transport,
    handlers={"repair-v1": handler},
    artifact_root=reviewed_input_bundles,
    code_root=reviewed_callback_code_directory,
)
session.publish(reviewed_descriptor)
# Use seal() only when no further batches should enter this session/window.
session.seal()
session.run()
```

The supplied `WindowBudget` must be owned by this process and clean. Any earlier registered batches must have all their original slots completed; unused slots cannot be reassigned. If the scope specifies `central_ledger_path`, it must match the supplied gate. The coordinator never creates a replacement ledger or calls `open_existing` itself.

`run(poll_interval=30, supply=None)` waits in memory when idle. An optional **reviewed, fixed Python callback** `supply(next_sequence, previous_descriptor_sha256)` may return the next prepared descriptor or `None`. It runs only after the preceding batch completed fully. It may inspect separately staged input data; it must not execute arbitrary queue text. No supplier, file watcher or live batch bridge is included here. Its code and dependencies must be bound by the future parent runner before live use. Alternatively, the owner can call `publish` and `step` itself; `step` executes at most one batch.

## Frozen ordered descriptor

A descriptor has exactly the following fields:

- `schema: "repodisco-session-descriptor-v1"`, the next integer `sequence`, and `previous_descriptor_sha256` (64 zeroes for the first);
- `batch_id`, a fixed registered `handler_id`, and `handler_binding_sha256`, the canonical JSON hash of that handler's relative `code_sha256` map;
- `artifact_directory`, relative to `artifact_root`;
- `freeze_path`, `freeze_sha256`, `runtime_path`, `runtime_sha256`;
- `input_sha256`, the **complete** relative file inventory of the isolated input bundle, including the freeze, runtime manifest and exact request files;
- `slots`, in fixed order, each containing `trial_id`, `request_path`, `request_sha256`;
- `max_calls`, exactly the number of slots, and `sdk_total_max_attempts: 1`.

Paths cannot escape their reviewed root, and symlinks/nonregular inputs are rejected. The descriptor's freeze/runtime hashes must refer to actual pinned files. The complete tree, request hashes, callback source hashes and the coordinator/window module hashes are checked again before execution and each request. A task-specific validator must return exactly `True` before the coordinator may register the batch with the global budget. The complete file inventory, hashes, symlink and nonregular-file checks run again after every validator, so a validator-created unpinned cache file is rejected before registration or dispatch. It must check the actual frozen plan, guard/source pins, model/settings, reviewed verifier gate and authorized study scope; generic hashes alone do not establish those facts.

`publish` validates the descriptor, checks the hash chain, rejects duplicate batch/freeze/trial IDs and aggregate over-allocation, then atomically renames an exclusively created temporary file into the queue and records its hash. This only publishes data; budget registration happens immediately before execution after revalidation. Existing queue files cannot inject work: unexpected files or changed bytes terminate the session. Published descriptors are never rerun.

## Executor capability and receipts

The registered executor has signature `executor(descriptor_copy, context)`. It receives:

- `context.input_directory`: the pinned input bundle;
- `context.output_directory`: a newly created batch evidence directory;
- `context.trial_ids`: the immutable ordered IDs;
- `context.invoke(trial_id)`: the only supplied request capability.

`invoke` loads the exact pinned request bytes and routes them through the canonical `WindowBudget`. The executor receives neither the raw transport nor a key. The capability rejects wrong order, repeated IDs, retained use after return, reentrancy, other threads and inherited use after fork. A caught dispatch error still closes the session globally. The parent must adapt an existing runner to this capability explicitly; it must not leave a second provider path in the callback.

A completed executor returns exactly:

```python
{
    "completed_trials": list(context.trial_ids),
    "evidence_sha256": {"relative-output-file": "its-sha256", ...},
}
```

Every declared request must have returned once with valid unique request ID and zero retry metadata; the exact output inventory must match the receipt. Mathematical proof failures and output-policy rejections can be ordinary completed evaluation outcomes if fully recorded. Missing requests, infrastructure errors, malformed receipts or ambiguous responses are terminal and cannot launch an independent next batch. `completion.json` records the exact descriptor, request IDs and evidence hashes. Before writing it, the coordinator opens each exact evidence file with `O_NOFOLLOW`, checks its identity and hash, calls `fsync`, and rechecks its bytes and identity. It syncs nested output directories from deepest to shallowest plus the batch directory’s parent, then rechecks the complete evidence inventory and identities. Any observed drift or sync failure terminates the session before a receipt or next batch. The executor must have finished and joined all evidence writers before returning; these checks are not an atomic concurrent-write transaction. A completed in-flight last response may be archived after the deadline, then the session closes; it does not authorize another request.

## Lifetime, stop controls and evidence

The session directory is created exclusively. A permanent `research-session.lock` is added under the canonical budget directory. Neither is reused or cleared, even after an intentional close. There is **no restart, abandoned-lock recovery, resume, reassignment or retry API**. Real competing-process and fork tests confirm the local ownership behavior.

`status.json` and immutable numbered `events/*.json` preserve `idle`, `running`, `completed`, `error` and `closed` transitions. Queue descriptors are immutable and hash chained. The window ledger owns durable request reservations and responses. Errors record only a fixed category and exception class, never an exception message, traceback, environment or client representation.

Two optional control files in the session directory are empty regular files, created atomically:

- `SEAL`: admit no further descriptors; drain the already published queue and close.
- `STOP`: stop before another dispatch and close, leaving any unfinished batch incomplete.

The owner can create them with `seal()` or `request_stop()` while idle. An external operator may publish an empty marker during execution. The deadline and STOP are checked again after durable reservation, immediately before calling the transport. A stop at that boundary may leave a charged but undispatched slot; it is not refunded. A stop during an in-flight call cannot cancel that call. Errors stop the global budget through its terminal finish operation when possible; an already poisoned gate retains its own terminal/ownership evidence. The coordinator never clears it to proceed.

## Limits and required review

This is a trusted Python orchestration boundary, **not a sandbox**. Reviewed callbacks can access Python globals or the filesystem; introspection can reach closures. They must not retain a second provider client, issue hidden retries, make network calls directly, leak credentials into requests/responses/logs, change frozen inputs, or mutate the gate. The library can count injected transport invocations, not hidden requests made inside arbitrary Python. The supplied no-retry transport must return only the normalized, non-secret response fields approved for archival; `WindowBudget` archives what it returns.

The credential test uses a fake private sentinel held in the transport closure and in an exception message; no sentinel appears in artifacts. This verifies the coordinator's serialization behavior, not universal secrecy of arbitrary callbacks or provider responses. No real credentials were used.

Filesystem durability relies on atomic creation/rename and functioning `fsync`. Successful local sync calls are not proof of a remote storage service’s persistence guarantees. Tests use the local filesystem; they do not establish Cannon/NFS behavior, crash recovery, distributed coordination or uninterrupted availability. Input/code hashes do not prevent a malicious concurrent writer from racing a read. A forced process kill, disk failure, expired credentials or lost compute allocation can end the session with incomplete evidence. Retained locks prevent automatic continuation; they do not guarantee resilience. Transport deadlines/cancellation and parent notification are separate live-runner responsibilities.

## Validation and freeze

Run from the repository root:

```sh
python3 -B experiments/research-window-20261114/session-runtime-002/test_session.py
```

`offline-tests.log` records 38 passing fake tests: aggregate allocation, sequential completion, validator gating, idle/per-request/post-reservation deadlines, fixed supplier order, duplicate/out-of-order/tampered descriptors, runtime/input drift, hidden extra queue files, request-order violations, caught timeouts, executor and persistence errors, incomplete receipts, retained/reentrant capability use, STOP/SEAL, ownership and fork isolation, and secret-free metadata. `offline-tests-initial.log` retains the first 26-test development pass, and `offline-tests-v1.log` retains the original 31-test pass. All 31 tests remain in revision 002. Seven added tests cover the actual third-validator mutation reproduction, file/nested-directory/parent sync ordering before each receipt, file and directory sync failures, byte drift, an added unaccounted file, and same-byte inode replacement during sync. Failed sync/drift tests confirm one already-returned request remains charged, no completion receipt is written, and no next batch is dispatched.

`validation.json` pins the final code/test/log hashes and verifies that the original session-runtime bundle and all four files in the window-runtime manifest are unchanged. `manifest.json` pins this new library bundle and its existing gate dependency. There were zero model, SDK, network, SSH, Slurm or verifier invocations. A reviewed actual batch adapter and compute preflight remain necessary before live use.
