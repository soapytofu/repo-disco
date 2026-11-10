# Varied monorepo corpus and family split

**Proposal, November 6, 2026 Eastern. No new model calls authorized or made.**
This is the active next-stage design, replacing the unexecuted 192-call main-corpus
recommendation in the [earlier plan](weeks5-6-corpus-plan.md). Historical experiments,
freezes and scores remain unchanged. The [machine-readable task list](../experiments/matched-corpus-002/plan.json)
contains 18 proposed semantic instances, not implemented fixtures or frozen prompts.

## November 9 implementation checkpoint

The four C1 development cases are now [implemented and verified](../experiments/varied-calibration-001/RESULTS.md):
126 primary controls matched expected outcomes, and 16 analyst alternatives
verified strictly. The [calibration proposal](../experiments/varied-calibration-plan-001/README.md)
freezes 16 exact workspace requests and 32 balanced trial slots, with no execution
authorization. This is the first 32-call stage below, not extra budget. The
machine-readable November 6 proposal retains its original historical status
fields; current concrete contracts, lineage limits and two documented client/
existential-proof implementation choices are described in the verified results.
All M1/M2 and reserved-family tasks remain unimplemented by this calibration work.

## Recommendation

Build **12 development instances in four familiar proof families**, and reserve
**six test instances in two new generator families**. Each instance has the same
four structural cells: shallow/shared, shallow/separate, deep/shared and
deep/separate. These yield **72 monorepo workspace variants**. The proposed staged
budget is **32 calibration + 64 development collection + 48 reserved-family test =
144 new calls for one model**, with two independent responses per variant.
Every paid stage needs its own later scope approval. Today's work is a zero-call
proposal and split review; there is no dispatcher or execution-ready prompt freeze.

The aim is broader obligations, not an arbitrary target failure rate. Keep easy
contrasts and publish ceilings/floors. Do not create apparent diversity by changing
names, constants, module wrappers or proof length. The corpus still measures
contract-guided helper synthesis inside one monorepo, with two immutable clients;
separate external repositories and invented specifications remain outside scope.

## What the evidence changes

The latest [witness/map pilot](../experiments/witness-map-calibration-pilot-001/RESULTS.md)
had 16/16 admitted outputs and 8/16 strict successes, but only **two semantic
instances**. Six witness failures share one incorrect endpoint choice. The two
[analyst map diagnostics](../experiments/witness-map-diagnostic-001/README.md)
separate a missing value fact from trigger warnings; neither changes the score.
These results justify distinct failure categories and more semantic coverage,
not a general causal sharing/depth claim.

Keep all existing clamp, sequence, interval, map, repair, extension and baseline
artifacts in development. Existing easy tasks remain regression anchors and are
not counted among the 18 new proposals or charged again in this budget.

## Proposed development tasks

C1 is the family's calibration instance; M1 and M2 are reserved for later
within-family development collection. Their conceptual descriptions are visible
now; their exact proofs, prompts and output distributions are not yet available.

| Family | C1: calibration | M1: collection | M2: collection | New obligation / principal controls |
| --- | --- | --- | --- | --- |
| D1 Conditional arithmetic | Clamp is nonexpansive: distance between clamped values is no larger than the input distance | Nonnegative soft thresholds compose: `Shrink(s,Shrink(t,x)) = Shrink(s+t,x)` | Saturating addition associates for nonnegative operands and cap | Region selection for intermediate values, two-input inequalities and saturation. Wrong equality/sign cases and unjustified unsaturated substitutions must fail. |
| D2 Sequence structure | Prefix-sum splitting with explicit slice bounds | Adjacent-run compression is idempotent, via a protected no-adjacent-equals invariant | Equal-length weave/unweave reconstructs both input sequences | Index bounds, output-shape invariants and paired recursion. Test off-by-one, missing boundary/base case, wrong projection and nondecreasing recursion. |
| D3 Witnesses and certificates | Allocate a total between two bounded integer variables, preserving their sum | Return either an interval-intersection witness or a valid separation certificate | Choose an integer in a nontrivial interval different from an excluded point | Coupled choices, positive/negative certificates and disequality. Test invalid endpoint choice, lost conservation, touching intervals and excluded-endpoint cases. |
| D4 Map state and frames | Swapping two present keys twice restores the map, including aliasing | Two fresh-key moves compose to a direct move | Restriction distributes over a disjoint map merge | Value history, changing domains and pointwise equality. Test stale/absent reads, missing freshness, intermediate-key removal and wrong domain/value branches. |

