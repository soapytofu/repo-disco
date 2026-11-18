# Reviewed native controls and actual-parent integration

This offline package connects the unchanged protected-body grammar to the now
reviewed **actual stage-one** proof scopes. It replays saved evidence; it runs no
verifier or model, issues no acceptance, and does not promote a repository.

| Saved control set | Qualified passes | Proof failures | Native passes rejected for missing coverage |
| --- | ---: | ---: | ---: |
| Dafny-VMC, 11 observations | 3 | 7 | 1 |
| Vest, 12 observations | 3 | 7 | 2 |

These are the existing analyst controls from `controls-001`, not new trials or
model-generated extensions. The combined authority is
`../control-gates-001.json`, SHA
`3325a3a688638bf5a894a9618722c811b9e58dc9a02c867730e41405fa048fd2`.
All 404 external inputs are pinned in `control-inputs.json`; raw archives and
upstream source trees are referenced in place instead of duplicated.

The actual `move-reference` run establishes 268 named Dafny units. The actual
`frame-reference` run establishes 5,411 timed Vest records across 5,301 tuple
keys. Vest's native summary is separately 5,722 verified items. Timing records
are not unique logical obligations. All 96 repeated tuple keys, maximum
multiplicity 11, remain intact; 26 external-spec labels retain their owning
report crate rather than using the label's `alloc/core/std/verus_builtin` prefix.

## Interfaces for a later trusted host

Import `integration.py` with this directory first on the module path, and reject
mixed cached modules from other protocol directories. The pilot renderer checks
module locations. The API exports `NativeBinding`, `AcceptedParentBinding`, and
the body policy as `integration.b`.

* `stage_one_scope(project, repo=DEFAULT_REPO)` returns reviewed inventory,
  command template, tool closure, warning policy and resource limits. It derives
  these from the actual stage-one runs, never a filtered stage-two reference.
* `control_material(project, case_id, repo=DEFAULT_REPO)` loads an exact saved
  analyst observation. `replay_control(...)` independently reconstructs its
  named outcomes, full occurrence inventory, raw flags and qualified result,
  and checks agreement with the published review. Every returned control is
  ineligible as an accepted model parent.
* `audit_model_parent_native(native, metadata, sources, *, repo=DEFAULT_REPO,
  allow_synthetic=False)` checks prospective stage-one evidence under the real
  qualification gate. It returns a derived native record, not acceptance.
* `validate_accepted_parent(child_stage_id, chain_id, sources, binding, artifacts,
  *, allow_synthetic=False, repo=DEFAULT_REPO)` additionally requires an exact,
  externally pinned host acceptance receipt and replayed native extraction.
  Stage IDs remain `vmc-move` → `vmc-pair` and `vest-frame` → `vest-batch`.
* `b.reconstruct`, `b.audit_candidate`, and `b.parse_response` preserve the
  inherited body grammar. Stage two routes through the above parent validator.

A prospective `NativeBinding` pins project, stage, origin, run ID, complete source
revision, protocol runtime, and all raw/metadata artifacts. An
`AcceptedParentBinding` adds chain ID and exact receipt/extraction hashes. The
host receipt schema is `repodisco-growth-host-accepted-stage-one-v3`. It binds the
actual source map, native binding, derived extraction, runtime, qualification
gate and reviewed host scope. Native `model_calls=0` describes the verifier
invocation, not the model request that a future host must independently record.

The host must separately establish and pin actual model-request provenance,
guarded candidate lineage and native execution. Self-consistent JSON and hashes
do **not** authenticate those claims. No producer for such real acceptance is
implemented here, and no actual model parent exists in these controls. A future
bounded host and its live evidence handling still need review.

## What remains fixed

Upstream sources, declarations, imports, type environments, behavior contracts,
new-file prefixes/suffixes and Vest registrations remain exact. Only the current
stage body is editable. Stage two preserves the *supplied accepted parent's*
bytes, including a nonidentical valid implementation; it cannot replace that
parent with an analyst reference. A future model may independently produce a
body identical to a reference, provided its model origin and fresh native run
are independently established. Source equality is not proof of observation
origin.

Known recorded analyst run IDs, complete raw-evidence fingerprints, bound
records and execution records remain ineligible even if origin or acceptance
labels are changed. The complete fingerprint is used, not an individual empty
stderr hash or a source-body blacklist. Explicitly marked synthetic evidence is
also rejected by default and cannot be admitted merely by changing its origin.

Whole-workspace success requires exit zero, complete intended scope, every
required occurrence passing and the pinned warning policy. An omitted failing
module can have native exit zero but fails coverage. An actually failing helper
with a passing child cannot advance. Failed proofs retain their exact native
flags, errors, diagnostics and resources. Fixed unlogged definitions remain
source-bound and are never counted as logged passes.

The analyst-control loader has a narrow exact-source exception for the saved
negative/omission cases, whose comments or intentionally missing registration
can lie outside the model grammar. This exception requires analyst-control
origin and exact reviewed bytes; it never weakens model-candidate reconstruction.
Direct child implementations without helper calls remain syntactically valid
unverified candidates. Call counts do not establish necessary proof dependence.

## Offline evidence

`native-control-replays-002.json` records all 23 exact replay summaries, full
extraction hashes, source/raw/tool/command pins, native resources and warnings.
The full derived occurrence records are reproducible with `replay_control`; their
raw inputs remain in the original archives. No source or prior score changed.

The final focused suite passed **19/19** in `offline-tests-004` against the final
production hashes. It includes ten actual-evidence tests, eight prospective
parent tests and one public-entry-point regression. Full stdout/stderr, exits
and tested-file hashes are saved. No older protocol suite or native verifier
was rerun.

Intermediate evidence remains preserved. The first run passed ten actual tests
and then stopped in synthetic fixture setup:
the fabricated Dafny CSV duration `0` did not match native `HH:MM:SS` syntax.
Only `test_fixtures.py` changed to `00:00:00`; the second run executed the eight
remaining parent tests successfully. Root review then found that the copied
native adapter still exposed its former v2 parent validator. That public entry
point now late-imports and forwards to the v3 validator. Its regression passed
in `offline-tests-003`; the final clean run followed because the production
change also changed the pinned policy digest. The first native replay summary
is retained under its original runtime identity.

`test_fixtures.synthetic_parent` fabricates native rows for explicit test-only
`allow_synthetic=True` coverage. Its positive path proves software branching and
exact source preservation, **not native proof or model acceptance**. It is not a
live handler dependency and must never be copied into a paid runner or exposed
to a model. All older protocol bundles remain unchanged.
