# Sequential additions to qualified real repositories

Prepared November 18, 2026. This is **nonpaid task construction and verifier-only
qualification preparation**. No model requests are authorized or dispatched by
this experiment. The analyst sources are currently unverified candidates.

The target is a short growing lineage: a qualified upstream seed, an accepted
first addition, and a second addition made against that exact accepted parent.
Earlier repairs and independent client extensions do not already establish this
result. The original real-source repair score remains 7/16 and all historical
protocols, source snapshots and results stay unchanged.

## Two concrete chains

| Qualified seed | First addition | Second addition |
| --- | --- | --- |
| Dafny-VMC, `e3631f8d335bf7ec3648b13976fa2a96a2a5406e` | Stable `MoveToFront`: move element k to the front while preserving every other element's order, length and multiset | `PickPair`: move original elements i and j to the first two positions in order, preserving the remainder; the reference composes the first API with adjusted indices |
| Vest, `333d61c1f0a2a5accc6962ee9a4ae05619fd0dcc` | U16-length-prefixed payload proof API: exact recovery, consumed length and arbitrary-suffix preservation | Recursive counted batch proof: recover an arbitrary finite list of payloads in order and preserve the suffix, composing accepted frame boundaries |

Dafny adds deterministic sequence operations related to the existing Fisher-Yates
library, not a probability distribution or random generator. Vest adds a
specification/proof library over existing combinators, **not executable parser
generation**. Vest already supports length-prefixed combinators; this task does
not claim to invent that capability. Its second-stage induction and exact suffix
property make the requested addition more than a renamed single-frame example.
Detailed sources, assumptions and prospective controls are in [dafny](dafny/README.md)
and [vest](vest/README.md).

Host-written contracts fix exact behavior before model collection. References,
alternatives and negative controls test that those contracts are attainable and
nontrivial; they must not appear in future model prompts. The prospective model
edits only the current function/proof body. Imports, signatures, specifications,
termination clauses, upstream files and accepted earlier additions are protected.
The host alone registers the new modules in the native verification scope.

## Qualification before collection

The draft fixtures contain 12 Dafny and 13 Vest source overlays. Their pass/fail
labels are expectations, not measured outcomes. Dafny has four passing offline
test methods covering finite sequence semantics, protected construction and
counterexamples; Vest has a source/overlay integrity review. Neither establishes
native parsing or proof success.

First run **two full-scope reference observations**, one per repository, with
both new additions present. Review old and new proof targets, exact source/tool
bindings, warnings and runtime. Only after that review may the distinct remaining
controls run; do not blindly submit all variants against a broken reference.
Preserve unexpected outcomes before deliberate versioned corrections.

The native controls must demonstrate:

- Correct and alternative reference implementations prove the augmented scope.
- Wrong stable order, index adjustment, length, header or recursion is rejected
  at the intended obligations, rather than merely failing to parse.
- A passing child under an unproved parent is not full-workspace success.
- A staged but omitted module is rejected for missing required evidence even
  when the native command exits successfully.
- Every original required unit remains covered; newly emitted targets are
  inventoried, and fixed unlogged definitions are labeled as such.

The initial resource choices for this **new qualification** are fixed before
dispatch: Dafny CLI resource limit 100,000 with a 300-second wall cap; Vest with
one Cargo build worker, one Verus thread and a 900-second wall cap. Both reserve
one CPU. The higher Dafny limit follows the separately published budget-sensitivity
finding; the Vest setting addresses serial preparation overhead. These are
explicit changes from the historical protocols, not historical rescoring or
measured speedups. A future model collection must bind its own reviewed settings.
No automatic retries, resource increases or duplicate submissions are allowed.

Only compute nodes may execute Dafny/Verus. Runtime preparation, source-policy
tests and fake-process tests remain offline. The separate qualification runtime
must be self-contained and hash-pinned before staging. Native proof inventories
and a frozen edit/parent policy are prerequisites to a model prompt freeze.

