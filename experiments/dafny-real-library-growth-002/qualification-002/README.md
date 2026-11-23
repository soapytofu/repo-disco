# Fixed remaining-control qualification

The source-bound reference gate has four reviewed strict zero-warning
successes: stable filter (59 units), the existing alternative splice algorithm
(60), AWS counted frames (81), and AWS tagged bounded pair (79). Their complete
source/record/raw/profile evidence is replayed before any operation. Reuse of
these observations is not another native trial.

This dispatcher runs only 14 Stdlib controls and 12 AWS controls. The complete
fixture catalog still has 31 entries. The active gate has 30: four selected
references plus 26 new controls, with five intended successes, 21 intended
proof failures and four native-success coverage omissions. The shifting
splice-reference is separately excluded after qualification-005 hit the fixed
1,000,000 resource limit. Its original PROOF_PASS expectation and actual
RESOURCE_FAILURE, source and raw evidence are preserved. No selected reference
or excluded shifting implementation can be dispatched here.

`control-selection-002.json` binds that selection to the actual reference gate.
The earlier prequalification selection and unfrozen draft remain in
`control-selection-001.json` and `selection-history-001/`; the earlier warning
gate implementation remains in `review-history-001/`. All new Stdlib controls
project exact revision-004 source hashes; AWS sources remain unchanged.

The inherited toolchains, flags and per-invocation caps are unchanged. Serial
jobs use one CPU and 4 GB, fixed two-hour Stdlib and four-hour AWS Slurm limits,
a live-confirmed UP/nonpreemptible test partition and no requeue or retries.
The native outer caps remain 360 and 900 seconds respectively. An outer timeout
or terminated process preserves its record and stops the remaining job cases.

Omissions use only exact predeclared command subsets. Helper-mutated cases are
analyst trust controls, ineligible for model acceptance. Positive expectations
require strict zero-warning success. Proof-failure expectations require the
actual named failures, complete inventory, zero warnings and matching warning
policy. Frontend, warning and resource failures cannot satisfy a proof-failure
expectation. A passing client cannot hide an unproved helper; missing units do
not count as whole-workspace success. Unlogged definitions remain source-bound
and are never counted as logged passes.

Bounded stdin transport, exclusive local/remote intents, all-step terminal
accounting, exact inventory replay and safe archival are retained. Every source,
command, tool fingerprint, native CSV/stdout/stderr, resource and accounting file
is preserved. There is no provider, model or credential operation. Synthetic
process tests never invoke SSH, Slurm or Dafny; the native-reference replay tests
only read already captured evidence. No new native outcomes are claimed here.

Root operates from the experiment directory, separately for stdlib and aws:

```sh
python3 -B qualification-002/ops.py inspect stdlib
python3 -B qualification-002/ops.py stage stdlib
python3 -B qualification-002/ops.py preflight stdlib
python3 -B qualification-002/ops.py submit stdlib
python3 -B qualification-002/ops.py status stdlib
python3 -B qualification-002/ops.py fetch stdlib
python3 -B qualification-002/review.py stdlib --output qualification-002/reviews/native-stdlib-001.json
```
