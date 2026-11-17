# Saved-output syntax diagnostic

This separate retrospective diagnostic fixes three lexical exclusions in the
original real-repository pilot: Dafny functional sequence updates, Dafny unary
negation after `assert`, and Verus `=~=` extensional equality. It does not change
the original guard, prompts, responses, candidates, scores or native evidence.
The original result remains **7/16 qualified accepts**.

No model requests are authorized or implemented here. Exactly seven originally
rejected saved responses are reconstructed without changing their body bytes.
They produce three distinct complete candidate files:

| Task | Original slots | New native checks |
| --- | --- | --- |
| Dafny-VMC swap | 1, 2, 15, 16 | 1 |
| Dafny-VMC small shuffle | 12 | 1 |
| Vest pair proof | 7, 10 | 1 |

Reuse requires the same task, body, candidate bytes, parent source inventory,
native command, toolchain and coverage profile. Envelopes may differ; each
original envelope and extraction receipt is retained. These are three new
native observations covering seven saved outputs, not seven independent runs.

The guard remains a bounded lexical policy, not a language parser or proof
checker. Its callable vocabulary, contracts, imports, signatures, protected
prefixes/suffixes and forbidden trust mechanisms are unchanged. Functional
updates are distinguished from writes to protected inputs; indexed, field and
tuple writes remain rejected. Rust macros remain forbidden. Native verification
decides whether admitted programs are well typed and proved.

`prepare.py` replays all sixteen saved responses under both guards. The nine
previously admitted candidate files must be byte-identical. The parent archive
is pinned in `parent-preservation.json`; source, scorer, environment and raw-log
bindings retain the original qualification policy, including exact upstream
warnings. The warning-only slot 13 and frontend-error slot 8 are out of scope.

Two exclusive Slurm jobs use the existing qualified toolchains: Dafny-VMC uses
one CPU / 2 GB for two sequential full-scope commands; Vest uses four CPUs / 4 GB
for one full default-crate command with three Verus threads and four Cargo
workers. Each uses a fresh source copy and build target, no requeue and no
automatic retry. A live nonpreemptible partition check precedes submission.
Source-copy/hash overhead is reported separately from native process resource
usage; four allocated CPUs do not imply four continuously active cores.

Run offline validation with `python -B preflight.py`. The operations script
stages the exact runtime once, repeats only the offline import/fake-process
preflight on Cannon, submits each verifier stage once, and fetches all raw
stdout/stderr/CSV/JSON/resource/accounting evidence. No provider SDK or credential
handling is included. A native failure is retained, never automatically repaired.

Results will be reported separately from the original experiment. This
post-hoc syntax diagnostic is not a fresh model evaluation or feedback comparison.
