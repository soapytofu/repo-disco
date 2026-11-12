# Certificate-order analyst diagnostic

November 12, 2026. **All four expected outcomes confirmed** on job 60066865,
nonpreemptible test, in 24 seconds. Three analyst repairs strictly verify
20 obligations each with zero errors/warnings; the unchanged unadmitted response
fails the expected certificate precondition. Four offline tests pass locally and
on Cannon. Zero model calls. [Full results and logs](RESULTS.md).
The [original partial pilot](../map-development-pilot-001/RESULTS.md) is preserved.

The earlier connection failure is retained in `connection-blocker-001.json`.
After reconnection, `reconnection-state-001.json` confirmed no prior remote
preflight, output, submission or matching job before proceeding once.

The completed model responses exposed a specific ordering issue: call the
disjointness certificate for restricted maps before the facts showing their
restricted domains. This diagnostic tests whether moving that existing call
after the two `RestrictKeys` calls suffices. No statement, contract, function,
import, helper signature or provider/client source is added or removed.

| Case | Actual compiled source | Expected outcome |
| --- | --- | --- |
| Response 08, separate | Move the one certificate call in each body | Strict success |
| Response 09, shared | Move the certificate call | Strict success |
| Response 04, originally policy-rejected | Original body, unchanged | Precondition failure |
| Response 04, analyst reordered | Move the certificate call; keep both ensures clauses | Strict success |

Response 04 has two `ensures` clauses in a forall proof block; the frozen model
guard allows one. For this **trusted analyst check only**, a syntax-review
projection joins those two explicit clauses by conjunction and checks all other
tokens with the unchanged bounded grammar. The actual Dafny input keeps both
original clauses byte-for-byte. This is not a general new parser, automatic
candidate admission or a change to its original rejection. Both response-04
sources still fail the original model guard, as the offline test confirms.

Original admitted responses 08/09 already have proof-failure evidence, so they
are not rerun unchanged. Their analyst versions, the exact unadmitted response 04,
and its reordered version are the four distinct checks. `prepare.py` binds
response/seed bytes and permits only moving the identified existing line.
The tests compare statement multisets, protected source, original rejection,
exact process staging and CSV capture, plus all pinned runtime inputs.

`manifest.json` freezes source/runtime; `ops.py` uses an exclusive staging and
submission record, live nonpreemptible test and no retries/requeue. All actual
Dafny checks must run on compute nodes. `review.py` checks exact diagnostic
categories, source hashes and preservation of every original model-archive file.
Unexpected results are retained before any deliberate correction.

The verified reorder establishes sufficiency of that analyst edit on these three
saved responses, not minimality, model improvement, necessary proof depth or a
general causal sharing effect. The original model scores remain unchanged.
