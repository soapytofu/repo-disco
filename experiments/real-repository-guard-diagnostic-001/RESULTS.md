# Separate syntax diagnostic

The guard revision admits all seven originally rejected responses without
changing any response body. They reconstruct to three distinct candidate files.
All 25 offline tests pass locally and in the staged Cannon environment.
The original pilot remains **7/16 qualified accepts** with its seven historical
guard rejections. No new model calls, mathematical edits or retries were made.

## Native outcomes

| Candidate | Saved slots covered | New observations | Outcome |
| --- | --- | --- | --- |
| Dafny-VMC swap | 1, 2, 15, 16 | 1 | Not accepted: 265 units pass; two downstream units exhaust the fixed resource limit |
| Dafny-VMC small shuffle | 12 | 1 | Accepted: all 267 units pass; only the three exact upstream warnings |
| Vest Pair proof | 7, 10 | 1 | All required proofs pass, exit 0; an additional Cargo cleanup warning prevents qualified acceptance |

**All three native observations are complete and reviewed.** Mapped to the
seven saved outputs, one is accepted, two complete all proofs with an additional
build warning, and four hit resource limits. There are no new frontend errors.
These mapped counts reuse identical-source observations; they are not seven
independent native checks or a revised model score.

Dafny job **61653288** completed in 83 seconds using one CPU / 2 GB. Both
observations preserve the exact 91-file source inventory except the registered
body. Both report all 267 required named units. The swap candidate exits 4 after
30.83 seconds; the small-shuffle candidate exits 0 after 32.48 seconds.
Native CPU usage was 90% and 94% of one core; peak resident memory was about
515–516 MiB. The full job used 59.314 CPU seconds, about 71.5% of its allocation.

The swap's own `FisherYates.Model.Swap (well-formedness)` unit passes.
The two failed CSV units have explicit **out-of-resource** diagnostics:

- `FisherYates.Correctness.InductionHypothesisPrecondition1 (correctness)`
- `FisherYates.Correctness.ProbabilityOfE (correctness)`

The native command still uses `--resource-limit 20000`. Its summary is
`265 verified, 0 errors, 2 out of resource`; the harness correctly withholds
full-workspace acceptance. This does not establish a mathematical counterexample.
No larger-budget rerun has been made. The small-shuffle candidate passes under
the unchanged warning policy; it is not a zero-warning result.

Vest job **61653437** completed in 501 seconds using four CPUs / 4 GB. The native
command took 215.28 seconds and exited 0. The complete 3,481-file source inventory,
all protected body boundaries and required coverage match. Native verified
counts are **340 vest_dev, 3,279 vest_lib and 2,102 vstd**, with zero errors and
all 5,410 required timed inventory entries (5,297 friendly labels) present and
passing. Native summary counts and timed-entry counts are distinct measures.

All five upstream warning blocks remain unchanged. One additional Cargo warning
reports failure to garbage-collect an incremental compilation session directory:
`Directory not empty (os error 39)`. This is a build-cleanup diagnostic, not a
failed proof. The exact frozen warning policy still rejects this candidate for
qualified acceptance. The warning is retained verbatim; it was not suppressed,
normalized away, retried or used to change the original scoring rule.

Vest's native process used 190% CPU (about 1.90 active cores on average) and
about 2.17 GiB peak resident memory. The full job used 416.368 CPU seconds,
**20.8%** of its four-core allocation. Approximately 286 seconds occurred outside
the timed native command, including tool/source validation, copying, hashing
and bookkeeping. This is not a measurement of any one preparation phase.
Future resource qualification should separate serial preparation from the
parallel command and test smaller allocations separately; no such rerun was
performed here.

## Evidence and interpretation

- [Offline exact replay](offline-replay.json) binds all sixteen saved responses,
  both guards, seven newly admitted outputs and nine unchanged prior candidates.
- [Source and diagnostic review](source-review-dafny-001.json) checks protected
  boundaries, source hashes and the exact failed/passed obligation names.
- [Native review](review-dafny-vmc-001.json), [transfer inventory](transfer-dafny-vmc.json)
  and [raw evidence](verification-dafny-vmc-001) preserve commands, stdout,
  stderr, CSV, resource use and source/coverage bindings.
- [Slurm accounting](accounting-dafny-vmc.txt) is separate from native timings.
- [Vest source/warning review](source-review-vest-001.json),
  [native review](review-vest-001.json), [full raw evidence](verification-vest-001),
  [transfer inventory](transfer-vest.json) and [accounting](accounting-vest.txt)
  retain the complete proof and additional-warning outcomes.
- [Final seven-output mapping and preservation review](final-review-001.json)
  bind all three native observations, all 36 transferred files, zero new model
  calls, and all 653 unchanged original pilot files.

Identical saved responses share a native observation only when their reconstructed
candidate files, parents, toolchain, command and coverage profile match.
The mapping does not turn repeated responses into independent verifier trials.
This retrospective diagnostic separates admission mistakes from native outcomes;
it is not a new model evaluation, a revised original score or a clean feedback
comparison. All 653 original pilot archive files remain pinned and unchanged.
The observed syntax exclusions are fixed in this separate guard revision.
Remaining native acceptance issues are solver-resource exhaustion and a build
warning; neither is fixed by relaxing the parser, and neither was automatically
repaired in this diagnostic.
