# Evaluation stability results

Completed November 17, 2026 (Eastern), with **zero new model calls**. The exact
saved Dafny swap candidate verifies the entire qualified scope at the larger
predeclared resource budget. A separate warning policy distinguishes complete
proofs from the exact observed Cargo cleanup warning. Historical scores and
archives remain unchanged.

## Full-scope resource comparison

Job **61661285** ran all four frozen cells once on the same nonpreemptible `test`
node, `holy8a26602`, with one CPU, 2 GB and no requeue. Each native invocation had
a 300-second wall cap. Both sources used the same pinned toolchain, 28 explicit
source inputs and 267 required named verification units. Only the `Swap` body
differs; no analyst repair was applied to the saved model candidate.

| Order | Source | CLI resource limit | Required units passed | Outcome | Native seconds |
| --- | --- | ---: | ---: | --- | ---: |
| 1 | Exact upstream | 20,000 | 267/267 | Qualified pass | 34.11 |
| 2 | Exact saved candidate | 20,000 | 265/267 | Two downstream resource failures | 30.60 |
| 3 | Exact saved candidate | 100,000 | 267/267 | Qualified pass | 31.93 |
| 4 | Exact upstream | 100,000 | 267/267 | Qualified pass | 33.06 |

All four runs retain exactly the three upstream trigger warnings. Thus the
passes are qualified full-scope passes, not zero-warning passes. There were no
frontend failures, wall timeouts or missing required units. The lower-budget
candidate has exit 4 and explicit `out of resource` diagnostics; the other three
commands exit 0. Job completion alone was not used as a proof-success signal.

The saved candidate implements the transparent function body as:

```dafny
s[i := s[j]][j := s[i]]
```

Its own `Swap` well-formedness obligation passes at both budgets. The unchanged
downstream lemmas use `Model.Swap` in their specifications and encounter resource
exhaustion only in the candidate's lower-budget cell.

| Named unit | Upstream, 20k and 100k | Candidate, 20k | Candidate, 100k |
| --- | ---: | ---: | ---: |
| `Model.Swap (well-formedness)` | 203,302, passed | 49,213, passed | 49,213, passed |
| `Correctness.InductionHypothesisPrecondition1 (correctness)` | 2,330,467, passed | 20,027,381, exhausted | 36,062,505, passed |
| `Correctness.ProbabilityOfE (correctness)` | 18,267,257, passed | 20,084,634, exhausted | 21,164,157, passed |

These are the verifier CSV's reported resource counts, distinct from the CLI
limit values in the first table. Exhausted counts are censored observations,
not estimates of completed proof cost. At the passing 100k setting, the candidate
uses about **15.5 times** the upstream resource count for the induction lemma,
while using fewer resources for its own well-formedness check. This is a concrete
example of a local implementation affecting downstream verification cost under
unchanged declared contracts. The passing larger-budget check establishes proof
completion for this candidate in the qualified scope; the original resource
failure does not establish mathematical incorrectness.

The four cells were predeclared controls, not adaptive retries. There is one
observation per cell, one candidate and one pinned toolchain. These results do
not establish a minimal sufficient budget, broad robustness, a general effect
of repository depth or sharing, or model performance on unseen tasks. The
candidate's lower-budget result is retained. The higher budget is not silently
adopted for future collections.

## Separate warning policy

The versioned reporting layer preserves the old acceptance field and separately
reports proof completion, operational warnings, unknown warnings and eligibility
under the new policy. Eleven warning tests plus six compute/fake-process tests
passed locally and in the staged Cannon environment; the tests made no provider
or native-verifier requests.

Replaying twelve existing native observations gives eight originally qualified
observations and ten complete-proof observations. Exactly two observations become
eligible under the separate policy:

- Original Vest pilot slot 13.
- Saved-output Vest diagnostic slot 07, whose exact candidate also represents
  saved slot 10. This is one native observation, not two independent checks.

Both contain the exact Cargo incremental-session cleanup warning with error 39.
The policy accepts that warning class only for a `vest_dev` session beneath the
single recorded `--target-dir`; it retains the complete text. Unknown warnings,
missing upstream warning blocks, other paths/errors, incomplete coverage and
unproved workspaces remain blocking. This change separates an operational cleanup
condition from proof completion; it does not repair the cleanup process itself.

These twelve observations are a policy replay on existing development evidence,
not a new model evaluation. The original pilot remains **7/16 qualified accepts**,
and every prior diagnostic retains its original classification. A future pilot
must explicitly freeze its warning and resource policy before collection. No
live repository revision was promoted by this analysis.

## Integrity, runtime and evidence

The source-bound review checks all four exact commands, source hashes before and
after verification, required named-unit coverage, raw log hashes, observations
and diagnostic-only acceptance records. All 40 frozen runtime files, 41 transferred
files and **867 parent archive files** match their recorded hashes. All four
records have one attempt and zero model calls.

The Slurm job took 161 seconds, used 122.436 CPU seconds (76.0% of its single-core
allocation) and reported peak batch RSS of 667,520 KiB. Individual native checks
used 93–94% CPU and about 514–518 MiB maximum RSS. Native time is reported separately
from job staging/verification overhead; the resource-limited check is not counted
as a correctness pass. This one-core allocation is sufficient for this serial
experiment. It makes no claim about Vest's allocation requirements.

- [Frozen design and scope](README.md), [plan](plan.json),
  [runtime manifest](runtime-freeze.json), and [submission](submissions/dafny-vmc.json).
- [Source-bound review](review-dafny-vmc-001.json) and
  [per-unit analysis](analysis-001.json), produced by [analyze.py](analyze.py).
- [Full native stdout/stderr, CSV and resource logs](verification-dafny-vmc-001/),
  [job stdout](dafny-vmc-61661285.log), [job stderr](dafny-vmc-61661285.err),
  [Slurm accounting](accounting-dafny-vmc.txt), and [transfer hashes](transfer-dafny-vmc.json).
- [Warning policy](warning_policy.py), [saved-observation replay](warning-replay-001.json),
  [local tests](local-preflight-001.json), [remote tests](remote-preflight-001.json),
  and [parent preservation inventory](preserve-parents.json).

The next collection needs a fresh, explicitly frozen evaluation policy. It can
report proof completion, resource exhaustion, frontend failures and operational
warnings separately, while retaining fixed source-integrity and coverage gates.
No further model or verifier job is submitted by this report.
