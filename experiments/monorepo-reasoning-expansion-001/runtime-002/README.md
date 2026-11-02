# Runtime correction, unchanged proof fixtures

Initial job 57104220 failed at Python import before `main()` and before any Dafny
invocation. Its staged `language.dafny` package transitively imports `execute` and
`language.dafny.prompt`, but those two files were absent. See the original root
job logs and [correction record](correction.json).

This new directory preserves all 1,476 fixture files, tasks/check definitions,
builder, verifier wrapper and review script byte-for-byte. It adds the two
dependencies from the already published balanced-pilot runtime. Two tests verify
isolated import resolution and exact file staging with one **fake** verifier
process; both pass locally and in the real Cannon Python environment. These
offline tests execute neither Dafny nor any model request.

The new manifest pins all inputs. Job **57106124** is a deliberate corrected
runtime submission on shared, with no requeue or automatic retry, not a retry of
a model call or an already executed proof check. Output is `verification-001` in
this directory. The negative phase is still gated on reviewing all 48 first-phase
outcomes. No semantic results are claimed yet. Follow-up ends at 22:22:25 UTC on
November 2, without canceling any already submitted job.

## Reviewed result: 44/48 expected

Job 57106124 completed its 48 checks in 4m12s on holy7c04101 (shared), then exited
1 because four reference outcomes disagreed with their expectations. All four
reverse-concatenation references fail the final equality assertion; this is a
proof failure, not a parser or name-resolution failure. The other five instances
pass all four reference variants. All 24 empty-helper controls fail proof checks
as intended. No model calls, retries or timeout outcomes.

`verification-001-review.json` and `verification-001-sha256.json` audit the full
archived input bytes and diagnostic records. The runtime manifest also matches
its local source snapshot. The failed reference bodies remain unchanged here.
A deliberate next fixture revision will make the reverse proof's base case,
induction application and concatenation reassociation explicit; its correctness
will be assessed by a separate verifier run, not inferred from this diagnosis.
