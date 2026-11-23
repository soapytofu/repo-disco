# Growth runner with bounded AWS error evidence

This separately versioned execution-004 package preserves the frozen eight-slot
growth proposal and adds diagnostics to a terminal transport failure. It is
preparation only: **zero model calls are authorized by this package**. No key is
read, checked, consumed or included during construction or offline preflight.
The execution-003 AccessDeniedException and execution-001 credential failure
remain closed and unchanged. This is not a restart or reassignment of their
unused slots, and cannot recover their missing provider metadata.

## Error handling

The unchanged `bounded_requests.py` persists a reservation before dispatch and
closes it on transport/response failure. The credential wrapper now captures
only the previously reviewed adapter's five fields:

- `Error.Code` and `Error.Message` (message limited to 512 characters).
- `ResponseMetadata.RequestId`, `HTTPStatusCode` and `RetryAttempts`.

The loaded bearer token and any previously visible bearer token are supplied
for literal redaction before truncation. Exception strings/tracebacks, headers,
request bodies and environment/configuration dumps are never recorded. Missing
or malformed fields remain null. No HTTP status, request ID or retry count is
inferred from an exception class. Unlisted/transformed secrets cannot be
detected by this literal adapter; it is not a general-purpose sanitizer.

Capture happens while the credential transport owns the in-memory token. The
environment is restored on every exit. The original exception is re-raised,
and a capture failure cannot reopen the transport. After the request gate has
stopped, the host optionally writes `slot-NN/transport-error.json`, binding the
redacted diagnostic to the exact request, reservation, runtime, slot and run.
The stop record identifies SAVED, UNAVAILABLE, CAPTURE_FAILED or WRITE_FAILED.
A partial failed write is preserved but is not interpreted as provider evidence.
Error extraction/writing does not cause an automatic retry, child dispatch,
response completion, proof score or accepted revision.

The saved-evidence reviewer checks the error record's exact schema, bounds,
hashes and reservation linkage. The diagnostic does not change the conservative
`AMBIGUOUS_OR_UNSAVED` status or turn a stopped collection into a completed pilot.
This checks trusted-host consistency; it does not authenticate arbitrary JSON
as an independently observed AWS event.

## Unchanged experiment and native policies

The prompt freeze remains
`9f2e4c9602b4ce98740f2a3fa1dcf7bbef07d2b0693db8d92d9cc55546820f0c`, and the
parent protocol freeze remains
`9cf8cc81bd55f83a591c04c2877ab9a0ece3927fcddc31f6f3d42d7953d42057`.
There are two independent lineages per project and at most two stages per
lineage: Dafny-VMC MoveToFront then PickPair; Vest frame theorem then batch
theorem. Vest adds specification/proof-library functionality. Each child is
rendered from its actual accepted parent, with no reference fallback. A failed
parent blocks its child without transferring its slot. Direct child
implementations remain valid; observed API reuse is separate from proof success.

All contracts, source coverage, protected edits, upstream snapshots, acceptance
rules, native proof inventories, model/settings, order and output limits remain
unchanged. One response per stage, independent contexts, no repair loop,
no retries or reassignment. The SDK still has total_max_attempts=1.
Provider ambiguity, integrity drift or unresolved native execution stops future
dispatch. No model availability/connectivity probe is part of preflight.

The prospective job retains one node, one task, **one CPU, 8 GB and four hours**,
with no requeue. Dafny uses resource limit 100,000 and a 300-second native wall
cap. Vest uses one Cargo worker, one Verus thread and a 900-second wall cap.
Both native verifiers run only on compute nodes. A live partition check must
confirm shared is UP, PreemptMode=OFF and supports the fixed duration before
any future submission. There is no resource escalation or duplicate submission.

## Offline qualification and future execution

`preflight.py --draft` reviews the explicit complete input closure before freeze.
Unit tests use fake transport/native processes and synthetic errors. The
installed-SDK regression uses dummy tokens, empty temporary AWS configuration,
an intercepted HTTP boundary and forbidden socket connections. Its five cases
cover the old token-lifetime defect, two successful synthetic responses, terminal
connection failure, AccessDeniedException/403 and ThrottlingException/429. The
last two check actual SDK parsing, redaction, request IDs/status/retry metadata
and one-attempt behavior. They are not live AWS access tests. Missing SDK packages
are explicitly skipped locally; `--require-sdk` on Cannon makes them mandatory.
Full stdout/stderr, source pins and runtime versions are retained in reviews.

The new runtime manifest pins explicit source and test dependencies. Isolated
manifest-only preflight checks relocation and the dependency closure. Old frozen
sources and ledgers are not edited. `copy-provenance.json` records exact origins;
the request gate, native adapter and pure five-field extractor remain byte-exact.

Root may stage this exact package and run fake-only Cannon preflight with
`ops.py stage` and `ops.py preflight`, using authenticated socket21, disabled
fallback transport and hard subprocess timeouts. The remote destination is
`~/formal-disco/outputs/real-repository-growth-001/execution-004/`; the qualified
interpreter is `/n/home13/sophiezeng/.conda/envs/repodisco/bin/python`.
These commands do not access the private handoff or submit a Slurm job.

Future paid execution requires a **separate explicit user decision** and a fresh
authorization binding this runtime, the unchanged prompt freeze, exact remote
directory, at most eight new requests, no retries/reassignment and an expiry
within 24 hours. No authorization is created by these instructions or ops.
Inspect output/ledger/submission/queue state and require an exclusive submission
lock before submitting. Existing claims cannot be reused by changing output
paths. Full sources, responses, request IDs, diagnostics, resources, failures
and accounting must be retrieved and reviewed. The handoff is consumed only by
a subsequently authorized compute run; it never enters staging, logs or Git.
