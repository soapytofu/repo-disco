# context-pilot-001: exported-lemma context in a two-module proof repair

**Status, October 21, 2026:** built and verified on Cannon (job 54502422). All 12 control checks matched expectations; seven offline policy/prompt tests passed. The eight-call pilot is prepared but awaiting the private credential handoff. No model calls have been made for this experiment. [Control log](VERIFICATION.md) · [Raw results](verification-001/results.json).

## Research question and scope

Does supplying the imported module's exported lemma signature and contract help a model repair a missing client proof? This is a **single deliberately constructed API-context fixture**, not a repository benchmark or evidence of performance across unrelated problems.

`MagnitudeFacts` exports an opaque `Magnitude(x)` function without a postcondition, and a lemma `EstablishLowerBound(x)` establishing `Magnitude(x) >= 0`. The client must prove that property. Exporting with `provides` hides the function body from the importing module; the client's proof uses the lemma instead. This follows [Dafny's export/opacity rules](https://dafny.org/dafny/DafnyRef/DafnyRef).

The reference and broken cases are assistant-authored. The model never receives the reference client or provider implementation. It may guess the lemma name in the local-only condition; the experiment does not assume that condition is impossible for a model.

## Preregistered pilot design

- Eight single-request calls: four repetitions per condition, one model and one task.
- `local_only`: broken Client.dfy, its target contract, common edit instructions, and original whole-repository verifier feedback. The referenced function name is visible, but the provider API inventory is not.
- `api_context`: exactly the same content plus a dependency-map sentence and exported function/lemma signatures and contracts.
- Same system prompt and candidate guard in both conditions. The appendix is the only prompt difference, tested offline. Input lengths are not matched; information availability and prompt length are not separately controlled.
- Alternating paired order: local/API, API/local, local/API, API/local. No random seed or randomization.
- Claude Sonnet 4.6 via Bedrock (`us.anthropic.claude-sonnet-4-6`, `us-east-1`), provider-default temperature, 4,096 output tokens per call, SDK total attempts 1. No automatic retries or learning from earlier trials.
- Whole-repository verification with `--verify-included-files` and a 60-second process timeout. A timeout or provider error stops the batch for investigation.
- No early stopping on a successful repair: both conditions receive their planned four samples, up to the eight-call total cap.

This specification and the task were prepared before model calls. The executed runner snapshot, protocol, and full prompts are archived with the run.

## Frozen proof/edit boundary

The provider source is immutable. The complete client response must retain exact bytes outside the proof body, after stripping outer whitespace and ensuring one final newline. Within the body, a shared allowlist accepts calls `F.Identifier(x);` and `assert F.Magnitude(x) >= 0;`, with whitespace. Unknown helper names are allowed by the guard and are left to Dafny to resolve. Empty proofs are also allowed for the verifier to judge. No assumptions, contract changes, new declarations, comments, or attributes are accepted.

This narrow fixture grammar protects the obligation and keeps edit policy equal across conditions. It is not a general-purpose Dafny edit validator. Failed guards are reported separately from failures that reach Dafny. A verified candidate is also reviewed for preservation before interpretation.

## Verifier-only controls

| Variant | Provider only | Client only | Whole repository |
| --- | --- | --- | --- |
| Reference with helper call | Pass | Pass | Pass |
| Missing proof | Pass | Fail | Fail |
| Assert desired result without helper | Pass | Fail | Fail |
| Reference client with unproved provider lemma | Fail | Pass | Fail |

These controls check that the helper call closes the client obligation, simply restating the desired result does not, and imported-but-unproved contracts cannot count as repository completion. The last control again demonstrates why whole-repository verification matters.

## Reproduction and evidence

- `fixtures/`: source cases; `repository-manifest.json`: module map, exports, variables, policy, and limitations.
- `run_verification.py`: verifier-only checks; new output directory required.
- `pilot_support.py`: frozen prompt construction and protected-body guard.
- `test_support.py`: seven offline tests including guard protection and exact prompt-difference checks.
- `run_pilot.py`: bounded noninteractive experiment. It records a dispatch before sending the request, refuses an existing output directory, and never retries an ambiguous request automatically.

Run offline checks with `python experiments/context-pilot-001/test_support.py`. Run fixture verification on a compute node with `python experiments/context-pilot-001/run_verification.py --output outputs/context-check-new` in the documented Dafny environment. The model runner expects the reviewed `verification-001` beside its staged source, and repository-root helpers from `experiments/repair-003/runner.py`; do not treat an archived completed run as a new-run configuration.

The credential handoff is deleted at model-run startup; it remains only in the process environment until completion. Credentials are never archived. Failed trials, exact prompts/responses, tokens, protected source hashes, verifier commands, and stdout/stderr are retained.

## Interpretation limits and next work

Any success difference here is about receiving a helpful exported-lemma API in a constrained setting. It does not disentangle information availability from reasoning ability, does not establish a causal role for context length, and does not generalize from one fixture to deeper repository structures. Four repeated requests are not four independent problems. Neither condition can browse the repository or request additional context.

Follow this with several independently designed tasks, distractor APIs and multiple candidate lemmas, a context-retrieval condition, and matched size/specification controls. Only then begin varying dependency depth or shared proof requirements. This is an intermediate step in the proposal's Weeks 3–4 context/verification infrastructure milestone.
