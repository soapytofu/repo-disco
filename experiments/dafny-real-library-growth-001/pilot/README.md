# Two executable library-growth chains: prompt draft

## Current preparation: draft-002

`draft-002` binds the reviewed standard-library and AWS UInt-only native gates.
Both gates match **12/12 expected saved observations**. This preparation adds no
model or verifier calls and issues no execution release. Root froze runtime
`69d07a07` after review; authorization and dispatch remain root-owned.

| Project | Stage one | Stage two |
| --- | --- | --- |
| Dafny standard library, 4.11.0 | `AppendAll` over the existing `DynamicArray` API | `AppendRotated`, preserving the actual accepted stage-one addition |
| AWS MPL UInt closure, 4.9.1 | Executable `ReadU16Frame` with exact payload/suffix contracts | Executable `ReadFramePair`, preserving the actual accepted frame parser |

The AWS scope contains three original files—`UInt`, `BoundedInts`, and
`Wrappers`—and makes no UTF8-validation or encryption-context claim. The earlier
102-file proposal remains unchanged below as unqualified history. Both current
prompts show their complete three-file upstream scope verbatim: 14,676 bytes for
the standard library and 18,360 bytes for AWS. Stage-one payloads are about 19 KB
and 24 KB, respectively; these are byte counts, not provider token estimates.

The ceiling remains twelve fresh requests: one two-stage lineage per project
in the first four slots, then two more lineages per project only after complete
healthy pilot accounting and at least one accepted stage-one result. Every slot
uses one independent response, no retries or reassignment. Unaccepted parents
block their children. All settings are Claude Opus 4.5, temperature 1, maximum
4,096 output tokens, with a `{"body":"replacement body text"}` response.

`prepare_v2.py` selects exact native profiles, complete reviewed control gates,
source bytes, and the existing root-owned execution binding/budget snapshot. It
checks reference reconstruction under the host body boundary, then removes each
entire reference body. Native options and source order match the actual qualified
commands. `reviews/final-draft-review-001.json` checks the actual model-visible
content: all four empty-body views, exact source context, reference-body and
private-control-label exclusion, protected boundaries, and deferred children.
All 16 prepared artifacts and 30 renderer input pins match. Caller-selected
hashes still need trusted-host review; they do not authenticate arbitrary JSON.

`render_v2.py` uses the **experiment/package root** supplied by the real bounded
runner and returns direct Converse payloads. There is no bare sibling `prepare`
import. A child can be rendered only from supplied accepted same-lineage source
and typed `ParentEvidence`; reference bodies are never a fallback. Both stages
retain `dispatch_eligible:false`. No exact child payload has been saved.

```python
renderer = runtime.load_renderer(package_root, "pilot/render_v2.py")
first = renderer.render_stage1(project, chain_id, root=package_root)
second = renderer.render_stage2(
    project, chain_id, exact_parent_sources, parent_evidence,
    root=package_root, allow_synthetic=False,
)
```

Seven focused integration tests passed in `reviews/renderer-integration-005`.
They exercise the actual manifest-staged loader, renderer and Runner in fresh
interpreters, including exact parent views, strict default synthetic rejection,
failed-parent child blocking, native argument order, Converse/context agreement,
package closure, reviewed upstream-source selection, and the packaged smoke CLI.
Only transport/native results are fake; all their inventories and receipts are
explicitly synthetic. These tests supply no native proof or model success. All
65 tested code/data pins remained unchanged.

Earlier transcripts are retained. `renderer-integration-001` failed before any
test because its host-template selector incorrectly assumed an include line;
`renderer-integration-003` exposed a synthetic report count error. The fixes
changed test preparation/reporting, not native results. Successful earlier suites
remain in `renderer-integration-002` and `renderer-integration-004`.

The actual final package was checked through the same staged path against its
real source/templates/native profiles using only synthetic transport/native
observations:

```text
python3 -B pilot/test_render_v2.py --smoke /absolute/path/to/package pilot/draft-002/scope.json
```

This mode does not load historical references, issue a budget claim, read a key,
or invoke a provider/verifier. It writes an explicitly synthetic twelve-slot
simulation to the sibling `synthetic-smoke` directory once, checks six exact
parent views and strict default parent rejection, and refuses to reuse that
directory. Synthetic pass records are software-test fixtures, not proof results.

The single final-package smoke passed in 1.55 seconds, with all 53 runtime pins
unchanged, twelve fake responses/native observations, six exact parent views and
six strict default synthetic rejections. Full logs and its 314-file evidence
inventory are in `../execution-001/reviews/actual-package-smoke-001`. A separate
read-only review checked every saved stage against the actual 58/60 standard-
library and 75/77 AWS inventories, exact command/tool pins and candidate bytes.
All six child workspaces and views retain their same-lineage synthetic parent
bytes. Only the allowed whole-file hashes for predeclared unlogged definitions
were materialized. Audit field-name/canonical-hash mistakes are preserved in
three review-attempt records; the smoke ran only once and no runtime, source or
saved result was changed. This remains software integration evidence, not
mathematical evidence for the synthetic bodies or model-generated growth.

## Historical draft-001 (unchanged)

`draft-001` is a reviewable prompt and edit-profile preparation, **not a native
qualification or execution release**. Root will freeze/release the pilot only
after the actual positive, negative and coverage gates have been reviewed.
The user's ceiling is twelve new requests, with no retries or reassignment.
No model or verifier calls were made while preparing this directory.

