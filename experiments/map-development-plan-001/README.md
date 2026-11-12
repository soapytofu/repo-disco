# Two-operation map development follow-up

November 12, 2026. **Frozen proposal: 16 calls, zero authorized or dispatched.**
Seven offline tests pass. No provider client, model runner or credential handling
is part of this plan. Source/evidence commit:
`5aa2ac109678546f30d623249f34cfaf54b6b16f`.

The question is whether the missing intermediate value/domain facts seen in map
swap recur on distinct operations: **fresh-key move composition (D4-M1)** and
**restriction over disjoint merge (D4-M2, corrected revision 002)**. Both were
selected in the November 6 corpus proposal before model outputs on these tasks.
They remain inspected map-development instances, not independent families or
held-out evaluation.

| Scope | Count |
| --- | ---: |
| Semantic instances | 2 |
| Bundled/decomposed interface × shared/separate helper workspaces per instance | 4 |
| Fresh-context samples per workspace | 2 |
| Proposed requests | **16 total** |
| Automatic retries, feedback attempts, reassignment, requeue | **0** |

These are the first 16 slots of the previously proposed 64-call development
collection, not 16 on top of it. The remaining 48 collection and 48 reserved-family
requests remain separate and unapproved. No earlier unused budget is reused.

## Frozen inputs and readiness evidence

[freeze.json](frozen-001/freeze.json) has SHA256
`84211b3fd2286cc0b6c8cb5b139c6856dc214270c09762c9dcc0f03f0fbe2097`.
It pins eight exact payloads, empty workspaces, task registries over the
quantified-expression grammar, the unchanged tolerant JSON extractor, target
scopes and 16 trial slots. References and negative diagnostics never enter
model context; full provider source and a derived import/include map do.

The pinned prospective settings inherit the prior calibration:
`global.anthropic.claude-opus-4-5-20251101-v1:0`, us-east-1, temperature 1.0,
4,096 output tokens per request (65,536 maximum across 16). This is not an
availability or pricing claim. Payloads are 10,242–11,518 UTF-8 bytes; token
counts are unmeasured. The fixed [order](frozen-001/trials.json) interleaves
instances and reverses which starts the second sample. Four Williams-square
rows balance relative cell positions; physical adjacent-trial transitions are
not claimed perfectly balanced. Samples use identical payloads in fresh contexts.

The freeze checks both manifests and all **76 current control outcomes**:
eight strict references, 60 proof failures and eight hidden-export failures.
Exact sources/contracts match reviewed compute archives. The restriction's initial
frontend failure is preserved separately. The plan also binds the raw evidence
and interpreter from the [five-case named-target diagnostic](../target-completion-diagnostic-001/RESULTS.md).
Those analyst controls are not model trials.

The new grammar admits quantified Boolean assertions rejected by the old swap
pilot. This is a different development protocol: preserve the old 27/32 score
and do not pool cohorts as one unchanged system or credit analyst repairs as
model successes.

## Evaluation

Primary outcome remains **guarded strict whole-workspace success**: protected
contracts/source, all includes verified, exit zero and no warnings. A prospective
runtime adds the validated CSV logger without weakening verification flags.

Secondary metrics group all obligations for each named editable helper contract.
Supplied providers and clients earn no model-edit credit. Report editable local
completion, supplied-client local verification, and client completion with
verified helper dependencies separately. Exact scopes and declaration inventories
are in [target-scope.json](frozen-001/target-scope.json). A rejected output earns
no completion credit; per-declaration verification is unavailable. Missing or
ambiguous CSV requires infrastructure review, never inferred target success.

Publish every cell denominator, extraction/guard/frontend/proof/warning category,
tokens and body duplication. Analyze instances separately before descriptive
interface/sharing contrasts. No output is replaced, silently removed or repaired
for scoring. Ambiguous transport, persistence or infrastructure failures stop the
batch for reconciliation; ordinary proof/policy failures consume their slots.

This cohort can show recurrence of the old failure mechanism or a ceiling on
the new tasks. Neither justifies selecting for a desired failure rate. Two
inspected instances cannot establish a general causal effect, necessary proof
depth, model ranking or held-out generalization. Separate mode has two copyable
bodies; shared mode has one plus a fixed forwarding wrapper. Shallow/deep denote
bundled/decomposed interfaces, with workload and source differences retained.

## Reproduction and execution gate

`python3 -B test_plan.py` runs seven offline tests, including exact regeneration
with network/process creation disabled, budget/order rejection, scoped syntax,
source/prompt bindings and target attribution. Existing freezes cannot be
overwritten. [Test log](offline-tests-001.log).

Before execution: test one bounded sequential runner using fake transport/verifier,
pin its code and these inputs, obtain **new explicit 16-call approval**, and
prepare a private key handoff. Authorization must bind both freezes and a finite
deadline. Check existing output/ledger/job state and live nonpreemptible partition
before one submission. This proposal authorizes no live connectivity test,
automatic restart, retry, model calls or alternate dispatcher.
