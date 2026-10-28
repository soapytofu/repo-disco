# Sequential repository repair agent: control validation

The agent now connects deterministic full-source/map context, a bounded injected
request interface, task-specific parsers and guards, real whole-repository
verification, failure feedback and immutable revision promotion.

`repository_agent.py` stores complete revisions and atomically replaces a single
HEAD pointer under a POSIX advisory lock. Failed edits/proofs leave HEAD unchanged;
stale base revisions and mismatched verification hashes cannot be promoted. A
crash before HEAD publication may leave an unreferenced revision but exposes no
partially updated repository. This is a local cooperating-writer contract, not a
distributed transaction or in-place update of Formal Disco's agenda objects.

The base is verified first. Already-verified inputs use no requests; non-proof
execution errors stop. Subsequent attempts use the original base plus the latest
failure feedback. Accepted candidates preserve protected files and contracts.
The declared dependency map is supplied task metadata, not inferred semantics.

## Current validation

28 related offline test methods pass, including nine agent methods. These cover
failure-feedback-success, rejected contracts, timeout/budget stops, stale updates,
source corruption, verified-source hash mismatch and simulated HEAD-write failure.

The submitted compute controls use **saved scripted responses**, not a model:
for each of two families × two sharing conditions, try a contract-changing edit,
a known incorrect proof, then the reference proof. Expected: edit rejection,
proof failure, successful atomic promotion; original revision remains intact.
Twelve scripted requests and twelve verifier calls (including four initial
checks), zero model/API calls. Real model-driven behavior is still unvalidated.
The fixture/guard/API source snapshots are pinned alongside the runner.

The agent deliberately starts with repository repair. Autonomous creation of new
modules, extension task scheduling, context selection and growing generated
repositories remain needed to demonstrate the proposal's beginning-to-scale
component. Existing controlled variants do not constitute autonomous generation.
