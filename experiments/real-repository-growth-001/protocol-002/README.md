# Native evidence and sequential growth policy, revision 2

**Prepared and tested offline; prospective parent integration remains
unqualified until the separate stage-one reference/negative controls pass.**
No model handler, paid authorization, native invocation, acceptance issuer or
revision promotion is included. The original `protocol/` is unchanged.

The body policy uses the corrected `RepoDiscoGrowthShift` and
`RepoDiscoGrowthPick` namespaces from `dafny-revision-002`. Vest's source and
grammar remain unchanged. All eight reference/alternative bodies reconstruct
exactly. Only the current stage's marked body is editable; interfaces, contracts,
imports, types, termination clauses and upstream files remain exact. The only
upstream edit is the host's exact Vest module registration. Stage two preserves
the actual accepted parent, including a nonidentical alternative body.

The bounded grammar and JSON envelope restrictions are inherited from the first
policy. Direct child implementations remain admissible; call counts describe
syntax and do not prove necessary API dependence. Native verification still
decides parsing, typing, termination and mathematics.

## Actual reference replay

`native_adapter.replay_reference(project, repo_root)` requires the externally
reviewed root gate `reference-gates-001.json`, SHA
`0999050882566d8630dec4566ed5526e05fbabcd9f4f1092c9c9322322a82207`,
and its pinned project gates, reviews and raw artifacts. It reads the exact
qualified seed plus saved overlays; no source archive is copied here.

| Saved observation | Preserved native evidence | Replay role |
| --- | --- | --- |
| Dafny job `61753046`, `qualification-002` | 269 passing named CSV entries; 267 original and 2 additions | Analyst full-reference control |
| Vest job `61747454`, `qualification-001` | 5,306 tuple keys and 5,416 successful timed occurrences; native summary reports 5,727 verified | Analyst full-reference control |

Both references contain **both stages in one verification**. Their result is
always stage two, `eligible_as_accepted_stage_one=False`. They are neither model
acceptances nor two sequential acceptance events. Filtering the second file or
its units out of these observations cannot produce stage-one evidence.

The replay also retains the six fixed frame specifications that Verus did not
log, bound to their exact source bytes and explicitly not counted as passes.
Inherited Dafny trust/unlogged scope remains as qualified upstream. No original
score, native result or warning policy is changed.

## Lossless Vest extraction

Each original timing entry receives this canonical JSON-string identity:

```text
["verus-timed-occurrence-v1", crate, module, label, mode, ordinal]
```

`ordinal` runs from 1 through the native multiplicity of that exact tuple.
Extraction retains every record, its actual Boolean success, timing fields,
source stream and JSON byte range, report index, module index and original
function-breakdown index. Rows sort by tuple and numeric ordinal. Decoding and
recounting must reproduce the exact native tuple-count map, without gaps,
duplicates or silent deduplication.

The crate is the **owning report's crate**, not the function-name prefix. The
actual reference includes 26 entries starting with `alloc`, `core`, `std` or
`verus_builtin` inside `vstd`/`vest_lib` reports. All 96 repeated keys, including
multiplicity 11, survive. The 5,727 native summary count is retained separately
from the 5,416 timed records. Occurrence slots are not unique logical proof
obligations or stable semantic identifiers across different programs.

`native-units.json` in the prospective host interface is a **derived extraction
artifact**, not an extra file emitted by Verus. It binds the full original
stdout/stderr/resource/CSV hashes, source revision and full source map, profile,
native command, toolchain/image records, run ID, reviewed scope/gate and exact
adapter runtime. The adapter recomputes it from original bytes before using it.
It never reconstructs individual outcomes from a deduplicated friendly-name map.

## Accepted-parent boundary

`NativeBinding` contains immutable artifact-pin pairs supplied by the trusted
host. `audit_native` replays those artifacts, checks before/after source and tool
identities, command scope, native results and the reviewed inventory, and applies
the pinned warning policy. A qualified pass requires exit zero, no timeout,
complete proof coverage and no unreviewed warnings. Valid failed observations
remain failures.

`body_policy.reconstruct` requires a separate `AcceptedParentBinding` for stage
two. That binding must select the actual model-origin **stage-one** revision,
its host acceptance record, replayable native evidence, and a separately reviewed
stage-one reference/negative-control scope. The actual source map must equal the
accepted revision. Analyst references/controls, changed parents, stale runs,
failed helpers, absent results and forged extraction summaries are rejected.
The package does not create such native acceptance records.

Positive parent-integration fixtures in `test_protocol.py` are explicitly
synthetic, use tiny invented inventories and execute no verifier. Default calls
reject them. The test-only opt-in is never evidence of real stage-one acceptance.
Actual remaining controls were still pending when this package was prepared.

**Host pins are an authority boundary, not cryptographic authentication.**
Arbitrary self-consistent JSON cannot prove that a job ran. The host must choose
pins from the reviewed native history, qualify the complete stage-one inventory,
review and freeze the expected command, resources, tools and scope, and preserve
its accepted-revision history. Labels such as `accepted` or
`reference_reviewed` are insufficient without that externally trusted binding.
No live dispatcher or model-call budget is supplied by this module.

## Checks and artifacts

```sh
/usr/local/bin/python3.12 -B -m unittest discover \
  -s experiments/real-repository-growth-001/protocol-002 -p test_protocol.py -v
```

Seventeen focused tests passed. They cover actual full-reference replays and all
native row locations, occurrence multiplicities, missing/duplicate/failed data,
stale source/run/command/tool evidence, both revised source chains, protected
edits and explicit synthetic parent-integration paths. Synthetic mutations of
saved JSON are negative parser fixtures, not additional native observations.

`offline-tests-001.*` preserves the exact test transcript. The compressed
`native-replay-*-001.json.gz` files contain the complete new derived replay data;
the full original logs remain at their pinned existing repository paths.
`offline-review-001.json` records source/runtime identities and replay counts.
`copy-provenance.json` records copied parser dependencies and source derivation.
All computation here is Python replay; no Dafny, Verus, model, network or Git
command was executed by this preparation.