Exact assumptions and targeted controls are in `plan.json`. For example,
allocation requires `a<=b`, `c<=d`, `a+c<=T<=b+d`; its result must satisfy both
bounds and `u+v=T`. The exclusion task requires integer `a<b`. The latter is
intentionally a simpler contrast, not an asserted harder task. Allocation is
related algebraically to interval intersection and stays in that ancestry group.
Prefix splitting inherits the sum/append line. New obligations within a family
are **not** claimed to be independent proof families.

## Reserved test families

These are **candidate reservations**, not already certified held-out data.
Describe targets now, but postpone concrete solutions and task-specific model
prompts until the development protocol is frozen.

| Reserved family | Three proposed targets | Boundary of the claim |
| --- | --- | --- |
| H1 Recursive-tree reconstruction | Mirror involution; tree zipper focus/plug reconstruction along a valid path; leaf frontier of a mirrored tree equals reversed original frontier | New branching-structure generator. Induction and sequence lemmas may transfer from development; mirrored-frontier is not conceptually unrelated to reverse/concat. |
| H2 Finite-state transition invariants | Reservation/release capacity safety; token consumption at most once between resets; refinement of a one-slot buffer's concrete traces to an abstract send/receive history | New transition-system generator. Generic arithmetic and trace induction may transfer; this is not a claim of unseen mathematical concepts. |

The older finite-set-witness reservation is not adopted: membership, witness and
map-domain work already make that boundary ambiguous. A tree/transition family
also fails admission if it merely wraps an existing sequence/map solution. Audit
actual definitions, reference bodies, template ancestry and normalized proof
shape—not only directory or topic names. If a proposed family fails the audit,
record the rejection and revise the proposal **before any test calls**; do not
quietly fill its quota with siblings of an easier or harder observed task.

### Hold-out discipline

1. **Group by ancestry before variants.** All four structural cells, renamings,
   constants, sibling templates, solutions, failures and diagnostic repairs stay
   with their semantic instance and ancestor family. Generic harness code may be
   shared; copying a task's proof skeleton is an ancestry link.
2. **Separate tuning from evaluation.** Use C1 cases and existing development
   artifacts for output policy, prompting and inference decisions. M1/M2 are a
   within-family collection, not an unseen-family test; if later used for training,
   their scores cannot be presented as held-out evaluation of that trained system.
3. **Freeze the system before constructing test solutions.** Pin model/settings,
   prompt template, extraction and edit grammar, scoring, stopping rules and allowed
   typed syntax. Exercise generic datatype/match/trace syntax on development-only
   toy examples first. Task-specific symbol registries may then be populated from
   protected test interfaces under that fixed rule, without learned proof hints.
4. **Validate test fixtures without tuning the solver.** Deterministic reference,
   negative-control, contract and grammar checks are allowed. A fixture correction
   must preserve its predeclared target and be recorded before evaluation. If test
   solutions or outcomes motivate changes to prompts, grammar, inference, task
   selection, training or hyperparameters, retire that family from the primary
   test and reserve a fresh family for the next system version.
5. **Keep evaluation artifacts out of training and retrieval.** Test references,
   controls and model outputs are excluded from training exports, few-shot examples,
   repair prompts and retrieval indexes. Split and ancestor IDs must travel with
   every record. Do not construct training trajectories from held-out failures.
6. **Evaluate a frozen configuration once.** The planned two fresh samples are
   independent attempts, not feedback retries. After examining test results, any
   revised system evaluated on the same tasks is labeled test-informed follow-up,
   not a fresh primary held-out result.

