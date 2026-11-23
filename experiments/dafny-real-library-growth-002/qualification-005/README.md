# Final splice reference qualification

This deliberate revision contains exactly one new native observation:
`splice-reference` from `stdlib/revision-004/`. The previous source versions,
failed native results and full raw evidence remain unchanged. The passing
filter from qualification-004 and both passing AWS references are reused by
their exact source/evidence identity; none is dispatchable in this revision.
The revision-002 public specifications and explicit read/write headers are
unchanged; this revision changes proof bodies only. The inspection result now
reports its exact output path, derived from the selected freeze location,
with direct and generated-program regressions for existing output directories.

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
never SSH, Slurm, Dafny or models. Explicit regressions reject AWS dispatch and
any repeated filter reference or extra case.
Final logs and the project freeze are recorded only after the revised sources
and package have been reviewed.

Root operates this package from the experiment directory:

```sh
python3 -B qualification-005/ops.py inspect stdlib
python3 -B qualification-005/ops.py stage stdlib
python3 -B qualification-005/ops.py preflight stdlib
python3 -B qualification-005/ops.py submit stdlib
python3 -B qualification-005/ops.py status stdlib
python3 -B qualification-005/ops.py fetch stdlib
python3 -B qualification-005/review.py stdlib --output qualification-005/reviews/native-stdlib-001.json
```
