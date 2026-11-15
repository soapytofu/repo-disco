# Intersection certificate verifier runtime 001

This is a verifier-only packaging of the original D3-M1 candidate. It has not run
Dafny. The 20 planned checks are four reference/alternative successes, fourteen
ordinary proof failures and two hidden-export resolution failures. These are
expected outcomes, not measured results. The interface returns ghost certificates;
it does not implement executable search. This remains a development witness task.

`inputs/candidate/` preserves every file named by the original candidate manifest,
plus that exact manifest (SHA-256
`b7399a81a95de0471811c3808360a3c3ff5f109e2bc63fa38468db1d61d4ed91`).
The candidate's original documentation, construction tests, metadata and all 176
Dafny files are included. The parent experiment's README/status may change without
changing this runtime. Root `cases.json` differs from the copied original only by
prefixing each case path with `inputs/candidate/`; `tasks.json` is an exact copy.

`verify.py` imports the unchanged witness verifier saved in that candidate and
overrides only its `ROOT` and `validate_pins`. Its existing `run`, `verify`,
`matches`, classification, version checks and evidence writer are reused unchanged.
Pin validation checks the complete copied inventory, every source hash and the
mechanical case mapping. The flat `runtime-manifest.json` and
`fixture-manifest.json` are compatible with the existing compute staging format.
The existing `repair-diversity-expansion-001/compute_ops.py` hardcodes its own local
base and remote prefix: the parent must provide this runtime's intended root when
reusing those operations. Do not invoke its CLI unchanged for this new directory.

Run `python -B test_structure.py` for the offline import/fake-process preflight.
All seven runtime preflight methods passed locally; see `offline-tests.log`.
Two corrected local test-setup attempts are recorded under `preflight-history/`.
The tests prevent real child-process/network activity and never read credentials.
They exercise one full fake 20-case run, exact staged bytes, single-attempt raw
stdout/stderr/base64/CSV preservation, source copies, strict diagnostic categories,
pin failures and refusal to reuse an evidence directory. Synthetic summaries
remain in temporary directories and are not scientific verification evidence.

After source review and a fresh live check that `test` is nonpreemptible, the parent
may stage this exact bundle and submit `verify.sbatch` once. It requests two CPUs,
8 GB, 25 minutes and no requeue. Actual Dafny runs only on a compute node. The
runner requires a Slurm allocation and refuses a host name containing `login`.
There is one verifier process per case, with a 60-second command limit and a
75-second subprocess deadline. Timeout or execution failure stops the loop;
proof and frontend outcomes are preserved without retries.

The one fresh output directory is `verification-001`. It receives all pinned
inputs, exact tool-version output, per-case decoded and base64/raw output, CSV
bytes and hashes, source hashes, summary and a complete evidence inventory.
Parent review must distinguish proof failures from parse/type/termination errors,
preserve every unexpected result, and review all protected provider and client
obligations before declaring the candidate validated. No model/provider calls,
credential handoff, paid authorization, or submission are implemented here.
