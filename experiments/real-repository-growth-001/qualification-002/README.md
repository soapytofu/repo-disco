# Namespace-revised Dafny reference qualification 002

This is a new, verifier-only package for **one full-scope Dafny-VMC
`pair-reference` invocation**, using the reviewed namespace revision in
`../dafny-revision-002/`. Native resolution and proof outcomes are still unknown.
No Vest invocation, negative control, provider call or paid runner is available
through this package.

The original reference job **61747428** stopped with exit **2** and
`RESOLUTION_OR_TYPE_FAILURE`: the added FisherYates child modules introduced
an enclosing-module import cycle. Its source, full logs, outcome and original
`qualification-001` package are unchanged. This package does not touch or
manage Vest job **61747454**, which belongs exclusively to that earlier
qualification.

## Exact scope

The only two overlay files are:

- `repodisco-growth/MoveToFront.dfy`: top-level `RepoDiscoGrowthShift`, with
  `Model = FisherYates.Model`.
- `repodisco-growth/PickPair.dfy`: top-level `RepoDiscoGrowthPick`, with
  `Shift = RepoDiscoGrowthShift`Public`.

Only namespace/import header bindings changed from the preserved failure.
Contracts, bodies, decreases, exports, call arguments and all **91 upstream
files** remain fixed. `plan.json` binds the reviewed revision manifest and
diff/provenance hashes. It authorizes one native reference command and no
other case. The original body-edit policy still binds the old namespaces:
**it is not live-compatible with these revised sources** and requires a
separate reviewed revision after mathematical qualification. This package
does not revise or freeze a model policy.

The native command retains all **28 original explicit source arguments**, the
original project configuration and both additions. Qualification requires all
**267 original named units**, both provisional new function units and the
unchanged baseline warning policy. Original upstream trusted/unlogged
definitions retain their existing status; they are not new logged passes.
New logger names still require actual native confirmation and root review.

## Fixed resources and evidence

- **1 CPU, 2 GB**, 30-minute Slurm allocation.
- **300-second native wall cap**, Dafny **100,000 resource limit**.
- Exact prior Dafny 4.4 tool closure, Z3 and container-image bindings.
- Fresh work/output paths and exclusive submission lock; no automatic retry,
  requeue, resource escalation or source repair.

The capture function and native parser are copied unchanged from the reviewed
prior package. The narrowed worker keeps exact source hashes before/after,
command and tool bindings, native stdout/stderr, all CSV unit results,
`/usr/bin/time -v` resources and wall time. An incomplete or failed proof is
preserved as evidence, never accepted by exit code alone. The reviewed terminal
archive gate is unchanged: one exact parent JobID and every returned relevant
step must have an explicitly terminal state before accounting/archive writes.

The other **11 Dafny control cases** remain outside this runtime, pending a
source-bound reference and actual-inventory review followed by a separately
prepared control run. A successful reference never releases them automatically.
No Vest input, image profile, script or stage is included in the runtime.

## Root-only execution after publication and review

The new remote destination is
`~/formal-disco/outputs/real-repository-growth-001/qualification-002`.
The job name is `growth-namespace-dafny`, distinct from the original reference.

1. Inspect local/remote state, then `python -B ops.py stage` once.
2. Run `python -B ops.py preflight`; this uses fake-process tests and shell
   syntax checks only, with no native verifier.
3. Run `python -B ops.py submit dafny-vmc` once. It checks its own receipts,
   outputs and queue, then selects only a live `test` or `shared` partition
   with `PreemptMode=OFF` and adequate time limit.
4. Monitor only the new receipt, fetch only after the terminal-state gate
   passes, and run `python -B review.py dafny-vmc` for offline evidence replay.

`copy-provenance.json` records exact copied sources, parser and tool metadata.
`derived-input-provenance.json` documents removing unrelated Vest metadata.
`adaptation-provenance.json` records narrowing the reviewed runtime to one
reference. `runtime-freeze.json` pins this self-contained package; prior
experiments are never changed or imported for execution. Offline fake-process
tests do not establish successful native parsing or mathematics.
