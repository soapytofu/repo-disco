# Vest: a frame API followed by a counted frame stream

Prepared November 18, 2026. **Offline proposal and analyst reference code only.**
No Rust/Verus command, cluster job, model call or mathematical acceptance is
claimed. The source and prospective control outcomes need native qualification
against the pinned Vest toolchain before a model prompt or budget is frozen.

## Two actual additions in a dependency chain

1. `growth_frame.rs` adds a U16 little-endian length-framing API for arbitrary
   payloads of at most 65,535 bytes. The new theorem must prove payload recovery,
   exactly two header bytes plus payload length consumed, and preservation of an
   arbitrary trailing byte sequence. It uses upstream `Bind`, `U16Le`, `Varied`,
   `SPRoundTripDps` and `NonTailFmt` contracts.
2. `growth_batch.rs` adds recursive serialization and counted parsing of an
   arbitrary finite sequence of those frames. The theorem must recover every
   payload in order, establish the sum of all frame lengths, and preserve the
   original suffix. It imports stage one's module and uses `frame_roundtrip` on
   an intermediate suffix containing the rest of the batch. Induction handles
   the remaining frames.

The batch count is **provided out of band**, not encoded in the wire data. These
are specification/proof-library extensions, not executable parser implementations
or a demonstrated runtime feature. Fixed spec definitions and explicit behavior
requests avoid treating specification invention as verified synthesis. A future
model task fills the marked proof body while all definitions, signatures,
preconditions, postconditions and termination measures remain host-fixed.

The upstream source already has `Bind(U8, Varied)` roundtrip demos and a U16
dependent-format length example. The new contribution proposed here is the
general payload/suffix boundary interface and its recursive batch consumer, not
a claim to invent length framing or to add an expressiveness capability absent
from Vest's generic combinators. No exact `growth_frame`/`growth_batch` module
exists at the pinned revision. The second theorem is stronger than duplicating
the first for a renamed payload: it covers unbounded finite lists and byte-slice
composition across accepted frame boundaries.

## Parent and edit rules

Use Vest commit `333d61c1f0a2a5accc6962ee9a4ae05619fd0dcc`, with its qualified
default-feature `vest_dev` root plus `vest_lib`/`vstd` dependency proof inventory.
The pinned snapshots under `real-repository-qualification-001/upstream/vest`
remain read-only. Module registration is host-owned: append `pub mod growth_frame;`
and, only at stage two, `pub mod growth_batch;` to the exact original
`vest_dev/src/formats/mod.rs`.

The future model may edit only text between the named `BEGIN EDITABLE` and
`END EDITABLE` markers of the newly requested proof. All upstream files, imports,
module paths, spec bodies, contract clauses and `decreases` clauses are protected.
No new `assume`, axiom, external-body attribute, verifier exclusion, build change,
or strengthened upstream trait bound is permitted. Successful proof of only the
new theorem is insufficient; all required old and new proof units must pass.

Stage two must use the **exact accepted stage-one source**, recording its hash,
its accepted evidence and the new child's parent link. It must not substitute the
analyst reference for a failed or different model parent. If stage one fails,
stage two is undispatched. Changes to stage one during stage two are rejected.
Model-visible stage-two context may legitimately include the accepted stage-one
proof. Analyst reference bodies, alternatives, negative controls, counterexamples
and body labels are audit-only. Imports/calls show an implemented dependency;
they are not proof that every valid batch proof needs this particular helper.

## Prospective native controls

`prepare_cases.py` creates **13 small overlays**, never copies the upstream tree
and never invokes a compiler or model:

- Five frame cases: reference, alternative using child-format theorems, empty
  proof, zero-length header inconsistent with arbitrary payloads, and a wrong
  consumed-length assertion omitting the two-byte header.
- Five batch cases with the exact reference frame parent: reference, reordered
  induction/helper alternative, empty proof, wrong zero-frame count, and omitted
  inductive argument.
- One broken-frame/passing-batch control: a caller may verify under the unproved
  frame contract, but whole-workspace acceptance must reject it.
- Two omitted-module controls: a staged frame or batch file without its host
  module registration must be rejected for missing required results even if
  the native command reports the preexisting scope passing.

Four overlays are intended full successes, seven are intended proof failures,
and two are missing-coverage rejections. **These are expectations, not observations.**
The omitted-induction/empty bodies in particular need actual verifier checks to
establish that the target cannot be discharged by existing unfolding alone.
Preserve unexpected passes or failures before any deliberate, versioned change.

The expected new friendly labels are:

```
vest_dev::formats::growth_frame::frame_roundtrip
vest_dev::formats::growth_batch::batch_roundtrip
```

Root must confirm exact native target labels/kinds and retain any additional
new well-formedness or termination targets in the source-bound inventory.
Unlogged spec definitions must be bound to their source hashes, never counted
as logged proof successes. The existing qualified baseline inventory and its
multiplicities remain mandatory for every new scope; missing dependencies, stale
IDs, changed sources or new trust bypasses reject acceptance.

## Qualification and evaluation boundaries

Root owns cluster staging, native commands, resource/warning policies, source
guards, ledger/runner, Git and publication. Native verification belongs only on
compute nodes using the exact pinned Verus/Rust/Z3 environment. No source change
or resource increase is an automatic retry. The current source package is not
an immutable freeze and contains no paid authorization or live runner.

An initial future one-chain pilot would need **at most two new model requests**,
one per stage, with no retry or reassignment and a fresh prompt context per stage.
This is a budget estimate, not authorization. A model-generated proof-library
descendant is counted only after the entire eligible scope verifies and its
parent identity is checked. Two accepted additions would represent one growing
lineage in one inspected development repository, not two independent tasks,
an unseen-family score, an iterative repair agent, or open-ended generation.

The first native run may expose syntax or solver issues: this offline preparation
has not validated `spec_fn` coercions, quantified trait invariants, recursive
unfolding, sequence-slice identities, friendly-label spelling or warning behavior
for these new sources. Treat analyst references as candidates until verified.
