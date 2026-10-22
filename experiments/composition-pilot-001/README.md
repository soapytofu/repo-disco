# composition-pilot-001: composing contracts with full source context

**Status (October 22, 2026):** all three tasks and the paired 12-call pilot are built. Six offline tests passed. Verifier controls are queued as Cannon job 54727417 (moved from test to shared CPU partition); model calls have not started and are gated on all reference/negative checks passing.

## Question

Can Claude compose facts across provider modules when all API names, contracts, and source files are available? Does adding a redundant structural dependency map improve success? This follows context-pilot-001, where missing API information caused invented helper names.

Three assistant-authored tasks each have two protected provider modules and one editable client. Opaque definitions are exported with `provides`, so client proofs use the exported contracts rather than revealing implementation bodies. Both model conditions still receive the complete provider source as text. No task hides API names from either condition.

| Task | Required composition in reference proof | Target |
| --- | --- | --- |
| Range / precondition | Establish `Bounds.Ready(x)` from numeric bounds, then use it to satisfy `Transform.EvaluateShift`'s precondition | `Shift(x) > x` |
| Relation lifting | Compose two `OrderFacts.Before` relations with `Transitive`, then pass the derived endpoint fact to `Reachability.Lift` | `Reach(a, c)` |
| Sequence composition | Establish the length of a concatenation, use nat nonnegativity and the positive prefix length, then call `SequenceProperties.FromPositive` on the concatenation | `Nonempty(s + t)` |

These are small compositional proof tasks, not a representative benchmark. The reference requires two relevant calls, but we do not assume the reference is the only possible proof. We explicitly check that either reference call alone does not discharge the target.

## Design frozen before model requests

- **12 independent single-request trials:** three tasks × two conditions × two repetitions.
- `full_context`: complete repository source, common task/edit instructions, and original missing-proof verifier feedback.
- `with_map`: the exact same prompt plus a JSON list of modules and their import aliases/edges. The map is checked against source imports and contains no proof-step order, lemma selection, or target-specific hints.
- All API names, contracts, and implementation source are identical in both conditions. Input token counts differ because of the map appendix; the design does not isolate organization from input length. Output caps and verifier budgets are equal.
- Alternating paired condition order by task/repetition, recorded in [plan.json](plan.json); no randomization or fixed sampling seed. No history or earlier trial feedback is sent.
- Model: `us.anthropic.claude-sonnet-4-6`, AWS Bedrock `us-east-1`, provider-default temperature, 4,096 output tokens, SDK total attempts 1.
- 60-second whole-repository verifier timeout. No retries. Stop the batch on an API error or timeout. Every dispatch is counted before its request; existing output directories cannot be overwritten.
- No early stopping on success: the planned condition counts remain balanced if the batch completes.

## Verification and edit controls

Every task has five fixtures: reference, empty proof, first call only, second call only, and incorrect composition (wrong order or arguments). The reference must verify; each negative control must fail a proof obligation, rather than a parse error, name-resolution error, or timeout. All providers are identical across a task's variants. The model pilot is gated on all 15 checks matching those expectations.

Only the final client lemma body can change. The guard retains exact bytes outside it after normalizing outer whitespace and a final newline. The body allows qualified lemma calls with parameter expressions using identifiers, integer literals, commas, parentheses, plus, and minus. It permits unknown names for Dafny to reject rather than supplying an answer whitelist. It rejects assumptions, weakened contracts, assertions, additional declarations, comments, and attributes. This is a deliberately constrained proof-composition pilot, not a general Dafny edit parser.

Whole-repository acceptance uses `dafny verify --verify-included-files Client.dfy`. Providers are copied unchanged into every candidate. Dafny's aggregate verified-obligation count is not treated as an individual-specification success rate. Logs distinguish edit rejection, name/parse errors, proof failures, timeouts, and successful verification.

Six offline tests check the reference/negative bodies, protected contracts, rejection of assumptions, exact map/source consistency, paired prompt equality except for the appendix, and a balanced 12-call plan.

## Evidence and reproduction

- [Task fixtures](tasks/), including protected source, reference/negative proofs, metadata, and structural maps.
- [Verifier runner](run_verification.py), [model runner](run_pilot.py), [prompt/edit policy](pilot_support.py), [offline tests](test_support.py), and [Slurm script](pilot.sbatch).

From the repository root, run `python experiments/composition-pilot-001/test_support.py`. Run verifier checks in the documented Cannon/Dafny environment with `python experiments/composition-pilot-001/run_verification.py --output outputs/composition-check-new`. Use a new output directory. The original model staging expects `verification-001` beside the source and the existing credential loader at `experiments/repair-003/runner.py`.

Model credentials are loaded from the private handoff, which is deleted immediately; the runner clears its environment at completion. No credential is archived. API prompts contain the broken client and providers only, never reference or negative-control proofs.

## Interpretation and planned follow-up

These tasks require chaining specified facts, but names are descriptive, proofs are short, and the call-only edit policy narrows the solution space. Success here is evidence of basic compositional proof completion, not arbitrary repository reasoning. Two repetitions per task are sparse; tasks, not requests, are the unit of generalization. A ceiling result cannot establish that maps never help.

If both conditions succeed, increase difficulty through longer chains, plausible distractor contracts, and argument transformations, while keeping all information available. Then use matched repository size/specification controls to separate dependency structure from code length. If failures appear, diagnose wrong arguments, missing intermediate facts, and unsatisfied preconditions separately before scaling.
