# Cross-module monorepo calibration: 16 variants, frozen 32-trial proposal

**All four development families are built and verified. Zero model requests.**
The [frozen proposal](frozen-001/settings.json) contains 32 independent one-response
trials: four families × shallow/deep × shared/separate × two samples. A new paid
budget and a hash-bound bounded dispatcher are required before any collection.
Existing paid budgets are not reused. [Weeks 5–6 plan](../../docs/weeks5-6-corpus-plan.md).

## Reviewed deterministic evidence

| Family | References pass | Intended proof failures | Termination failures | Hidden-name failures | Total |
| --- | ---: | ---: | ---: | ---: | ---: |
| Conditional preconditions | 4 | 20 | 0 | 2 | 26 |
| Sequence induction, revision 002 | 4 | 24 | 4 | 2 | 34 |
| Relational join | 4 | 22 | 0 | 2 | 28 |
| Finite-map updates/frames | 4 | 24 | 0 | 2 | 30 |
| **Selected calibration controls** | **16** | **90** | **4** | **8** | **118** |

All 118 selected outcomes match their intended categories, with no unexpected
parse errors. These are source-fixture controls, not model success rates.

- Conditional job **55978267**, test, 1m14s: 26/26 expected. Original root fixtures,
  checks, raw verification-001 and results-review.json remain unchanged.
- Remaining-family job **56015268**, test, 4m07s: relational/map **58/58** expected.
  Initial sequence fixtures exposed a well-formedness error: an opaque predicate
  did not establish that a tail slice was in range. Full failed evidence is retained
  in [remaining-families-001](remaining-families-001/README.md); it is not counted as
  valid sequence calibration evidence, even where an intended negative also failed.
- Corrected sequence job **56016216**, test, 1m39s: **34/34** expected.
  [Revision 002](remaining-families-001/revision-002/README.md) adds an explicit
  nonempty guard inside StepReady; no helper/client contract or proof body changes.
  All 34 exact one-line source differences were audited.

Every job ran only on compute nodes with live-confirmed PreemptMode=OFF, no requeue
and no model transport. Full source snapshots, source/code hashes, commands,
stdout/stderr, exit categories, submission/environment records and failed controls
are archived. The stricter offline review distinguishes well-formedness and
termination failures from ordinary pre/postcondition failures.

## What is being compared

Each case is one monorepo workspace with trusted providers, editable helper bodies
and two immutable clients. Independent fixture directories are alternative
configurations; there are no dependencies between separate Git repositories.

Conditional proofs normalize/reflect interacting inputs; sequence proofs require
explicit induction; relational proofs join two prerequisite facts; map proofs
preserve an invariant and untouched keys through two distinct updates. Within each
family the client and trusted-provider bytes are identical across all four cells.

Depth refers to **provider-contract composition**, not import-graph depth or proven
minimum proof length. Sequence uses 1 versus 3 stages per recursive step, with the
same base case and recursive obligation. The relational diamond uses 1 versus 4
calls with critical paths 1 versus 3. Map proofs have two update chains and a common
Compose lemma, totaling 3 versus 7 calls. Do not pool these as identical linear
chains. [catalog-audit.json](catalog-audit.json) records actual source sizes,
imports, reference calls, matching checks and source-to-verifier bindings.

Shared mode edits one helper; a fixed wrapper serves client B. Separate mode edits
two equivalent helper bodies. Source size, output workload and the forwarding edge
differ. The guard forbids delegating to another editable helper, but copying proof
text between bodies remains possible. This is a workload/architecture comparison,
not a claim of sharing's cognitive benefit at identical work.

## Guard and frozen proposal

[GUARD.md](GUARD.md) specifies calibration-body-v1: one tolerant JSON extraction
policy, exact file set and immutable bytes, bounded proof grammar, task-specific
call allowlists, no assume/reveal/bypass attributes. Semantic validity is decided
by whole-workspace Dafny verification. Eight adversarial guard tests pass, including
byte-exact replay of every accepted reference. The first and remaining design
suites each have four passing tests. Four freeze tests pass; catalog-audit.py checks
all 118 exact verifier inputs and the single-line sequence correction.

[frozen-001](frozen-001/) contains:

- Exact empty-body workspace sources, 16 prompts, system instruction and settings.
- [32 trial records](frozen-001/trials.json), two identical-prompt independent
  samples per variant, fresh context and no feedback. Four cyclic Latin rows are
  assigned once each; families are interleaved; the second sample reverses cell
  and family order (seed 20261028).
- Claude Opus 4.5 model ID from the previous pilot, us-east-1, temperature 1,
  maxTokens 4096, strict verifier timeout 30s; no automatic retries or reassignment.
- Guard/code pins, reviewed-preflight bindings and [file hashes](frozen-001/freeze.json).

Only full seed sources and a declared file map enter prompts. Reference solutions,
negative controls, ablation outcomes, proof graphs and prior model responses do not.
The 16 prompt sizes are 4,887–6,472 UTF-8 bytes; these are not API-token estimates.
The four instances are development/calibration data, excluded from the proposed
main set. The 192-call main corpus remains gated on calibration review.

No credentials were read, no model calls made, and no live dispatcher submitted.
