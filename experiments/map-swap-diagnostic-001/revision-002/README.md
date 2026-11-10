# Corrected negative-control binder

This deliberate verifier-only revision changes the false assertion's binder from
reserved Dafny keyword `fresh` to `badKey0`. The previous control's parse error
and complete job 59527654 archive remain unchanged in the parent directory.

Only one control ran. It fails proof checking on
`assert forall badKey0 :: badKey0 == 0;`, rather than failing parsing. No parser,
client, contract, provider or other body text changes. The five successful
diagnostic outcomes from the prior run are reused without rerunning them.

Three offline methods check exact edits, unchanged policies/protected bytes,
guard reconstruction, fake verifier behavior and isolated submission scope.
No model calls or real verifier invocations occur in these tests. Compute
job **59528781** completed on nonpreemptible `test` in six seconds: exit 4,
13 verified obligations and one assertion error. It also reports one missing-
trigger warning, preserved separately from the assertion failure. This is not
a warning-only result or a strict pass. The [review](verification-001-review.json)
confirms exact source hashes and the expected proof-failure category. Full
evidence is in [verification-001](verification-001), with scheduler logs and
accounting alongside it. This does not change the original pilot score of 27/32.
