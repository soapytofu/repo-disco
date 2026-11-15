# Fixed-target migration seed validation

The two fresh seed checks matched their expected ordinary proof failures in
job **60865223**, completed on nonpreemptible `test` in **30 seconds**. Both
`Helper.Transfer` and `Client.Target` have actual failed correctness units in
each workspace. No model calls were made.

| Fresh seed | Helper | Client | Other observations |
| --- | --- | --- | --- |
| Relative-advance return contract | Postcondition failure | Call-precondition and public-postcondition failures | Five diagnostic errors; total arithmetic Endpoint is source-bound but unlogged |
| Extracted-entry return contract | Postcondition failure | Call-precondition and public-postcondition failures | Three diagnostic errors; all three map-provider well-formedness units pass |

Both verifier processes exited 4 with zero warnings, frontend errors or
timeouts. Failure counts are diagnostics, not independent tasks. The old helper
and caller bodies remain byte-exact under the selected new helper contract;
public contracts, kernel definitions and imports are unchanged. The old bodies
may retain their original runtime behavior. This study concerns satisfying an
explicit API migration, not discovering a new public runtime defect.

[Full sources and raw evidence](fixtures-and-controls/verification-001/),
[accounting](fixtures-and-controls/accounting-60865223.txt),
[scheduler stdout](fixtures-and-controls/verify-60865223.log) and
[scheduler stderr](fixtures-and-controls/verify-60865223.err) are preserved.
The 126-file transfer includes the exact runtime and fixture snapshots, raw
stdout/stderr/CSV and tool-version evidence. Dafny 4.11.0 and Z3 4.12.1 match
the frozen versions. There was one submission and one verifier attempt per seed.

The [repeatable offline review](review_seed_evidence.py) and
[source-bound gate](reviews/seed-review-001/stdout.json) check the transfer,
environment, exact source bytes, full guard receipt, raw/base64/log hashes and
named verification units. A separate read-only review confirms both outcomes.
The scorer correctly reports both as failed workspaces; successful validation
of these negative controls is not successful model repair.

Eight controls reuse exact observations from job 60723362: paired and alternative
repairs pass, helper-only repairs leave the client failing, and client-only
repairs leave the helper failing. The gate replays those eight against the new
fixed-contract candidate policy without running Dafny again. Thus this study
contains **two new verifier observations plus eight reused observations**.
The parent's old-header `caller_only` controls remain ineligible candidates.

These observations establish that the selected one-sided changes are
insufficient. They do not prove every solution needs two edited files or calls
to `H.Transfer`; direct implementations using transparent kernel functions
remain eligible. All earlier experiment sources and model scores are unchanged.

The next offline step is a four-payload prompt freeze for the proposed 16-response
comparison: two development tasks, two feedback conditions, four fresh responses
per cell. It has no model result, iterative agent loop or paid execution
authorization. The previous paid session remains terminal.
