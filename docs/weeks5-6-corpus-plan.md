# Weeks 5–6: matched cross-module monorepo corpus

**Current gate:** the first 32-call calibration is complete. A revised 32-call
proposal is now frozen after stronger task construction and 136 selected verifier
controls. Its model execution is not authorized. Main collection remains deferred;
see the latest update at the end.
The preparation plan below is retained to show the original design.

**Plan updated October 28, 2026 following Nada’s scope feedback. No model calls are
authorized. The user authorized non-paid calibration construction and verifier checks.** The initial Weeks 1–4 milestones
are recorded in [the acceptance review](weeks1-4-acceptance.md). This plan defines
the next experiment; all 16 calibration variants and exact 32-trial prompts are now built, verified and frozen. Model execution remains unauthorized.

## Scope: cross-module reasoning within one monorepo

The unit is a **single monorepo workspace snapshot** containing provider, helper,
and client modules under one source/version boundary. Clients consume contracts
from modules in that workspace. Shared proof reuse and dependency depth are
internal architectural properties. Separate Git repositories, cross-repository
version resolution, package managers and remote dependency integration are out of
scope, following Nada's suggestion.

The corpus stores alternative workspace snapshots in separate fixture directories
inside repo-disco. Variants are independently built through their own entry point;
they are not simultaneously imported into one Dafny namespace and are not treated
as dependencies between repositories. All required files must be checked within
each selected workspace. Previously saved repository-level experiments retain
their names and evidence; the clarified scope does not change their results.

The existing counts remain unchanged: 16 calibration snapshots and 96 main
snapshots. “Repository variant” below means an isolated monorepo configuration,
not a separate external repository or integration boundary.

## Research question and why the next batch differs

Measure how cross-module dependency depth and shared proof structure affect
**whole-monorepo completion and generation effort**, with contracts protected. Recent composition,
depth, agent and extension pilots reached ceiling success on small development
tasks. More copies of those easy proofs would increase volume without establishing
the proposed effect. First build structurally richer obligations and screen them
on a separate calibration set.

The primary task is **contract-guided proof synthesis for multiple immutable
clients**: the model completes allowed helper proof bodies, and the entire
repository must verify. This produces verified repository variants and saved
trajectories. It does not ask models to invent specifications or treat weak,
self-generated contracts as evidence of functional correctness. New-client
extension can remain a separate later collection track; do not pool its scores
with helper synthesis.

## Concrete corpus size

| Unit | Calibration | Main development corpus |
| --- | --- | --- |
| Development proof families | 4 | Same 4, with disjoint semantic instances |
| Underlying semantic instances per family | 1 | 6 |
| Structural variants per instance | 4: shallow/shared, shallow/separate, deep/shared, deep/separate | Same 4 |
| Repository variants | 16 | 96 |
| Independent one-response samples per variant | 2 | 2 |
| Experimental API requests | **32** | **192** |

The main corpus has **24 underlying semantic instances**, 96 structural variants
and 192 attempted trajectories. These are not 192 independent problems or 96
unrelated families. Up to 192 trajectories may verify; the number of unique accepted
repositories is unknown and may be much smaller after deduplication. Failed,
rejected and ambiguous trials remain in the experiment archive.

Six instances must vary actual obligations/preconditions or constructions, not
just rename symbols or replace constants in the identical proof. Track template
ancestry even when instances differ. The initial primary corpus is modest research
data, not a claim of sufficient scale for useful fine-tuning.

## Development and reserved families

| Family | Existing evidence / proposed harder obligation | Status |
| --- | --- | --- |
| D1 Conditional preconditions | Extend existing sign-case work to interacting guards and prerequisites that must be established before composing contracts | Development; original sign examples are already inspected |
| D2 Sequence induction and algebra | Explicit base/step reasoning with an intermediate relation, rather than only a longer list of Append calls | Development; inspected sum/append ancestry stays in development |
| D3 Relational composition with a join | Two prerequisite paths must establish compatible facts before the final client obligation | Development; existing relation/diamond templates remain development |
| D4 Finite-map update and frame preservation | Compose update contracts while preserving untouched keys and an invariant used by multiple clients | Development; verifier controls and guard validated |

Reserve two *candidate* later evaluation families: recursive-tree transformations
and witness-based finite-set constructions. Do not build/tune on their concrete
model prompts or responses during these stages. Before later evaluation, audit
actual template/proof ancestry and freeze the family split; topic labels alone do
not establish independence. If a reserved family shares the developed proof
skeleton or is used to tune the system, reclassify it as development. **No held-out
performance claim is possible now.** The reserved families consume zero calls in
this Weeks 5–6 plan; their implementation/evaluation budget is separate.

