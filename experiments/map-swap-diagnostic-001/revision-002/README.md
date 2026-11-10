# Corrected negative-control binder

This deliberate verifier-only revision changes the false assertion's binder from
reserved Dafny keyword `fresh` to `badKey0`. The previous control's parse error
and complete job 59527654 archive remain unchanged in the parent directory.

Only one control will run. It should now fail proof checking on
`assert forall badKey0 :: badKey0 == 0;`, rather than fail parsing. No parser,
client, contract, provider or other body text changes. The five successful
diagnostic outcomes from the prior run are reused without rerunning them.

Three offline methods check exact edits, unchanged policies/protected bytes,
guard reconstruction, fake verifier behavior and isolated submission scope.
No model calls or real verifier invocations occur in these tests. Compute
results are pending. This does not change the original pilot score of 27/32.
