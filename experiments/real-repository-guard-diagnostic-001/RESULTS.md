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
| Vest Pair proof | 7, 10 | Pending | Job 61653437 is still running |

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

## Evidence and interpretation

- [Offline exact replay](offline-replay.json) binds all sixteen saved responses,
  both guards, seven newly admitted outputs and nine unchanged prior candidates.
- [Source and diagnostic review](source-review-dafny-001.json) checks protected
  boundaries, source hashes and the exact failed/passed obligation names.
- [Native review](review-dafny-vmc-001.json), [transfer inventory](transfer-dafny-vmc.json)
  and [raw evidence](verification-dafny-vmc-001) preserve commands, stdout,
  stderr, CSV, resource use and source/coverage bindings.
- [Slurm accounting](accounting-dafny-vmc.txt) is separate from native timings.

Identical saved responses share a native observation only when their reconstructed
candidate files, parents, toolchain, command and coverage profile match.
The mapping does not turn repeated responses into independent verifier trials.
This retrospective diagnostic separates admission mistakes from native outcomes;
it is not a new model evaluation, a revised original score or a clean feedback
comparison. All 653 original pilot archive files remain pinned and unchanged.