If D4 or a structural pairing cannot meet the verification/matching gates, stop
and revise the plan before collection. Do not quietly substitute a task family
or spend requests on invalid fixtures.

## What “matched” means

For each semantic instance use the same externally meaningful client targets,
preconditions/postconditions, two client modules, naming policy, model/settings,
output policy and end-to-end score across all four cells. Keep helper names and
contracts visible in every condition. Export views must prevent calling hidden
shortcut APIs. Do not reproduce the earlier hidden-helper-name test.

- **Sharing treatment:** one helper proof reused by both clients versus two
  client-specific helper proofs with equivalent contracts. Clients stay immutable.
  The separate condition inherently has more proof bodies/source to generate;
  this is part of the repository-level workload treatment. Record editable-body
  count, target count, bytes/tokens and output length. Do not interpret a success
  difference as a pure cognitive benefit of sharing at identical work. Auxiliary
  call-only shared/separate fixtures remain controls, not the primary treatment.
- **Depth treatment:** target a shallow versus three-stage reference dependency
  chain within each family, using the same final client semantics. The chain must
  require contract composition/induction; extra nesting, module names or redundant
  calls alone do not qualify. Record actual per-family reference depth and
  contract-ablation evidence. This is reference-relative, not proof of minimum
  possible depth. Changes in available helper decomposition are intentional;
  document them explicitly rather than claiming identical APIs.
- Match total module layout, non-target context and interface naming where feasible.
  Publish a per-pair mismatch table for unavoidable source length, editable-body,
  API and token differences. Never fill a condition with a solved duplicate helper
  that reveals the answer just to make its length match.
- Hold **full source plus declared file map** fixed throughout the primary study.
  This isolates architectural workload from a separate map-presentation experiment.
  Maps contain structural facts, not reference proof steps or privileged solution
  annotations. Reference solutions and ablation results never enter model prompts.

If a strict semantic pair cannot be built, label it unmatched and exclude it from
the paired comparison *before* freezing or running the model. Keep a record of
that design rejection. Do not drop valid tasks after seeing model failures.

## Week 5: build and calibrate

1. Implement a versioned manifest using existing repository/metric tooling:
   family/template ancestry, semantic-instance and pair IDs, seed, split, depth and
   sharing labels, immutable source hashes, entry point, allowed bodies, declared
   imports, reference-only proof graph, resolved helper identities and ablations.
2. Generalize only the guards needed by these proof languages, with adversarial
   tests for changed contracts, assume/axiom/reveal, verification-disable attributes,
   malformed or ambiguous output and edits outside the permitted scope. Freeze a
   common extraction policy within this experiment; do not mix historical parser
   results into its score.
3. On compute nodes, validate every reference and empty-body control; check targeted
   missing-prerequisite, wrong-argument/boundary and shared-contract ablations.
   Separate intended proof failures from explicit export/name controls. Each case
   must preserve the intended client semantics and actual staged source bytes.
   Expect several hundred verifier checks for the full set (roughly 600 if using
   six checks per main variant), **zero experimental API calls** for manual fixture
   construction and preflight. Record the final actual control count.
4. Freeze the 16 calibration variants and their exact prompts/order/settings, then
   request separate authorization for **32 calls**, two independent samples each.
   No feedback repair or SDK retries. Fresh context per sample.
5. Treat calibration as a diagnostic gate, not a significance test. A family with
   8/8 successes, 0/8 successes, or repeated parser/guard failures needs inspection
   before scale-up. Do not simply approve the main batch because infrastructure
   ran. The aim is interpretable proof difficulty, not a predetermined success rate.
   Publish ceiling/floor results even if the family is redesigned.

Calibration uses disjoint semantic instances and is never pooled into the main
result. Any redesign gets a new version and verifier controls. A further model
calibration is a new budget; it is **not** automatically included in 32 or 224.

## Week 6: freeze and collect the main corpus

After calibration review, build six production instances per family and all four
structural variants. Freeze source/contracts, instance IDs, lineage, split, model
ID, inference settings, parser/guards, reference-only data and all prompts before
the first main request. Start from the same approved Claude configuration as the
recent pilots unless a model change is explicitly recorded before this freeze.

Counterbalance the four structural cells within each semantic instance using a
four-order Latin-square rotation; reverse the order for the second independent
sample. Across 24 instances, allocate each order six times. Interleave families
and freeze the resulting dispatch list. Deterministic ordering seed: 20261028;
this does not promise deterministic provider sampling. No sample sees another
sample's response or verifier feedback.

