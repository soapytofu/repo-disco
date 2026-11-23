# Source-bound native reference profiles

This directory reviews saved verifier observations. It runs no verifier, provider,
SSH command, or model request. A native proof result is usable here only after
the corresponding qualification archive passes its original source, tool,
accounting, command and raw-log review.

`selection-001.json` deliberately leaves both standard-library selections unset.
The AWS-only inspection in `reviews/aws-native-002/` maps 81 counted-frame and
79 tagged-pair named units, including the same 77 inherited units in each case.
All are native passes with zero warnings. The profiles retain definitions that
do not emit CSV units as explicitly unlogged source-bound observations, never
as proof passes. The actual primary function labels are well-formedness units.

The original standard-library references failed; a passing AWS inspection does
not qualify them. A later selection must explicitly name a passing version's
fixture manifest, edit profile, immutable base, qualification runtime and exact
observation. No implicit latest-directory selection is permitted. Both original
fixture manifests and earlier failed observations remain bound to the final
review. Earlier inspections and test logs are retained; `review-history-001/`
preserves the code before explicit receipt and fixture-pin checks were added.

The final `reference-gate.json` may be written only when all four selected tasks
have actual passing references. No aggregate gate has been issued by this
preparation. Each task's eventual gate entry includes its native profile and
strict replay receipt, exact record/raw/source pins, edit profile and base pins,
run ID, raw fingerprint, actual target labels and complete per-task input pins.
All input paths are relative to `dafny-real-library-growth-002`. Consumers must
verify these pins and the replay's zero-warning, full-coverage result; the top
level `PASS` flag is insufficient by itself.

Run a partial inspection only with an explicit output name:

```sh
python3 -B native-profiles-001/review.py \
  --selection native-profiles-001/selection-001.json \
  --tasks aws-batch aws-tagged --inspection aws-native-NEW
```

Run from the experiment directory. Outputs are exclusive: existing inspection
files or a final gate are never overwritten. A full build omits `--tasks` and
`--inspection`; it rejects missing, failed, stale or incompletely mapped
references. Nine focused offline checks passed in `reviews/tests-002.*`,
including actual failed-reference rejection, stale raw bytes, missing units,
duplicate/unknown labels, changed contracts and missing fixture pins.

This gate releases reference evidence for subsequent review of controls. It
does not authorize model collection or establish model performance.