The [offline parent policy](protocol/README.md) reconstructs only the current
body and exact host registration while retaining the actual accepted parent.
Its accepted-parent examples are explicitly synthetic and rejected by default;
they do not establish native acceptance. The separate
[reference runtime](qualification-001/README.md) permits only the first two
reference invocations. Neither package promotes revisions or releases the
remaining controls automatically.

The policy passed 19 offline tests, including eight exact reference/alternative
reconstructions. The runtime passed 31 tests locally and in an isolated package.
Independent review identified and corrected an archive-state check that could
have fetched suspended jobs prematurely; the original runtime and test records
are retained. The [implementation review](implementation-review-001.json)
binds these packages and their limitations. No new native job has been submitted.

Before live parent-policy integration, the host must preserve the native
inventory's multiplicities. The existing Vest scope has 5,300 tuple keys but
5,410 timed occurrences, including 96 repeated keys. Encode each occurrence as
canonical JSON `["verus-timed-occurrence-v1", crate, module, label, mode, ordinal]`,
numbered 1 through the observed count within that exact tuple. Recounting the
expanded IDs must reproduce the reviewed native inventory exactly; retain each
raw record's success flag and stream/report/module/function indices. These are
timed occurrence slots, not distinct logical proof obligations. Preserve native
crate summary counts separately. New occurrences require the same treatment.

The policy's distinct `native_units` artifact is a host-derived extraction from
the original native streams, not a separate verifier output. Its provenance must
bind those complete stdout/stderr hashes, extractor/runtime identity, source
revision, command, toolchain and run ID. The host must replay extraction and
inventory expansion before issuing a parent receipt. Hash-consistent records
alone cannot authenticate their own proof claims. This adapter and actual native
parent evidence remain prerequisites to any model collection.

## Accepted-parent and measurement rules

Each lineage starts from the pinned qualified upstream snapshot. Stage one gets
one independent response and one declared verification attempt. If accepted,
save its exact source, parent hash, patch and source-bound native evidence. Stage
two must use that source and evidence; substituting an analyst reference or an
unrelated successful response is prohibited. Stage two cannot change stage one.

If stage one fails, stage two stays **blocked and undispatched**; its slot is not
reassigned. If stage two fails, retain the accepted first addition. No post-failure
feedback, repair response or interactive agent loop is included in this design.

Report planned/dispatched/returned/blocked slots, admission failures, frontend
failures, proof failures, resource failures and warnings separately. A verified
stage requires complete augmented-scope evidence and protected-source integrity.
Report complete two-stage lineages per repository, not descendants as independent
repositories. Record tokens, wall time, resources, changed declarations and
accepted-parent hashes. Use the eventual warning policy exactly as frozen.

The reference second stages use the first APIs. Future valid direct implementations
remain mathematical successes; report their lack of first-API reuse separately.
Observed calls and source/dataflow inspection can establish actual reuse in a
candidate, but cannot establish that every valid proof requires that helper.
Do not collapse verified extension, observed API reuse and necessary proof
dependence into a single metric.

## Prospective model budget — not authorized

Recommended first collection: **at most eight new calls**, two independent
lineages per repository and at most two stages per lineage. The minimum
demonstration is four calls, one lineage per repository. Two repeated lineages
provide a small repeatability check, not four independent task families or a
statistical comparison between languages. Do not pool these outcomes with the
earlier 16-call repair pilot.

Before requesting approval, complete native controls, protect edit/parent
boundaries, freeze source-selection rules and stage-specific prompt templates,
and test the bounded runner. Stage-two exact prompts necessarily depend on the
actual accepted stage-one source: freeze the rendering rule prospectively, then
archive each instantiated payload and parent binding before dispatch. Model
settings, order, guards, scoring and global call limit must be explicit.

Existing model budgets are exhausted or terminal. There is no new model handler,
authorization, credential handoff or paid submission here. These inspected
upstream seeds are development material; no held-out, broad generation or causal
depth/sharing conclusion follows from this proposed pilot.
