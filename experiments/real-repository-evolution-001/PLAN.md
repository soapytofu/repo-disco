# Real-repository repair and progressive extension

Prepared November 16, 2026 for the November 24 meeting with Nada. This is a
source-reviewed implementation plan, not a completed evaluation or an authorized
model run. [source-audit.json](source-audit.json) records four candidate upstream
commits, files inspected and unresolved baseline requirements. No new model,
provider connectivity or verifier calls were made during this preparation.

## Why this is the next step

The existing corpus primarily uses constructed Dafny scaffolds, supplied contracts,
and task-specific proof grammars. The four completed new-client extensions each
started independently from one of two verified small seeds. They establish
constrained extension, not a sequence that keeps growing an online repository.

The next milestone is to start with existing formal codebases and evaluate
contract-preserving repairs and a short chain of additions. The original
structural research question stays open. Real-repository feedback results would
test transfer beyond our constructed tasks; they would not isolate causal
dependency-depth or shared-proof effects.

## Source-reviewed shortlist

| Candidate | Initial component to inspect | Main reproduction gate |
| --- | --- | --- |
| [Dafny-VMC](https://github.com/dafny-lang/Dafny-VMC) | Fisher-Yates interface/implementation/model and supporting arithmetic/probability modules | Use the actual verification script and its pinned Dafny 4.4.0 environment; example builds use --no-verify. Existing termination exemptions and trusted boundaries must be disclosed. |
| [Dafny standard libraries](https://github.com/dafny-lang/dafny/tree/8c137ba351c60a521cfb122011770fdbea9a0453/Source/DafnyStandardLibraries) | Connected collection, parser or JSON modules; exact sites pending review | Verify pinned library source with a compatible Dafny build. Merely importing the preverified standard-library binary does not verify our edits. The older dafny-lang/libraries repo is deprecated. |
| [Vest](https://github.com/secure-foundations/vest) | Handwritten dependent-format clients plus imported combinator contracts and proofs | Use its pinned Verus/Rust versions and the full verification scope. Focused checks exclude dependency proofs. Existing DSL-generated code is not LLM output. |
| [Verified Storage](https://github.com/microsoft/verified-storage) | pmemlog arithmetic helpers and their actual log callers | Reproduce its recorded Verus toolchain and provider/consumer verification; preserve the trusted storage specifications. Runtime/compatibility remain unknown. |

These are four candidate upstream repositories, two per language. Libraries,
examples, and research systems must be labeled as such; “online repository” is
not synonymous with industrial production software. Two components from one
repository do not become independent repositories. Shared upstream library
ancestry must be recorded. All candidates are development material after inspection.

## First gate: reproduce the unmodified code

For each candidate, record commit/submodules, license, toolchain/solver/lockfile
versions, exact source bytes, resource limits, verification command, entry/module
scope, dependency proof coverage, raw output and return status. Review setup
scripts before execution. Run verification only on nonpreemptible compute nodes;
do not execute Dafny or Verus verification on the login node or local Mac.

Inventory existing extern/axiom/assumption/termination exemptions and trusted or
unverified files. Preserve those boundaries and prohibit newly introduced proof
bypasses. A successful build or test suite is distinct from proof verification.

First reproduce the declared package verification scope. If a large project
requires a smaller dependency-closed component, explicitly name the narrowed
scope and its fixed external assumptions. Never label a component check as
verification of the entire upstream repository. Preserve baseline failures and
version incompatibilities; correct them only as deliberate versioned work.
Inspect prior submission state; no duplicate submission or automatic retry.

Eligibility requires an unmodified passing scope and reproducible task controls.
Target four repositories; if fewer pass before the collection freeze, report
every exclusion and reduce the scope/budget. Do not substitute convenient tasks
after model outcomes have been inspected.

## Lane A: repair real source with a matched feedback comparison

Target two distinct task sites per eligible repository (eight if all four pass).
Each must have a real caller/provider relationship, not an isolated arithmetic
snippet copied into a new synthetic file. Prefer varied obligations: composition
of interfaces, dependent length/range checks, invariants or library lemma use.

A task may be a deliberately masked proof/implementation, an explicitly requested
interface-preserving change, or a documented historical failure. Label its origin.
An induced failure is not a newly discovered upstream bug. Keep unmodified
upstream solutions in the audit archive and out of model-visible candidate bodies;
audit other files for equivalent copied solutions. Public pretraining exposure
cannot be excluded.

Before freezing each task, show original/reference success and a meaningful
failing starting candidate in the declared scope. Confirm that empty bodies do
not pass trivially. Protect public contracts, provider assumptions and build
configuration; declare exact editable bodies/files. The old small Dafny grammar
is not automatically suitable for real Dafny or Verus. Validate a language-specific
output/region policy offline and verify its accepted control candidates.

Primary comparison: failure notice versus raw verifier diagnostics, identical
source/task instructions/context and equal one-response budgets. Two independent
responses per task-arm; counterbalance request order. Do not transfer feedback,
solutions or state between arms. Full source for the scoped component and a
declared dependency map is the initial context policy; log truncation or retrieval
if an explicit context limit requires a revised design.

A counterexample/contract-context augmentation is a useful subsequent ablation.
Prepare it without conflating it with the primary comparison: an augmented
counterexample must be validated against the task assumptions and failed
obligation; a solver model is not automatically a concrete runtime failure.
Record tool outputs and costs. Do not insert analyst repair hints into one arm.
Freeze a separate scope and budget before any additional model trial.

## Lane B: grow a verified repository in sequence

For each eligible seed, predefine two meaningful extension requests:
1. Add a new client/operation and its required specification, using existing APIs.
2. Build a second client/property that actually uses the first accepted addition.

The host reviews and fixes requested behavior before generation. The model writes
implementation/proof code; only declared module-registration changes are host
owned. This is initially contract-guided evolution. Open-ended specification
invention is a later, separately reviewed mode.

Verify the old scope plus each new addition and relevant tests. Check both intended
functionality and unchanged existing behavior/specifications. Store parent hash,
request, patch, verification evidence and accepted child revision. Step two starts
from the accepted step-one snapshot, not the original seed. If step one fails,
step two is blocked and its slot is not reassigned. Record a blocked child as
undispatched, not as a proof failure.

Freeze extension specifications, prompt templates, source-selection rules and
slot order before dispatch; archive each exact instantiated prompt and its parent
hash. Reject duplicate/empty wrapper additions as evidence of substantive growth.
Measure new behaviors/contracts/modules and actual uses of accepted additions;
syntactic call counts alone do not establish necessary proof dependence.

## Proposed call ceiling, not authorization

At four eligible repositories:
- Repairs: 4 repositories x 2 task sites x 2 feedback arms x 2 responses = 32 calls.
- Growth: 4 seed repositories x at most 2 sequential additions = 8 calls.
- Total: at most 40 new calls, one model, zero automatic retries or reassignment.

This is a planning estimate, not a frozen paid scope. At N eligible repositories,
the corresponding ceiling is 10N. A two-repository pilot with both languages
would be 20 calls. Extra models, augmentation arms, task generation or repair
rounds require their own explicit budget. The previous 128-call session remains
terminal after its ambiguous request; no remaining slots or credentials are reused.

First complete the task controls, language-specific guards/scoring and bounded
runner tests. Then present exact reviewable prompts/settings, handler hashes,
call accounting and compute plan for a new user decision. No new model calls
are authorized by this plan.

## Results that would be useful on November 24

Deliver baseline reproduction records and an eligibility table; repair outcomes
by repository, task and feedback condition; per-stage extension lineage; and one
fully inspected success/failure case in each language where available. Preserve
all logs and rejected outputs.

Primary outcome is verification of the declared complete scope, with all targeted
and required dependent obligations checked and no new trusted escape. Separately
report frontend/parser rejection, guard rejection, proof failure, warnings,
timeout and infrastructure failures. Include per-target outcomes, token/call
costs, wall time, specification fidelity and accepted changes.

Report language/repository results separately. Different toolchains and task
difficulty prevent interpreting Dafny-versus-Verus totals as a causal language
comparison. Repeated responses and extension descendants are clustered under
their source task/repository, not independent tasks or held-out families.
Passing against a weak supplied contract does not establish missing semantic
properties. A meaningful negative result is acceptable; successful proofs
cannot be promised in advance.

## Working schedule and immediate action

- November 16–17: source and trust-boundary audit, pinned setup, reproduce baseline scopes.
- November 18–19: choose task sites, verify fail/pass controls, implement/test Verus adapter and edit policies.
- November 20: freeze eligible tasks, exact repair prompts and extension templates; review proposed paid scope.
- November 21–22: run only a separately approved bounded collection; preserve partial stops and failures.
- November 23: audit accepted sources, metrics and lineage; prepare results and two case studies.
- November 24: discuss external-validity evidence and the next structural/tool-feedback experiment.

The immediate next work is baseline reproduction, starting with Dafny-VMC and
Vest. Standard libraries and pmemlog follow as independent candidates, subject
to pinned build feasibility. No call to a model is needed for this stage.
