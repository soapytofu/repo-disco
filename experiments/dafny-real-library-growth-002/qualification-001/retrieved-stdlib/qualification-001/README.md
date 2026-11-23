# Four-reference native qualification

This verifier-only package initially dispatches exactly four analyst references:
`filter-reference` and `splice-reference` for the Dafny standard library;
`counted-reference` and `tagged-reference` for the AWS UInt-derived framing
scope. Each project has one job containing two serial reference invocations.
No baseline rerun, negative control, alternative, model call or credential flow
is dispatchable here. New native outcomes and labels remain unknown until the
submitted evidence is reviewed.

The standard-library profile retains Dafny 4.11.0, one core, resource limit
1,000,000, a 300-second verifier limit and 360-second outer cap. AWS retains
Dafny 4.9.1, the previously qualified Z3 4.12.1 manylinux binary, resource limit
500,000,000, a 300-second verifier limit and 900-second outer cap. All prior
tool fingerprints and flags are copied exactly in `tool-profiles.json`.
Each Slurm job requests one CPU, 4 GB and one hour on live-confirmed UP,
nonpreemptible `test`, with no requeue or automatic retry.

`collect.py` checks the exact runtime, reference source hashes, full explicit
file argv and tool fingerprints. It retains original workspaces, raw CSV,
stdout/stderr, GNU time resources and before/after identities. Source or tool
drift fails closed after evidence retention; an outer timeout or process
failure stops the remaining reference. Ordinary native proof failures are
retained as observations and do not trigger repairs or retries.
Verifier and version-check subprocesses exclude every `AWS_*` variable plus
`BOTO_CONFIG`, `BOTO_PATH` and `BEDROCK_API_KEY`; their values are never read or
printed by the filter. Slurm, executable-path and other ordinary settings remain.

`ops.py` supports bounded inspect, stage, synthetic preflight, submit, status
and final archive operations. It uses only authenticated socket 21. Every
remote program travels through `python -B -` on stdin, including base64 stage
bytes, so inventories never become giant shell arguments. Stage, submission
and archive intents are exclusive locally and remotely. Final archiving
requires the exact parent and every returned relevant Slurm step to be
terminal, no matching queued job, and an unchanged inventory between estimate
and transfer. The full tarball is retained before safe extraction and replay.

The primary `review.py` checks the transfer inventory and exact native
source/raw/tool/command identities. It uses the unchanged common scorer's CSV
parser and resource decoder, retaining every actual row. Previously observed
inherited labels are required: 56 for the standard-library base, 58 when
accepted `AppendAll` is present, and 77 for the accepted AWS frame-pair scope.
New target labels are never guessed. Success is reported only as
`NATIVE_SUCCESS_INVENTORY_PENDING`; no qualified profile or acceptance is
issued. Root must inspect new units and all unlogged declarations before
creating a final profile. Inherited declarations whose full source file changed
are explicitly marked for review, even when the declaration itself is unchanged.

The 24 offline tests use synthetic sources, intercepted cluster processes and
small Python child processes. They make no SSH, scheduler, provider or native
verifier calls. Full logs are under `reviews/offline-001/` and the final
environment-isolation run under `reviews/offline-002/`.

After root reviews and freezes each exact project bundle, root may use:

```sh
python3 -B qualification-001/ops.py inspect PROJECT
python3 -B qualification-001/ops.py stage PROJECT
python3 -B qualification-001/ops.py preflight PROJECT
python3 -B qualification-001/ops.py submit PROJECT
python3 -B qualification-001/ops.py status PROJECT
python3 -B qualification-001/ops.py fetch PROJECT
python3 -B qualification-001/review.py PROJECT --output qualification-001/reviews/native-PROJECT-001.json
```

Run these from the experiment directory; `PROJECT` is `stdlib` or `aws`.
No project freeze is implied by this README. Local and Cannon synthetic
preflights precede each single submission. Any unexpected native result is
preserved before considering a separate, deliberate revision.
