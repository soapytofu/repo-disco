# Sequential growth edit and parent policy

**Offline qualification only.** This package reconstructs candidates and checks
their source/evidence bindings. It does not run Dafny or Verus, issue acceptance
receipts, promote revisions, dispatch model requests, or freeze a paid pilot.
It contains no native accepted-parent fixture.

The current source templates come from the sibling Dafny and Vest construction
packages. Native reference/control qualification is a separate prerequisite.
If those sources change, update this preparation deliberately before a future
pilot; do not silently substitute new templates into an existing run.

| Stage ID | Addition | Editable region |
| --- | --- | --- |
| `vmc-move` | `repodisco-growth/MoveToFront.dfy` | `MoveToFront` function body |
| `vmc-pair` | `repodisco-growth/PickPair.dfy` | `PickPair` function body |
| `vest-frame` | `vest_dev/src/formats/growth_frame.rs` | `frame_roundtrip` proof body |
| `vest-batch` | `vest_dev/src/formats/growth_batch.rs` | `batch_roundtrip` proof body |

The host owns every prefix, suffix, declaration, import, type, specification and
termination clause. All 91 Dafny-VMC or 3,481 Vest upstream file bytes remain
fixed, including build files. The only upstream change is the exact host-owned
Vest `formats/mod.rs` append prescribed in `policy-spec.json`. Dafny command
registration remains a native-host responsibility; staging and hashing a file
do not prove that Dafny checked it.

Stage two adds a fresh file to the **actual accepted stage-one byte map**.
The parent body cannot be edited. An accepted alternative cannot be replaced
with a nonidentical analyst reference, even when both have the same interface.
An existing child, missing parent, unexpected file or changed registration is
rejected. Reconstruction returns a new in-memory map and never mutates its input.

## Body syntax and trust boundary

The bounded, ASCII lexical policy reuses the prior tested tokenization,
delimiter, functional-update and JSON-envelope helpers. It permits the current
reference/alternative syntax, typed Verus `choose`/`forall`/`exists` binders,
`Seq::<...>::empty()`, the fixed `seq!` macro, assertions and approved calls.
New declarations, imports, proof bypasses, attributes, indirect calls, protected
name shadowing and input assignments are rejected. Comments and strings inside
the replacement remain outside this restricted grammar. Native verification
still decides parsing, typing, termination and mathematics.

The response must contain one JSON object with exactly one `replacement`
string. A missing trailing newline is added by the host; both submitted and
rendered body hashes are recorded. No filenames, accepted-parent records or
verification flags can come from the response.

Parent API call counts are descriptive. The policy does **not** require a call
to `Shift.MoveToFront` or `frame_roundtrip` as evidence of necessary proof
dependence. In particular, a direct Dafny slice expression is admissible while
the accepted parent remains fixed and included. Its proof is still untested by
this policy. The frozen Vest specifications already use the frame API; this is
specification/proof-library growth, not executable parser generation.

## Host-pinned parent evidence

`AcceptedParentBinding` is trusted host input selected from the actual accepted
history, never a model-supplied value. It pins project, stage, chain and run IDs,
the exact source-map digest, the policy runtime identity, and hashes of
`accepted.json`, `review.json`, `profile.json` and the required-unit inventory.

The externally reviewed native profile must cover the entire qualified project
plus stage one, retain all old required units, identify every new required unit,
and bind the actual toolchain, native command, warning policy and qualification
review. **This draft does not invent the new native unit names.** The native
reviewer must construct and inspect the complete inventory from real evidence.
It must explicitly handle any legitimate unlogged declarations rather than
counting them as passing observations.

The binding check requires:

- All actual parent source hashes equal the profile, accepted record and native
  review's before/after inventories, with unchanged public and internal contracts.
- Exit zero, no timeout/frontend/proof failure, complete registration and
  coverage, and one `Passed` observation for every profile-required unit.
- A passed host-pinned warning policy and zero unreviewed warnings. Known
  inherited warnings may be recorded; nonzero warning-only exits are not accepted.
- Exact complete raw-artifact hashes, including distinct stdout, stderr, native
  proof-unit and execution-evidence roles.

The schema checks and exact field examples are in `validate_parent` and the
explicitly synthetic `synthetic_parent` test fixture. That fixture is **not an
acceptance implementation**. Default production calls reject its
`synthetic-offline` kind; `allow_synthetic=True` is solely for offline tests.

**Hashes establish consistency with externally trusted pins, not authenticity
of arbitrary self-consistent JSON.** A caller that invents the host pins can
also invent a story. The host must review the native evidence, protect its
accepted-revision history and reject filesystem symlinks before reading/staging
source byte maps. This module does not replace that native gate or authority.

## Host integration points

Use `reconstruct(stage_id, body, parent_sources, chain_id=...)` for stage one.
Stage two additionally requires `parent_binding` and `parent_artifacts` from the
reviewed host gate. `parse_response` adds bounded single-JSON extraction.
`audit_candidate` repeats the exact source comparison before native verification
to detect post-reconstruction edits. Every result remains
`candidate_unverified=True`; the host must verify the complete workspace before
any promotion. No live integration is included here.

The default warning/exit policy and required inventory must not be weakened to
get a candidate accepted. Broken or absent native evidence blocks the child.
Tests use clearly labeled synthetic records, so they establish these rejection
paths and source preservation, not proof success or real generated growth.

## Offline checks and provenance

From the repository root:

```sh
/usr/local/bin/python3.12 -B -m unittest discover \
  -s experiments/real-repository-growth-001/protocol -p test_policy.py -v
```

The focused tests reconstruct eight exact reference/alternative sources, check
both actual-parent lineages, protected sources/registration, stale or failed
evidence, missing results, forbidden edits and valid extended syntax. An isolated
package check copies only the declared production files into temporary storage
and repeats the eight source reconstructions without access to sibling modules.
It invokes Python only.

`inherited-inputs.json` records source and copied hashes. The old body guard has
only a relative import adjustment; its task-specific dispatcher is unused. Its
envelope extractor is byte-identical. Templates copy the current exact fixed
source; only the Vest marked proof bodies were removed. No upstream archive or
prior experiment was changed or duplicated. `offline-checks-001.*` and
`offline-review-001.json` record this preparation, not native acceptance.