| Project | Stage one | Stage two |
| --- | --- | --- |
| Dafny standard library, 4.11.0 | Implement `AppendAll` over the existing `DynamicArray` API | Implement `AppendRotated`, with the accepted stage-one addition fixed in the workspace |
| AWS MPL selected closure, 4.9.1 | Implement executable `ReadU16Frame` under exact payload/suffix contracts | Implement executable `ReadContextEntry`, preserving the accepted frame parser and fixed UTF8/context specifications |

The first four slots cover one lineage per project and its two stages. Expansion
adds two independent lineages per project (eight more slots), only after complete
healthy pilot accounting and at least one accepted stage-one result. Each slot
gets at most one response in a fresh context. A failed/unaccepted parent blocks
its child; the unused child request cannot be reassigned. An ambiguous request or
native infrastructure failure stops the run rather than inviting a retry.

All settings are shared: Claude Opus 4.5
(`global.anthropic.claude-opus-4-5-20251101-v1:0`), temperature 1, maximum 4,096
output tokens. The only response is `{"body":"replacement body text"}`.

## What the model sees

Stage one includes the fixed empty-body template, ordinary syntax/edit rules,
legitimate upstream context, and exact dependency declarations. New analyst
reference bodies, negative controls, diagnostic outcomes, private control labels
and analyst repair advice are excluded. AWS fixed specification functions remain
visible because they define the task; only the editable implementation body is
removed. Extraction receipts bind the original fixed prefix/suffix and the body
removal outside the model-visible payload.

The standard-library prompt shows all three original source files (14,676 bytes).
The AWS workspace retains all 102 dependency-closed original files (1,303,397
bytes), while the prompt shows four complete relevant files—`UInt`, `UTF8`,
`Wrappers`, and `BoundedInts`—plus verbatim module/import and
`EncryptionContext`/`Utf8Bytes` declaration excerpts. Each excerpt records exact
source positions, original whole-file hash, and excerpt hash. The prompt states
which files are omitted or only partially shown. No fabricated interfaces stand
in for missing source.

The complete AWS include/import inventory contributes substantial context:
276 include edges and 522 import declarations. Current stage-one payload sizes
are approximately 19 KB (standard library) and 154 KB (AWS); these are byte counts,
not provider token or price estimates. Full upstream source remains available
to the host verifier regardless of prompt selection.

An explicit inherited-trust audit identifies 100 AWS observations and 77
conservatively forbidden callable-name tokens. They include inherited callable
trust attributes and declaration spans containing `assume`; module-level extern
namespace annotations are separately disclosed. New bodies cannot invoke or
alias those tokens, including `ValueIsSafeBecauseItIsInMemory`, `Encode`, and
`Decode`. This is not a claim that all transitive upstream trust has been removed.
The source inventory remains part of the trusted qualification scope.

## Actual stage-two parent

No exact stage-two payload is saved: `exact_live_payload` and
`exact_payload_path` are null. A template contains exactly one
`{{ACCEPTED_PARENT_SOURCE}}` placeholder. It is filled only after replaying the
exact same-lineage accepted stage-one source, native observations and host-pinned
request/receipt through `common.guard.validate_parent`.

The renderer preserves all accepted body bytes. For AWS, it removes only the
exact fixed leading metadata comments omitted from stage one's model view;
the host source and its full hash retain them. There is no analyst fallback.
Synthetic, analyst, failed, stale, substituted or wrong-lineage parents are
rejected by default. Explicit synthetic test opt-ins remain marked synthetic
and cannot authorize dispatch. A direct stage-two implementation is not rejected
merely for omitting a helper call; any API-call observations are descriptive.

All source files are explicit verifier inputs. Guard profiles use an empty
registration-change map plus an exact ordered complete `verification_inputs`
list; they add no unqualified `All.dfy`. Root's native profile must bind the same
list to the exact command, toolchain, complete named inventory and warning rules.
Every `native_profile_path` remains null until that actual review is complete.

## Code interfaces

`prepare.prepare(experiment, destination)` constructs a new exclusive draft
directory. It never mutates an existing draft. `render.bundle(root)` checks the
draft artifact, original source and common-code pins. Here `root` is the draft
directory; its default is `pilot/draft-001`.

```python
first = render.render_stage1(project, chain_id, root=draft_directory)
second = render.render_stage2(
    project, chain_id, exact_parent_sources, parent_evidence,
    root=draft_directory, allow_synthetic=False,
)
```

Both return `payload`, `payload_sha256`, project/stage/chain/slot identity,
`guard_profile_sha256`, source revision and file pins, and `parent_audit`
(null at stage one). Stage two also returns the exact parent source/view hashes.
`parent_audit` contains `native_review`, `receipt_sha256`,
`source_revision_sha256`, `synthetic`, and `acceptance_issued:false`.
`render.common_api()` returns the one validated `guard, review_native` module
pair; callers should use it to construct the same typed `ParentEvidence` and
`EvidencePins` classes. Mixed module caches fail closed.

Rendering is not authorization: `dispatch_eligible` and `authorization_issued`
remain false. The future bounded execution host owns actual request provenance,
budget/ledger checks and a separately reviewed qualification release. Self-
consistent hashes or caller JSON do not establish native authenticity.

## Offline evidence and limits

Ten focused tests passed in `reviews/offline-001`, with full stdout/stderr,
exit status and tested file hashes. They cover exact context extraction,
dependency declarations, twelve-slot structure, fixed settings, inherited trust
restrictions, deferred children, and parent rejection/preservation. Every parent
native record in those tests is visibly synthetic; no native proof or model
acceptance is inferred. `reviews/draft-review-001.json` checks the constructed
artifacts and records actual context/payload sizes.

These are two selected development chains for contract-guided executable
extension. They do not establish whole-upstream-repository completion,
unrestricted repository synthesis, necessary dependency depth, held-out
performance or absence from model pretraining.