This is an **author-visible, protocol-frozen family holdout**: we must inspect
references to validate fixtures, and the repository is public. It is not a blind
external benchmark and cannot establish absence from model pretraining. A separate
custodian such as a collaborator could strengthen blinding later; that is optional,
not a dependency or permission to contact anyone. The current reservation has no
implemented references, exact prompts, results or independence certification.

## Matching and depth policy

For each instance, preserve the final client semantics, target count, protected
contracts, model settings, names and output policy across four cells. Use full
source plus an automatically derived **file-level** dependency map in every
condition. Reference proof graphs, negative controls, solutions and prior outputs
never enter the model context. The model's export visibility and the checker's
visibility must be documented separately.

Shared mode has one editable helper reused by two clients; separate mode has two
editable, equivalent helpers and allows copying. Both may use common provider
lemmas. Record output-body count, source size and token cost; the comparison is
repository completion under different reuse/workload structures, not equal-work
cognitive difficulty or independent discovery of two proofs.

Replace a universal numeric depth target with **family-specific interface
factorization**. Record separately:

- Import graph depth.
- Reference contract-application dependency graph, counting actual prerequisite
  edges, not source call order or number of calls.
- Alternative verified proof routes and observed resolved call/use graphs.
- Targeted contract-ablation sensitivity for each distinct client.

All 18 proposals currently have **unknown numerical proof depth**. A deep label
is provisional until references and ablations support a meaningful factorization
difference; no minimum-depth claim follows. In particular, earlier map key-set
facts permit a different order of value observations. If a shallow/deep pair is
not defensible before model collection, record the design failure and revise its
scope/counts; never retain a fake depth contrast or drop a cell after seeing model
performance. Publish per-pair API, source length, editable-body and token mismatches.

## Build and acceptance sequence — no model calls

1. Start with D3-C1 allocation and D4-C1 swap, since existing evidence exposes
   witness-choice and value-frame errors. Then build D1-C1 and D2-C1. These are new
   versioned fixtures; prior frozen tasks and scores remain untouched.
2. Use immutable provider/client definitions and fixed helper signatures. Validate
   functional specifications for vacuity and missing requirements. Strictly verify
   all included files on a live-confirmed nonpreemptible Cannon compute partition.
3. For every variant require a reference success, empty-body proof failure and at
   least two distinct targeted semantic negative controls. Each family also needs
   a boundary and wrong-instantiation control; induction families need termination
   controls, and export restrictions need explicit name-resolution controls.
   This is a floor of **288 verifier checks for 72 variants**, plus additional
   distinct controls—an estimate, not completed evidence or independent trials.
4. Confirm two distinct clients rely on the helper guarantees by targeted contract
   ablations; ensure client safety is not proved vacuously. Guard all immutable
   bytes and forbid bypasses such as `assume`, axioms and verification-disable
   attributes. Preserve original failures and exact diagnostic categories.
   Semantic negative controls must preserve the protected task contracts. Attempts
   to weaken a precondition are separate guard-rejection checks, not proof failures.
   If an omitted fact is automatically inferable and the negative still verifies,
   retain that evidence and revise the control before freezing; do not mislabel it.
5. Replay known syntax forms through the existing tolerant envelope and bounded
   body guard. Extend syntax only as a separately versioned development protocol
   when necessary. More permissive extraction must not repair JSON or proof code.
6. Freeze the calibration's 16 variants, 32 requests, exact order, policies and
   budget before seeking paid approval. Test families are not included in that
   calibration. Implementation or guard incompatibility is a build gate, not a
   reason to spend requests on invalid tasks.

After calibration, inspect the failure mechanisms and validity—not a required
success-rate band. Any redesign or extra calibration needs a new version and
budget. Before collecting M1/M2, freeze their targets and forbid task selection
based on preliminary model answers. Complete the lineage/protocol audit and
verifier checks before admitting H1/H2 to the final test freeze.

