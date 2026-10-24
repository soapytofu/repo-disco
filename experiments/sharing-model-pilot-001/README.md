# Eight-call shared-versus-separate pilot: frozen preparation

**Completed: exactly eight Claude calls, no retries. Shared 0/4 accepted; separate 0/4 accepted.** Every response contained explanatory prose before the requested JSON object and was rejected by the frozen parser at the first character. **No model-generated candidate reached Dafny verification.** This is an output-format failure, not a mathematical proof failure or evidence of a shared-versus-separate reasoning difference.

[Trial table](TRIALS.md) · [Summary](model-summary.json) · [Raw responses, prompts and ledger](model-001/) · [Evidence review](model-review.json). Token usage: **5,208 input + 5,678 output = 10,886 total**. Job 54973122 completed on shared in 2 minutes 39 seconds. The eight-call budget is exhausted.

The original preparation protocol and frozen bundle remain unchanged. The later authorization is recorded in `authorization.json`. Review confirmed the exact frozen prompts/order, eight distinct provider request IDs, unchanged input snapshots, verbatim saved responses, and zero candidate/verifier outputs. The adapter logged each dispatch before its request and used one SDK attempt; it cannot restart the existing `model-001` directory. No acceptance rule was relaxed after observing results.

The earlier verifier-only preflight still establishes that the evaluator accepts reference JSON repairs and rejects empty proofs. It does not establish that a model will obey this output format. A possible next step is a separately labelled offline extraction diagnostic on these existing responses, or a revised output protocol validated before any newly authorized model batch. Neither has been performed as part of this run.

## Frozen design

Each independent request must return both complete client files in one JSON object. Both conditions receive the full provider and empty client source, identical system instructions, and no map, reference proof, prior responses, or verifier feedback. Protected imports select the permitted export view. Four repetitions per condition use one model configuration: `us.anthropic.claude-sonnet-4-6` on Bedrock us-east-1, provider-default temperature, maximum 4,096 output tokens. The proposed transport must use a single SDK attempt and no automatic retries.

| Sequence | Repetition | Condition |
| --- | --- | --- |
| 1 | 1 | shared |
| 2 | 1 | separate |
| 3 | 2 | separate |
| 4 | 2 | shared |
| 5 | 3 | shared |
| 6 | 3 | separate |
| 7 | 4 | separate |
| 8 | 4 | shared |

This is balanced alternating order, not randomization. Repeated requests are not independent task families. Each call starts with a fresh conversation. The only prompt-source difference between conditions is ClientB's export view. Provider source, client goals, instructions, and source byte counts match; model token counts have not been measured. Finish remains shared in both conditions.

`plan.json` fixes the order and exact prompt hashes. `protocol.json` fixes proposed settings, metrics and stopping rules. `frozen-bundle.json` hashes the fixtures, prompts, plan, protocol and evaluator used in preparation. Do not silently regenerate these after any model request. Record a new protocol revision and revalidate affected checks if a change is needed.

## Acceptance and logging

The primary outcome is both client files passing the edit guard and whole-repository verification. All dispatched requests belong in the denominator, including API errors; report transport failures separately. Record individual client outcomes as secondary diagnostics. Complete source, protected provider hashes, raw response, parsed files, verifier commands/stdout/stderr/exit/timing, and response token usage must be retained. Outcome categories are SUCCESS, EDIT_REJECTED, RESOLUTION_OR_PARSE_ERROR, PROOF_FAILURE, TIMEOUT, VERIFIER_ERROR, and (at future dispatch) API_ERROR.

The strict JSON parser rejects duplicate, missing, and extra file keys. It normalizes only outer whitespace and one trailing newline, then requires exact protected client bytes. Proof bodies permit qualified calls and restricted parameter expressions; unknown helper names are left for Dafny to reject. Assumptions, reveals, comments, assertions, contract edits, import changes, and arbitrary file writes are rejected. Provider and aggregate files are copied from frozen inputs. All.dfy verifies with included files first, then each client independently. A timeout or verifier infrastructure error stops remaining verification checks. Every evaluation requires a fresh output directory.

The live adapter is designed to check this frozen bundle and the compute preflight, enforce an explicitly authorized eight-request cap, write each dispatch to a durable ledger before sending, preserve ambiguous API outcomes without retrying, and stop the entire batch on an API error, timeout or verifier infrastructure error. Ordinary proof/format failures continue to the next independent planned trial. No repair loop, extra calls, early success stopping, or adaptive prompt edits are permitted. The authorization above permits one eight-call batch; it does not authorize retries or budget expansion.

## Offline use

From the repository root:

```sh
python3 experiments/sharing-model-pilot-001/test_harness.py
python3 experiments/sharing-model-pilot-001/pilot.py check
python3 experiments/sharing-model-pilot-001/pilot.py request 1
```

The last command prints the frozen request but sends nothing. On a Slurm compute node, an already-saved response can be evaluated with:

```sh
python experiments/sharing-model-pilot-001/pilot.py evaluate shared response.json --output outputs/new-offline-evaluation
```

`preflight.py` performs four deterministic response replays: authored reference and empty proof for each condition, each checked as a whole repository and per client (12 verifier checks). These are not model trials. The evaluator refuses verification on login nodes. Compute job **54969539 completed on shared in 47 seconds: all 12 checks matched expectations**, with requeue disabled. [Check table](PREFLIGHT.md) · [Raw logs and snapshots](preflight-001/) · [Review](validation-review.json). The snapshot matches the frozen evaluator, fixtures and prompts.

## Validation and limits

Nine offline tests cover both reference repairs, protected-byte changes, forbidden bodies, JSON schema errors, unknown-helper handling, prompt/order consistency, no verification after edit rejection, duplicate-output refusal, timeout stopping, and frozen-bundle tamper detection. The full task's earlier 46 verifier controls are archived under sharing-reasoning-001; this preflight additionally checks the exact new empty-proof inputs and JSON response path.

This pilot measures completion of a small designed proof pair under different shared-helper access, not a general reasoning benchmark or a causal advantage of sharing. Correct arguments and precondition failures can be reviewed from raw candidate bodies and diagnostics; the harness does not infer reasoning quality from call names alone. A ceiling result should motivate harder tasks, not more repetitions of the same easy proof.
