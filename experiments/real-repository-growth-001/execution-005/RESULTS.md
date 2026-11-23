# Bounded resource-outcome runner preparation

Subsequent authorized collection: [job 63033780 is running](COLLECTION.md).
The preparation record below describes the earlier offline checkpoint.

Prepared November 23, 2026. **No additional model or native verifier calls**
were made to construct or qualify execution-005. This is host-policy preparation,
not a model repair or additional mathematical verification result. The first
returned growth candidate and its original terminal run remain preserved in
[execution-004](../execution-004/COLLECTION.md).

## Change and evidence

The new runner contains only fully evidenced Dafny solver-resource failures:
record an unaccepted stage, block its child, then continue independent lineages.
All 268 units and the named resource diagnostic in the saved failure agree under
the new audit. The [retrospective replay](reviews/resource-replay-001.json) retains
`qualified_pass=false`, does not issue a parent, does not change the original
native classification, and makes no verifier/model call.

The model prompts, source protections, proof acceptance, actual-parent checks,
resource limits, request gate, credential lifetime, SDK one-attempt setting and
full-evidence reviewer stay fixed. Provider uncertainty, incomplete evidence,
process timeouts, signals, unknown diagnostics, frontend or integrity failures
still stop future dispatch. The changed policy never turns resource exhaustion
into a proof pass or a mathematical counterexample.

| Qualification | Result | Full evidence |
| --- | --- | --- |
| Focused policy tests | 12/12 passed | [Transcript](reviews/draft-001/resource-tests.stderr) |
| Final manifest-only isolated package | 100/100 core tests plus 12/12 resource-policy tests, 155.85 seconds | [Driver output](reviews/draft-003/preflight.stdout), [core log](reviews/draft-003/evidence/unit-tests.log), [resource log](reviews/draft-003/evidence/resource-tests.log) |
| Installed SDK locally | Not installed; explicitly skipped | [SDK record](reviews/draft-003/evidence/sdk-imports.json) |
| Cannon qualification | 100/100 core tests, 12/12 resource-policy tests, and 5/5 intercepted-SDK scenarios; 737.20 seconds | [Full record](remote-preflight-001.json), [core log](reviews/cannon-preflight-001/unit-tests.log), [resource log](reviews/cannon-preflight-001/resource-tests.log), [SDK transcript](reviews/cannon-preflight-001/sdk-auth-regression.json) |
| Prior execution-004 frozen inputs | All 4,170 unchanged | [Root review](preparation-review-001.json) |
| Current package | 4,189 repository files, 214,602,266 bytes | [Runtime manifest](runtime-freeze.json) |

The final runtime SHA is
`5c007d3a1b77a7ff413e9b79a68e1485f18915534fcf05459cf760869ce94d7b`.
It pins the new policy and its tests, all original acceptance/prompt dependencies,
and 15 exact old evidence files used only for offline regression. Saved model
bodies and analyst counterexamples never enter a new prompt. Passed extractions
remain byte-identical to the inherited parent-integration path.

The synthetic dispatch test exercises a resource failure at the first Dafny
slot, no accepted parent for that lineage, its child undispatched, seven total
simulated requests and the other three lineages completing. The unchanged
saved-evidence reviewer replays that synthetic collection. This is an accounting
and containment test, not seven real model outcomes.

## Preparation history

The first isolated invocation rejected macOS's `/tmp` symlink before tests ran;
its [stderr](reviews/draft-001/preflight.stderr) is saved. The next invocation
used canonical `/private/tmp` and found one logging regression among 100 tests:
a skipped resource-suite message was appended to the preserved timeout log.
The [failed run](reviews/draft-002/evidence/unit-tests.log) and its
[pre-correction source](reviews/draft-002/preflight-before-correction.py) remain.
The correction keeps the original unit log exact and stores the skip reason
separately. The final isolated suite passes on the exact current source pins.
No paid request, native invocation or live run was retried during preparation.

The original 600-second core-test bound is unchanged. The added suite has its
own 180-second bound; either failure fails preflight. The outer remote driver
retains a 900-second process-group bound. These offline bounds are separate from
unchanged native/provider limits.

The exact package is staged once on Cannon. The [final root review](preparation-review-001.json)
confirms complete local/remote source agreement, all 22 copy origins, unchanged
prior runtime pins, and both test suites passing within their original bounds.
Cannon used Python 3.11.17 and boto3/botocore 1.43.115. No live key was read,
no provider socket connection was attempted, and no Slurm job was submitted.

## Next collection and reporting

Sophie authorized up to 100 new calls, with confirmation before exceeding that
ceiling. The [current budget](../research-budget-20261123-002.json) records one
used request in a closed eight-slot allocation, leaving 92 calls unallocated.
A new cohort can allocate at most eight from that remainder. It is a new frozen
collection under the changed stopping policy, not recovery of the seven unused
slots. No new execution authorization or submission exists at this preparation
checkpoint. A private handoff is required because the last job consumed it.

Report every attempted stage and blocked child. Give this cohort's complete
four-lineage metric only if collection is fully accounted for. Retain the earlier
incorrect response in the results table and any descriptive accounting of all
observed growth outputs; do not erase it when presenting the fresh cohort. Mixed
stopping policies are not a causal comparison. Reassess task/context or agent
design from the actual failures; do not keep sampling for a favorable headline.
