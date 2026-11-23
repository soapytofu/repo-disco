# Revised Stdlib reference qualification

This deliberate revision contains exactly two new native observations:
`filter-reference` and `splice-reference` from `stdlib/revision-002/`. The
original qualification-001 source, failed native results and raw evidence remain
unchanged. AWS has no configuration, dispatch route or freeze in this revision.

The collector, archive protocol and reviewer are adapted from qualification-001.
The same standard-library toolchain and resource settings remain: Dafny 4.11.0,
one core, resource limit 1,000,000, a 300-second verifier limit and a 360-second
outer cap. The single Slurm job requests one CPU, 4 GB and one hour on a
live-confirmed UP/nonpreemptible `test` partition, with no requeue or retries.
Every verifier and version-check child excludes `AWS_*`, `BOTO_CONFIG`,
`BOTO_PATH` and `BEDROCK_API_KEY` without reading their values.

Only the exact reviewed revised sources may be frozen. Full explicit argv,
source and tool hashes, CSV rows, stdout/stderr and resources are retained.
The reviewer checks all inherited native labels and reports actual new labels;
it never issues a qualified profile or acceptance. New declarations with no
native unit remain explicitly unlogged and require manual review.

All remote code and staging bytes use bounded stdin transport. Exclusive local
and remote stage/submission/archive intents, exact terminal parent/step checks,
inventory replay and safe extraction remain in force. No provider, model or key
handoff operation exists. No controls or original reference reruns are enabled.

The offline suite uses synthetic process responses and tiny Python subprocesses,
never SSH, Slurm, Dafny or models. An explicit regression rejects AWS dispatch.
Final logs and the project freeze are recorded only after the revised sources
and package have been reviewed.

Root operates this package from the experiment directory:

```sh
python3 -B qualification-003/ops.py inspect stdlib
python3 -B qualification-003/ops.py stage stdlib
python3 -B qualification-003/ops.py preflight stdlib
python3 -B qualification-003/ops.py submit stdlib
python3 -B qualification-003/ops.py status stdlib
python3 -B qualification-003/ops.py fetch stdlib
python3 -B qualification-003/review.py stdlib --output qualification-003/reviews/native-stdlib-001.json
```
