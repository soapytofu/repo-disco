# Completed: 18/24 strict whole-repository successes

Job **57162314** completed on nonpreemptible `test` in **4m39s**, November 3,
2026 UTC (November 2 Eastern). All **24 approved requests** returned with unique
request IDs and **zero SDK retries**. No model budget remains in this pilot.

| Original outcome | Count |
|---|---:|
| Strict whole-repository verification, protected contracts preserved | **18/24** |
| Body-output guard rejection; never sent to Dafny | **5/24** |
| Admitted proof that failed an assertion | **1/24** |
| Truncation, frontend, timeout or transport/infrastructure failure | **0** |

Denominators: 24 planned, 24 reserved, 24 dispatches begun, 24 returned, 19 guard
admitted, 19 verifier invocations, 18 strict successes. The conditional 18/19
among admitted outputs does not replace the primary 18/24 score. All 24 responses
have the requested JSON filename-to-string shape; the five rejections occurred
inside the bounded body language. No response was repaired or rescored.

| Task | Shallow shared | Shallow separate | Deep shared | Deep separate | Strict total |
|---|---|---|---|---|---:|
| Nested clamp | V | V | V | V | 4/4 |
| Clamp stability | V | V | V | V | 4/4 |
| Reverse concatenation | G | G | V | V | 2/4 |
| Nested filtering | V | V | V | V | 4/4 |
| Commuting updates | G | V | P | G | 1/4 |
| Delete after update | G | V | V | V | 3/4 |
| **Total** | **3/6** | **5/6** | **5/6** | **5/6** | **18/24** |

V = verified; G = guard rejection with unknown Dafny outcome; P = proof failure.
Conditional: **8/8**; sequence: **6/8**; maps: **4/8**. These are two distinct
semantic instances per family, each visited in four configurations, not eight
independent problems or repeated samples of one configuration.

## What failed

| Trial | Observed cause | Interpretation |
|---|---|---|
| [02](model-001/reasoning-cal-02/response.json), [18](model-001/reasoning-cal-18/response.json) | Local identifier `s'` contains an apostrophe outside the frozen guard's identifier alphabet | Output-policy mismatch. The prompt did not explicitly spell out the allowed identifier alphabet. Neither response was semantically checked. |
| [08](model-001/reasoning-cal-08/response.json) | Assertions use `{k}` and `{j}` set literals | The prompt explicitly excludes set literals. No Dafny result for this response. |
| [21](model-001/reasoning-cal-21/response.json) | Map updates and map comprehensions | Both constructs were explicitly excluded from returned bodies, although visible provider code contains them. No Dafny result. |
| [24](model-001/reasoning-cal-24/response.json) | Map updates such as `m[k := x]` | Explicitly excluded output syntax. No Dafny result. |
| [03](model-001/reasoning-cal-03/verification.json) | `assert rhs[q] == y` fails in the `q == j` branch | Actual assertion failure, exit 4: 15 verified, one error. |

For trial 03, code inspection suggests a missing inner-update fact. The outer
update observation relates `rhs[q]` to `K.Put(m,j,y)[q]`, but this branch does not
call `O2.PutAt(m,j,y,q)` to expose that value. This is a diagnosis from the saved
code/contracts, **not a verified repair**. Trial 08 appears to have the same
omission after its rejected set expressions, but its semantic outcome is unknown.
All original responses and diagnostics are retained unchanged.

## What the successful proofs show

The conditional cases remain at ceiling. Shallow clamp proofs consist of two or
three API observations; deep proofs assemble lower/upper facts before the solver
finishes the relation. The richer semantics did not remove the ceiling for these
two sampled instances. Nested filtering also reached 4/4 using explicit recursion
and branch reasoning. The accepted reverse proofs use recursive decomposition
and concatenation reassociation. Successful map proofs assemble domain/value
facts and use pointwise proof blocks with extensionality.

All **12 separate responses contain identical body strings in HelperA and
HelperB**, including the two rejected responses. All ten admitted separate
responses also match under the guard's syntax representation. Copying was allowed
by design; these results do not demonstrate independent proof synthesis for each
client. Shared primitive definitions remain present in both conditions.

Shared totals are 8/12 and separate 10/12; shallow 8/12 and deep 10/12. The larger
numbers are descriptive only: syntax rejections differ across cells, there is
one sample per variant, and output workload differs between sharing conditions.
No causal advantage, monotonic depth effect, held-out generalization or population
success rate follows from these counts. The five rejected outputs do not establish
five reasoning failures.

## Audit and evidence

The [reproducible audit](results-review.json) verifies exact request payloads and
order, frozen/runtime/source hashes, authorization deadline, unique IDs, zero SDK
retries, raw-response copies, guard decisions, candidate bytes, whole-repository
verifier commands and accepted records. The [manual review](manual-review.json)
records inspection of all 18 accepted proof bodies and all six other outcomes.
Protected sources/contracts were unchanged for all 19 admitted candidates.
The valid `assert false` in one filter proof is inside a contradictory branch
under the fixed threshold precondition; it remains a checked assertion, not an
assumption or bypass.

- [Every trial with raw-response and diagnostic links](TRIALS.md)
- [Full run archive](model-001), [request ledger](model-001/requests/ledger.json), [environment](model-001/environment.json)
- [Runner stdout](model-57162314.log), [stderr](model-57162314.err), [Slurm accounting](accounting-57162314.txt)
- [Archive file hashes](model-001-sha256.json), [transfer inventory](transfer-001.json), [submission evidence](submission.json)

Usage: **73,528 input + 10,249 output = 83,777 tokens**; reported cache read/write
tokens are zero. No dollar cost was captured. The model and inference settings
are unchanged from the frozen proposal. No new model or Dafny runs were made for
the offline audit; the only new semantic results here are the original 19 candidate
verifications in this pilot.

## Next gate before larger collection

Keep the larger corpus deferred. First separate output-language coverage from
proof ability: a future, explicitly labeled verifier-only diagnostic can check
the five saved rejected bodies without changing this score, and test the proposed
single-step repair for trial 03. A later protocol should either support the
needed pure syntax with protected-boundary tests or explicitly teach the exact
accepted identifier/expression forms. Any change needs a separate version and
freeze, not modification of this run.

Reconsider the two conditional instances and nested filtering before scale-up:
their four-cell ceilings persist. Additional difficulty and sampling decisions
should use these per-task observations, not the aggregate 18/24 figure. No new
model calls, protocol revision or main-corpus collection is authorized by this
completed batch.