Collect **192 calls** under one separately approved stage ceiling. For operational
checkpoints, partition the frozen dispatch list into four disjoint 48-request
batches, preserving the global order and balancing cells/families. Bind each quota
to its exact trial IDs and use one dispatcher per batch; never distribute a shared
cap among uncoordinated processes. Inspect completed ledgers before starting the
next batch. A fresh batch is a preassigned subset, not a retry allowance.

Run on a live-confirmed non-preemptible compute partition, no Slurm requeue, SDK
retry or automatic recovery. Reserve each request durably before dispatch. Stop
on transport ambiguity, source/hash drift, verifier infrastructure errors or
interruption, then reconcile evidence; do not replace that trial or reassign its
call. Ordinary parser/edit/proof failures are completed experimental outcomes.
Set job/deadline limits from calibration timing and bounded provider/verifier
limits; no queue-time guarantee is possible.

## Scoring, reuse and analysis

Primary score: whole repository verifies with strict exit zero **and** all edit
and source-integrity checks pass. Report end-to-end successes per dispatched
trial, with parser/edit/proof/infrastructure categories visible. Also report
planned/reserved/dispatched counts so a stopped batch cannot silently shrink the
denominator. Code that verifies under weakened or bypassed contracts never counts.

For each family, report the four cell rates, paired shared-minus-separate and
deep-minus-shallow contrasts, and requests/tokens/time per completed repository.
Keep the two samples grouped under their variant, and paired variants grouped
under their underlying instance. Descriptive uncertainty conditional on this
small development corpus is appropriate; four families do not support broad
population or held-out generalization claims. No power guarantee is made.

Keep import depth, intended reference proof depth, observed resolved calls and
contract-ablation dependence separate. Count sharing across **distinct client
targets**, not repeated trials. Inspect a stratified sample of successes and all
unexpected failure categories for specification fidelity and shortcuts.

Preserve full attempts, frozen prompts, raw responses, model/request IDs, tokens,
extraction decisions, candidate/parent hashes and raw verifier logs. Export only
verified, contract-preserving trajectories into the accepted corpus, deduplicated
by normalized proof/contract/template ancestry rather than byte hashes alone.
Train/development/held-out separation applies before downstream training, including
all ancestors and renamed siblings. Accepted-corpus size is an outcome, not a quota
that justifies unbudgeted replacement calls.

## Call estimates and optional work

| Stage | Calculation | Calls | Included in recommendation? |
| --- | --- | ---: | --- |
| Offline design and verifier preflight | No provider requests | 0 | Yes |
| Difficulty calibration | 4 families × 1 instance × 4 cells × 2 samples | 32 | Yes, first approval only |
| Main corpus | 4 families × 6 instances × 4 cells × 2 samples | 192 | Yes, gated on calibration |
| **Recommended total** | 32 + 192 | **224** | Proposed ceiling, not yet authorized |
| Optional map ablation | Fresh balanced subset: 4 families × 1 instance × 4 cells × 2 contexts × 2 samples | 64 | No; total would become 288 |
| Optional one-step repair | One feedback request for each failed main sample | 0–192 | No; worst-case total would become 416 without map ablation |

The optional map study must randomize/counterbalance both contexts together in a
fresh batch. Do not compare a later no-map batch against earlier all-map runs and
call it a clean context experiment. Optional repair is a separately labeled
adaptive trajectory; it does not change the original one-response score and is
not an independent pass@2 sample. Larger multi-model evaluation belongs to a
later, separately designed/budgeted phase.

Recent measured means were about 1,010 input/143 output tokens for the easy
extensions and 1,179/552 for the live agent. Harder multi-module tasks will likely
be longer. For planning only, assume **2,000–6,000 input and 500–2,000 output tokens
per request**: 224 calls would be approximately **560,000–1,792,000 tokens** total.
These are assumptions, not measured future costs. Check the actual model/region
and lab billing rates before approving a dollar cap; no current price or $1,000
funding fit is claimed here. No API token-count or connectivity calls were made.

The immediate next action is the **zero-call build/preflight stage**, not the
224-call batch. Freeze and review the 32-call calibration first; authorize the
192-call main stage only if the tasks and collection pipeline are informative.

## Calibration ready (zero model calls)

