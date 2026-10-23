# Controlled corpus design: Weeks 5–6

Design draft, October 23, 2026. This is a proposal, not a measured model result. The composition pilot's 15 corrected deterministic controls passed; its 12 model trials are still queued at this checkpoint.

## What the current map represents

`composition-pilot-001` supplies module names and directed import/alias edges. The map repeats information already present in the full source. It does not identify which contracts a target proof needs, an ordering of lemma calls, or a dependency between proof obligations. Its benefit, if any, is therefore structural organization of visible information. Both conditions see provider implementations, while Dafny export boundaries hide definitions from the client's proof checker. These are different notions of visibility.

The current three tasks each require composing two provider calls in the reference proof. That does not establish a general corpus of long dependencies, and a two-call reference is not proof that no shorter alternative exists. Missing-call and incorrect-call controls establish failures for those particular bodies only.

## Units and primary outcomes

- **Repository task:** immutable source files, target proof body, protected contracts, entry point, and required verifier version. Assign a stable task ID and source hashes.
- **Trial:** one model response under a preregistered context condition, followed by edit validation and one whole-repository verification. Record dispatch before the request; preserve ambiguous transport outcomes without retrying.
- **Completion:** all included source verifies, protected bytes remain unchanged, and the permitted edit policy passes. Report successes / dispatched trials, with transport failures separately visible. Do not discard unsuccessful trials from the denominator.
- **Family:** common generator/template ancestry. Split by family before collecting training trajectories to prevent near-duplicate train/test leakage.

Report task-by-condition counts and paired differences before pooled percentages. Two replicates on three hand-designed tasks are exploratory; they do not justify general claims about repository reasoning or model ranking. Dafny's aggregate verified count is not a count of independent specifications.

## Separate structural and proof metrics

| Metric | Operational definition | Limitation |
| --- | --- | --- |
| Import depth | Longest directed path from the client in an acyclic module import graph; edge direction is importer to imported module | Imports can be redundant. Reject cycles for this corpus rather than silently assigning a depth. |
| Required proof depth | Longest prerequisite chain in a manually annotated graph of contract applications for the intended solution | Reference-relative until alternative proofs are audited; not inferred from imports alone. |
| Provider coverage | Number of distinct provider modules called in an accepted proof | Record resolved symbols, not aliases alone; more calls are not necessarily better. |
| Lemma reuse | Number of distinct client targets using each resolved provider lemma, plus the fraction used by at least two targets | Several repeats of the same task do not create additional client targets. |
| Shared-proof dependence | Number of target proofs that fail after a specified shared lemma contract is weakened/removed in a deterministic ablation | Run ablations on compute nodes; resolution errors and proof failures are distinct. |
| Repair cost | Dispatched requests, input/output tokens, accepted edits, and verification wall time per task | Keep failed attempts and transport outcomes; record model and pricing date separately if estimating dollars. |

Store import edges, intended proof-prerequisite edges, and observed call edges as separate fields. Mark annotations as intended, observed, or ablation-tested. Do not present an intended proof graph as model-discovered evidence.

## Matched comparisons to build before scaling

1. **Map presentation:** preserve the current full-source versus full-source-plus-map comparison as its own experiment. Add a separate, preregistered length control using an equally sized neutral source index. Token matching must use the actual model tokenizer/counting interface where available; otherwise report measured token differences and the approximation. A neutral appendix can still affect attention, so it is not a perfect placebo.
2. **Dependency depth:** construct shallow and chained proofs with matched module count, number of exported contracts, target specifications, allowed edit scope, and approximately matched source/prompt tokens. Keep useful API names equally available. Record unavoidable differences instead of claiming an exact match.
3. **Shared proofs:** compare multiple clients using a common helper against clients using separate equivalent helpers. Match target semantics, reference proof lengths, and total source size as closely as possible. This changes sharing rather than simply adding more targets.
4. **API naming robustness:** generate consistent, arbitrary API renamings across source, maps, references, and expected diagnostics. This is a separate factor; do not change names in only one context condition.

Balance condition order within each task and keep each request independent. Reserve held-out generator families before tuning prompts. Fix the request budget and stopping rule before any new paid batch; unused authorization from older pilots is not automatically a new budget.

## Build acceptance gate

Before a new model batch, on compute nodes: verify every reference with included files; confirm missing-proof and targeted ablations fail for the intended reason; reject parse/export errors as invalid fixtures; check source/map consistency and protected-byte enforcement; archive versions, hashes, commands, diagnostics, and seeds. Run offline prompt checks to ensure only the planned context factor changes. Freeze the corpus manifest before dispatch.

Next implementation milestone: a versioned manifest and validator for the three edge types above, with explicit DAG checking and deterministic metric output. Start with the existing fixtures without modifying the queued pilot's source or prompts. New fixtures and further paid evaluations require their own verification evidence and budget.
