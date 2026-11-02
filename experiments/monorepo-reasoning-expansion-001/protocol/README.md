# Development output guard for the six reasoning tasks

`body_guard.py` is a separate **offline-only** protocol. Nine test methods pass.
All 24 authored reference workspaces reconstruct byte-for-byte; 104 semantic
negative-control bodies also reconstruct without repair. Neither is a claim
that a proof verifies. The corresponding Slurm reference gate remains pending.
Old parsers, prompts and run archives are unchanged. No model pilot is frozen or
authorized, and this module has no transport, credential or verifier code.

Input is an exact JSON object mapping the task's editable filenames to body
strings, optionally enclosed by one whole-response JSON fence. Duplicate keys,
extra files, prose, multiple candidate objects, changed seed bytes and full-source
replacements are rejected. The **trusted host** supplies task metadata and pinned
empty sources; metadata is not accepted from model output. Protected prefixes,
suffixes, contracts, imports, decreases clauses, shared forwarding helper,
providers, clients and entrypoint are reconstructed from those sources.

The bounded grammar accepts:

- Fresh, non-shadowing `var name := expression;` locals, with lexical block scope.
- `if condition { ... } else { ... }`, assertions and whitelisted lemma calls.
- Self-recursion at the fixed signature. Termination remains Dafny's responsibility.
- A single-bound-variable `forall key | domain ensures property { ... }` proof
  block; bound names cannot escape their scope.
- Integers, booleans, pure conditional expressions, arithmetic/comparisons,
  membership, sequence literals/slices/indexing, `.Keys`, cardinality and the
  task's whitelisted opaque function calls.

It rejects arbitrary declarations, imports, comments, string literals, attributes,
assumptions, reveals, loops, assignments to existing locals, cross-helper delegation
and calls unavailable through the selected export view. No map comprehensions,
map literals/updates, explicit local types, lambdas, arbitrary quantifiers or
arbitrary Dafny syntax are supported. These are **treatment restrictions**, not
claims of full Dafny support or security isolation for arbitrary input programs.

The JSON/body/token/statement/nesting limits bound parser work. Syntax inventories
are descriptive; they do not evaluate operators or type-check expressions.
In particular, Dafny supplies the meaning of chained comparisons. `assert false`,
empty proofs and nondecreasing recursion can pass syntax admission and must then
fail semantic verification. Guard admission must never be counted as proof success.

Tests exercise exact reconstruction, immutable source boundaries, semantic-control
admission, export visibility, local/quantifier scoping, ambiguous output, adversarial
bypasses and complexity bounds. Alternative local names and pure conditional
expressions are admitted unchanged; **these alternative source bytes have not yet
been verified**. The archived log and hashes identify the tested implementation.

Before a future model pilot: complete fixture verification, review and pin this
policy against the final revision, verify any newly proposed alternative proof
bytes on compute nodes, write explicit syntax instructions, and separately review
the fixed prompts, trial order and request budget. No such execution is authorized
by this prototype.

Run offline tests from the repository with:
`python3 -B experiments/monorepo-reasoning-expansion-001/protocol/test_body_guard.py`.
