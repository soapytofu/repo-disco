# Remaining-control observations

Both verifier-only jobs completed on one CPU each. Full source, native CSV,
stdout/stderr, resources, frozen inputs and accounting are retained: 458 files
for Stdlib job **63182430** (1m45s), and 464 files for AWS job **63182480** (1m56s).

| Project | Declared controls | Expectations matched | Unexpected outcomes |
| --- | ---: | ---: | --- |
| Stdlib | 14 | 12 | two resource failures |
| AWS | 12 | 12 | none |

There are no missing observations or warnings. All four omission controls have
native-success exits but lack their declared target units, so the reviewer
rejects them for incomplete coverage. Both AWS unproved-helper controls exhibit
actual passing caller units and failed helper units; neither is accepted as a
complete workspace.

`splice-no-tail-pop` exceeds the unchanged 1M limit. `splice-unproved-seed` has
both a genuine AppendAll postcondition failure and an out-of-resource Splice
unit. They do **not** satisfy their intended ordinary-proof-failure categories,
and the latter does not demonstrate a passing splice caller. The original
expectations, sources and failed reviews remain unchanged.

Two new, separately versioned controls will use the already-verified rebuild
alternative: retaining old content instead of clearing it, and pairing the
unchanged passing caller with an unproved AppendAll helper. Only those new
sources need further native observations. The 24 matching controls will be
reused by exact evidence identity, not rerun. No combined qualification release
or model collection has occurred; all observations here are analyst controls.