## Proposed budget and collection order

| Stage | Semantic instances | Workspace variants | Samples per variant | Proposed calls |
| --- | ---: | ---: | ---: | ---: |
| Zero-call construction and preflight | All 18 proposed | Up to 72 | No model sampling | **0 now** |
| Development calibration | 4: one C1 per development family | 16 | 2 | **32** |
| Development collection | 8: M1/M2 per development family | 32 | 2 | **64** |
| Reserved-family evaluation | 6: three per reserved family | 24 | 2 | **48** |
| Total for one model | **18** | **72** | 2 | **144** |

These counts replace the unexecuted older 224-call recommendation; they are not
additional to it. Earlier exhausted budgets are never reused. A second model on
the identical collection and test cohorts would add **112 evaluation calls**;
new model-specific calibration or feedback repair would be separately designed
and budgeted. Fine-tuning and large open-ended generation are not covered here.

Use four Williams orders of the four structural cells, interleave families and
reverse each order for the second independent sample (the opposite row in the
listed square). Stage totals permit exact overall position/first-order balance.
Three test instances per family cannot each give perfect within-family row balance;
publish the residual imbalance and do not claim otherwise. Seed `20261106` fixes
ordering, not provider sampling. The complete trial list is created only at the
source/prompt freeze. Counterbalance consistent API renamings across whole pairs
if used; they remain siblings, not extra instances.

Each batch has a durable reservation ledger, exact trial IDs, zero SDK retries,
no Slurm requeue and no reassignment. Use fresh conversations without feedback.
Stop on ambiguous transport or infrastructure failure and preserve evidence;
ordinary parser, guard, warning or proof failures are completed outcomes. Recovery
requires reconciliation of all ledgers, never an automatic replacement call.

For scale only, the last pilot averaged about **3,280 input and 725 output tokens
per call**. Applying that observed mean mechanically to 144 calls gives about
**0.58 million tokens**; new tree/trace inputs and proofs may be longer. This is
not a spending quote. Exact model availability, output cap and current lab billing
must be checked at the later execution freeze; no dollar fit is claimed now.

## Evaluation and deliverables

Primary outcome is **strict whole-workspace completion**: admitted output,
protected contracts/source, all included files verified, exit zero and no warnings.
Report extraction rejection, edit rejection, frontend/name error, proof failure,
warning-only exit, truncation and transport/infrastructure failure separately.
A warning-only proof does not become a strict pass after an analyst edit.

Publish planned, reserved, confirmed-dispatched and returned counts. For a complete
stage, successes are out of all planned/dispatched requests. If interrupted,
report successes out of attempted reservations together with attempted/planned
coverage and ambiguous requests; do not present the partial rate as a completed
cohort. No failed task is silently removed or replaced.

Report each family and each semantic instance before aggregate rates. Compute
shared-minus-separate contrasts within each interface and interface contrasts
within each sharing condition, averaging the two samples per cell first. Keep
calibration, development collection and held-out-family results separate. Summarize
families with equal weights and show the two test-family results individually.
Exploratory intervals may resample whole instances with their four cells intact;
never treat 144 responses or 72 variants as independent problems. Eighteen designed
instances and two reserved families do not support a population-wide causal claim
or a power guarantee.

Record token cost, verification time, accepted-body duplication, distinct-client
reuse and ablation sensitivity alongside success. Inspect all successes for
contract fidelity/shortcuts and all new failure categories; analyst diagnostics
get separate records and never revise the primary score. Export only verified,
contract-preserving **development** trajectories for later training, deduplicated
with ancestry and normalized proof structure as well as byte hashes. Accepted
corpus size is measured after collection, not a quota warranting extra calls.

Deliverables before paid approval: implemented task/source manifest, family and
ancestor assignments, reviewed strict reference/control evidence, per-pair mismatch
table, separate reference/observed/ablation graphs, common policy/version tests,
source/prompt hashes, exact order, bounded runner and stage-specific budget. Today
only the task/split/evaluation proposal and its consistency review are complete.
