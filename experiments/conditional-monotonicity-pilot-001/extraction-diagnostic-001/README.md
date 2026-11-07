# Saved-response extraction diagnostic

The eight-call pilot returned seven responses with explanatory text surrounding one schema-matching JSON object. This diagnostic selects that unique object by exact character span and passes its body strings through the same pinned v4 guard. Each selected object is the only JSON object with exactly the expected editable filenames and string values. Proof statements and all surrounding source remain byte-identical to reconstruction from those saved strings.

Job 58524840 was submitted once to nonpreemptible test with no requeue, solely to verify these seven candidates. New model calls are zero. **All seven candidates verified**, each with 14 obligations verified, zero errors, zero warnings and exit zero. The job completed in 25 seconds. The primary pilot retains its frozen full-response parsing outcome of 1/8. [Diagnostic review](review.json) · [Complete compute archive](verification-001/) · [Stdout](verify-58524840.log) · [Stderr](verify-58524840.err)

The existing diagnostic verifier wrapper was reused with the case count and historical-score label updated. Source hashes, exact extracted spans and original response hashes are recorded. The code includes no provider client or key access.

[Extraction code](prepare.py) · [Exact cases](cases.json) · [Runtime manifest](manifest.json) · [Submission](submission.json)

The observed proof bodies use nested region branches for the ordered inputs and the exported observations. All four separate responses copy identical bodies into their two helpers. This supports treating the conditional instance as an easy development anchor. Future output handling should be validated for an unambiguous JSON envelope before another model budget is considered.