[monorepo-calibration-001](../experiments/monorepo-calibration-001/README.md)
contains all 16 configurations and the exact [32-trial frozen proposal](../experiments/monorepo-calibration-001/frozen-001/trials.json).
All 118 selected verifier controls match: 16 reference passes, 90 ordinary proof
failures, 4 intended termination failures, and 8 explicit hidden-name failures.
The initial sequence well-formedness failure is preserved; revision 002 adds an
explicit nonempty guard and passes all 34 sequence controls. Trusted providers and
client contracts match within each family. Eight guard tests and four freeze tests
pass, alongside the two four-test design suites and source/evidence audit.

The depth target has now been instantiated more precisely: conditional proofs use
one versus three stages per branch; sequence proofs use one versus three stages
per recursive step; the relational diamond has critical path one versus three
but one versus four calls; two map updates plus common Compose require three
versus seven calls. These are reference-relative contract dependencies, not raw
import depth, identical linear chains, or certified minimum proof depths.

The fixed wrapper in shared mode adds an import edge and reduces editable bodies
from two to one. This source/output workload difference and the guard's prohibition
on cross-helper delegation are disclosed. All templates remain development data.

Prompts contain only complete empty-body seed workspaces, declared file maps and
uniform output instructions. References and control results are excluded. Two
samples per variant reuse the same prompt independently; four Latin rows once
each, family interleaving and reversed second-sample order are frozen. Model ID,
settings, guard, source hashes and reviewed-preflight bindings are pinned. No model
requests, credentials or live dispatcher are used in this preparation.

Next: review this frozen scope and obtain separate 32-call approval before binding
a bounded dispatcher to it. Do not run the main 192 calls until calibration has
been analyzed. The larger main corpus is not built or frozen by this milestone.

## Calibration execution and scale-up gate (October 28 Eastern)

The separately authorized [32-call pilot](../experiments/monorepo-calibration-pilot-001/RESULTS.md)
completed in 7m20s:32 requests,32 unique IDs,zero SDK retries,101,595 tokens. Frozen
end-to-end score **18/32**:conditional 0/8,sequence 3/8,relational 7/8,map 8/8.
All fourteen other responses failed output checks before verification; all eighteen
admitted candidates verified. This is not evidence that deeper reasoning failed.

Five rejections were missing final newlines, six used unsupported pure inline if
expressions, and three failed the frozen JSON-wrapper rule. A separately logged
verifier-only diagnostic checked the first eleven with exact limited output-policy
adjustments: **11/11 verified**, no new requests. Original scores remain unchanged;
the three wrapper cases are not evaluated. Full raw archives and guarded-source
audits are published, including all failures.

**Do not start the main 192-call collection.** First version the output protocol
(body-only insertion and explicitly supported pure expression grammar), then
strengthen obligations and verifier controls where ceiling risk is apparent.
Any revised calibration needs a new freeze and separately approved call budget;
this run exhausted its 32 calls. Earlier no-execution statements in this document
record the preparation stage, not the current authorization history.

## Revised protocol and first stronger instance (October 29)

[Calibration v2 preparation](../experiments/monorepo-calibration-v2-001/README.md)
now implements body-only JSON insertion with immutable host-owned contracts and
file structure, plus bounded pure inline conditional expressions. Nine offline
tests pass, including exact reconstruction of previously verified examples. A new
alias-aware map-transfer instance has all four matched configurations validated:
job 56196595 completed 38/38 expected controls, including four references through
the new assembly path. Full source hashes and raw diagnostics are published.

This adds semantic obligations for aliasing, exact balances, conservation and
untouched entries; it does not establish greater model difficulty. The other
families still need substantive review/redesign before a complete revised pilot
freeze. No new prompts have been dispatched, no new model budget is authorized,
and the original 32-call experiment remains unchanged. Main collection is still
deferred.

## Revised calibration frozen (October 29)

The [new frozen proposal](../experiments/monorepo-calibration-v2-001/frozen-001/README.md)
has 16 variants and 32 independent one-response samples. It retains conditional
preconditions as a protocol anchor and substitutes weighted offset induction,
constructed interval witnesses and alias-aware transfers for the other instances.
All four families use body-json-v2.1, immutable host assembly, full source plus
declared maps, the previous model/settings, a new fixed Latin-square order,
no feedback and no retries. Preparation validates **136 selected controls**:
16 reference passes, 108 proof failures, 4 termination failures, 8 hidden-name
failures. Two unsuccessful relational provider revisions remain archived and
excluded from that validation set. Six freeze tests pass.

This proposes **32 additional calls**; none have been authorized or made. The
original 32-call outcomes stay unchanged, and the main 192-call proposal remains
deferred. Tasks and protocol both changed, so future before/after differences
cannot be attributed solely to either change. All instances remain development
data, with shared/edit-count and reference-depth limitations disclosed.
