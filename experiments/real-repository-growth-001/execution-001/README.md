# Eight-slot repository growth runner preparation

This package prepares the previously frozen growth pilot for a possible future
execution. **No model calls are authorized by this package.** It contains no
authorization file, credential, submitted job, accepted model parent or live
stage-two payload. Root must finish independent source review before constructing
`runtime-freeze.json`; a separate explicit human decision is needed before any
paid execution.

The maximum is eight fresh requests: two independent lineages for each of
Dafny-VMC and Vest, with at most two sequential additions per lineage. One
response is allowed per stage, with no retry or feedback repair loop. An ordinary
proof or edit-guard rejection is an evaluated failed stage; its child is blocked
without reassignment. API ambiguity, integrity drift or unresolved native
execution stops future dispatch. Eight is a ceiling, not a target to fill.

The immutable pilot remains the authority for prompts, model/settings, order,
contracts, output grammar and stage-two rendering. Child prompts require the
actual accepted first addition and its source-bound native receipt. Analyst
reference/control artifacts are host-side qualification evidence only; they are
not model context or accepted model parents. Synthetic test fixtures are included
only for explicit offline tests and must never enter live dispatch.

`build_runtime.py inspect` resolves an explicit repository-relative input
inventory without writing a freeze. After root review, `freeze` creates the new
runtime manifest exclusively and refuses an existing manifest. No unrestricted
repository scan selects credentials, live ledgers or output directories. The
qualified upstream snapshots, proposal, policy, saved evidence, native closure
and execution sources are hash-bound. Existing cluster images and toolchains
remain at their qualified paths; the native host checks their exact hashes.

The remote layout is
`~/formal-disco/outputs/real-repository-growth-001/execution-001/`, with exact
repository paths under `repo/`, a mirrored runtime manifest and `run.sbatch`, and
fresh output in `model-001/`. A supplied authorization is copied verbatim to
`authorization.json`; ops never manufactures approval. It must name Sophie Zeng,
state the explicit human approval basis, bind this runtime and pilot, cap new
requests at eight, prohibit retries/reassignment, and expire within 24 hours.

Ops uses only authenticated socket 21 (or an explicitly supplied socket path),
batch mode, disabled fallback transport and hard subprocess timeouts. Submission
and every other remote operation use the qualified Conda interpreter at
`/n/home13/sophiezeng/.conda/envs/repodisco/bin/python`, with no system-Python
fallback. Submission
requires a passing fake-only remote preflight, fresh output/submission/ledger
state (including the exclusive execution claim), the authorization, private handoff metadata, and a live `shared` partition
check showing `PreemptMode=OFF`, `State=UP` and at least four hours. Handoff
contents are never read, hashed or printed by ops. Exclusive local intent and
remote lock survive failed or ambiguous submission; there is no retry/resume
operation. Older paid ledgers and results remain unchanged.

The job requests one node, one task, **one CPU, 8 GB and four hours**, with no
requeue. Dafny remains fixed at resource limit 100,000 and a 300-second native
wall cap; Vest uses one Cargo worker, one Verus thread and a 900-second native
wall cap. Up to four invocations of each native backend plus eight 180-second
provider reads account for 6,240 seconds before build/setup overhead. The Slurm
bound is fixed, not an adaptive escalation; the short `test` partition is not
assumed to support it.

Preflight runs only the new fake transport/native tests and `bash -n`. Remote
preflight additionally requires boto3/botocore imports, records their observed
versions, and constructs a `Config` with 15-second connect/180-second read limits
and one total SDK attempt. Local preflight reports an absent SDK without treating
it as a provider check; `--require-sdk` makes imports mandatory. No client is
constructed, and no verifier is called. Logs preserve code hashes,
test output and draft/frozen status. A relocated manifest-only package must also
pass preflight before staging is released.

After a terminal job, fetch requires exactly one parent accounting row and
explicit terminal states for every relevant step. Similar-prefix IDs do not
substitute for the parent; suspended, stopped, unknown or live steps fail closed.
Before either endpoint is changed, a read-only regular-file inventory and local
free-space check reserve the full transfer plus headroom. Source bytes, responses,
request ledger, accepted records, native stdout/stderr, CSV/JSON, resource reports
and failures are preserved. Only the eight exact generated
`slot-NN/native/fresh-target` Cargo target directories are excluded, using the
same enumerator as the run's archive manifest; all native source workspaces
remain included. No scratch files are deleted. Raw native failures remain failures even if a later,
separately versioned diagnostic succeeds.

Preparation entry points (for root after review):

```text
python -B build_runtime.py inspect
python -B preflight.py --draft
python -B build_runtime.py freeze
python -B ops.py stage
python -B ops.py preflight
python -B ops.py submit --authorization /path/to/explicit-reviewed-authorization.json
python -B ops.py status
python -B ops.py fetch
```

Only preparation and offline tests are in the current authorized scope. Listing
future commands does not authorize their execution.
