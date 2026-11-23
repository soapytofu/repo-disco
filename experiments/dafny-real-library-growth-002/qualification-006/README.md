# Existing alternative splice qualification

This package dispatches exactly one new native observation: the already
constructed `splice-alternative` from `stdlib/revision-004/`. It snapshots and
rebuilds the sequence through the accepted `AppendAll` API. It is a different
analyst algorithm under the same fixed contract, not a retry of the shifting
implementation and not a model success.

`selection-001.json` preserves the original `splice-reference` expectation
(PROOF_PASS) and its actual qualification-005 RESOURCE_FAILURE. That source,
its evidence and the 31-entry complete fixture catalog remain unchanged. The
shifting implementation has no dispatch route here. The passing filter and
both AWS references are reused by exact source identity, never rerun.

Only the alternative source selected in the config is staged. The collector,
reviewer and bounded stdin/exclusive archive protocol are inherited from
qualification-005; origins and the exact adaptation diff are recorded. No
provider, model, key-handoff, retry or resource-escalation operation exists.

The resource policy is unchanged: Dafny 4.11.0, one core, resource limit
1,000,000, verifier time limit 300 seconds, outer cap 360 seconds. The one Slurm
job uses one CPU, 4 GB, one hour, live UP/nonpreemptible test and no requeue.
Native children exclude AWS_*, BOTO_CONFIG, BOTO_PATH and BEDROCK_API_KEY.

Complete source/tool hashes, CSV, stdout/stderr and resource evidence are
retained. The reviewer reports actual labels and diagnostic categories; it
never grants a qualified profile or accepts a model candidate. The alternative
becomes a selected solvability reference only after a genuine native pass and
complete source/inventory review.

Offline tests use fake processes and tiny Python subprocesses only, with
explicit rejection of AWS, passing-filter and resource-failed-reference
repeats. There is no Dafny, Slurm, SSH or model call in those tests.

Root operates from the experiment directory:

```sh
python3 -B qualification-006/ops.py inspect stdlib
python3 -B qualification-006/ops.py stage stdlib
python3 -B qualification-006/ops.py preflight stdlib
python3 -B qualification-006/ops.py submit stdlib
python3 -B qualification-006/ops.py status stdlib
python3 -B qualification-006/ops.py fetch stdlib
python3 -B qualification-006/review.py stdlib --output qualification-006/reviews/native-stdlib-001.json
```
