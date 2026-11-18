# Real-source growth: reference qualification 001

This package prepares **two verifier-only invocations**, one for each complete
two-stage reference extension. Native verification has not yet run. The
reference bodies are analyst fixtures, not model-generated repository growth.
No model scope, paid runner, credentials or provider connectivity is included.

| Project | Phase-one case | Fixed native cap | Allocation |
| --- | --- | --- | --- |
| Dafny-VMC | `pair-reference`: MoveToFront plus PickPair | 300 seconds; resource limit 100,000 | 1 CPU, 2 GB; 30-minute job |
| Vest | `batch-reference`: frame plus counted batch | 900 seconds | 1 CPU, 4 GB; Cargo workers 1, Verus threads 1; 45-minute job |

Both use the already qualified pinned source snapshots, images and toolchains
at `outputs/real-repository-qualification-001`. Dafny runs every original
explicit source plus both new files. Vest runs the full default `vest_dev`
scope and dependency crates, with a fresh Cargo target and offline dependency
resolution. This does not extend coverage to excluded crates, feature sets or
trusted upstream definitions.

The new Dafny resource limit is a deliberate fixed change from the earlier
20,000-limit repair policy, informed by the published budget-sensitivity
diagnostic. Vest's one-worker, one-thread configuration is a deliberate
concurrency change from its earlier qualification. Neither change alters an
old score or freezes a future model evaluation policy. Budgets do not escalate
after failures.

## Inputs and later controls

`inputs/` contains exact small overlays for **12 Dafny and 13 Vest controls**,
with provenance to the sibling development packages. `plan.json` binds their
hashes and makes only the two reference cases executable. The other **23
controls have no dispatch route** in this runtime. They require a separately
published review binding actual reference outcomes, sources, commands, tool
identities and new verification inventories, followed by a separate fixed
control-dispatch preparation. Exit zero never releases them.

All 267 original Dafny unit names must be present together with the provisional
new function units. The unchanged native Verus parser retains every
`(crate,module,label,mode)` multiplicity, all three crate reports, exact
version metadata and whole-crate status; the only predeclared metadata change
is one Verus thread. Original inventory multiplicities must remain identical.
Both new proof functions must appear. Every additional emitted unit must
match a declared new function and is retained with its native result.

Logger names for the new code have not yet been observed. Missing or unexpected
new labels block readiness for inventory review. Fixed new Vest spec
definitions that do not emit timing units are enumerated as
`UNLOGGED_FIXED_SPEC_DEFINITION`, bound to their exact source hashes and never
counted as logged passes. These provisional observations still require root's
explicit source-bound review; this package creates no release/acceptance file.

## Evidence and outcome classification

The worker preserves the exact native command, source hashes before/after,
container and tool-closure checks, raw stdout/stderr, Dafny CSV or native Verus
JSON, `/usr/bin/time -v` resources and elapsed wall time. Failure evidence is
retained before any later deliberate revision. A passing client cannot hide
an unproved helper. Missing scope, changed sources, stale raw files, malformed
reports, frontend errors, timeouts and proof failures cannot count as success.

The exact baseline warnings remain visible. The copied warning policy v2
separately recognizes only its source-bound Cargo cleanup class; unknown or
missing warnings block readiness. Native proof completion, warning policy and
whole-scope coverage remain separate fields. Native summary counts are not
interchangeable with the timed-unit inventory.

`review.py` replays complete worker records and returns an evidence-integrity
review. A valid archive of a proof failure is not a successful reference.
Partial/startup failure archives remain available for manual review and cannot
produce the complete-evidence receipt.

## Root-only execution sequence

After local and remote state inspection and the user's socket-21 reconnect:

1. `python -B ops.py stage` copies the exact frozen package once.
2. `python -B ops.py preflight` runs only fake-process/import tests and shell
   syntax checks on the login node. It invokes no native verifier.
3. `python -B ops.py submit dafny-vmc` and `python -B ops.py submit vest` each
   submit their single reference once. Before submission the helper inspects
   its own state and queue and selects only live `test` or `shared` with
   `PreemptMode=OFF`, adequate time limits and `State=UP`.
4. Root monitors only those new receipts, then uses `ops.py fetch PROJECT`
   once terminal. The archive gate requires one exact parent JobID and an
   explicitly terminal state for it and every returned step. Missing/duplicate
   records, live or unknown states block accounting/archive writes. Complete
   state names with normal `+` display suffixes or `CANCELLED by <uid>` are
   normalized; truncated base names are never guessed. Full output, accounting,
   the terminal-state review and root Slurm logs are preserved.
5. `python -B review.py PROJECT` performs offline source/raw/inventory replay.
   Root inspects the actual new unit names and every unexpected outcome before
   pinning any later reference gate.

Submission intents, remote locks, fresh output/work directories, fresh build
targets and `--no-requeue` prevent automatic restart. Ambiguous submissions
require read-only investigation. No alternate runner, retry, standalone
control launch or old-job polling is part of this package.

The unmodified native capture/parsers and warning policy are listed in
`copy-provenance.json`. Adapted worker/reviewer/ops origins are listed in
`adaptation-provenance.json`. `runtime-freeze.json` pins only this self-contained
package, not any still-evolving edit protocol. Offline tests establish these
engineering checks using synthetic native reports and fake capture; they are
not evidence that the new Dafny or Verus source parses or proves.

The pre-staging archive-gate correction is recorded in `revision-002.json`.
`review-history-001/` preserves the original ops/tests, runtime freeze and
offline records; the original runtime is reconstructable byte for byte. New
local and isolated preflight evidence uses the `002` suffix. No native run or
historical result was changed by this correction.
