# Replacement splice controls

Verifier-only job `63185390` completed in 22 seconds on one nonpreemptible
`test` CPU. Both new controls match their predeclared outcomes at the unchanged
1,000,000 resource limit. No model requests were made.

| New control | Actual named correctness outcomes | Native total |
| --- | --- | --- |
| Retain old content before appending the requested splice | Splice fails its exact-content postcondition; AppendAll passes | 59 verified, 1 error |
| Verified rebuild caller with the old return-only helper mutant | AppendAll fails its postcondition; Splice passes under its declared contract | 59 verified, 1 error |

Both outcomes are ordinary proof failures with zero warnings, frontend errors,
resource failures or missing units. The second case demonstrates why a passing
caller cannot qualify a workspace containing an unproved helper. The ordinary
model edit guard separately rejects this mutation of a protected helper.

The full 320-file transfer contains the pinned input package, both actual source
workspaces, CSV, stdout/stderr, resource records and terminal accounting. Exact
replay is recorded in `reviews/native-stdlib-001.json`.

These are two new analyst observations. The two earlier shifting-based controls
remain recorded as resource failures in qualification-002; they were neither
retried nor rescored. The intended current qualification set combines four
selected reference observations, 24 unchanged matching qualification-002
controls and these two replacements. Model difficulty remains unmeasured for
this new cohort.
