# Pinned real-repository qualification results

Verifier-only. No model calls. Dafny-VMC is qualified for the declared scope; Vest has successful native baselines; its coverage controls are submitted.

| Dafny-VMC observation | Native result | Coverage decision |
| --- | --- | --- |
| Unchanged baseline | 267 verified, 0 errors; exit 0 | Native and explicit-source adapter agree on all 267 units |
| Broken real `Swap` body | 266 verified, 1 proof error | Native and adapter both reject; `Shuffle` still passes |
| New failing file omitted from original command | 267 verified, 0 errors; exit 0 | Rejected: required `QualificationDetached.Fails` result absent |
| Same failing file explicitly verified | 267 verified, 1 proof error | Rejected with actual assertion failure |

All four cases retain exactly three upstream trigger warnings. Warning diagnostics are classified separately from frontend errors; none of these observations is a zero-warning result.

Source coverage: 28 declared Dafny input files; 267 uniquely mapped obligations across 26 files. `DafnyVMCTrait.dfy` contains explicit upstream `{:verify false}` bodies and `Bitstream/Interface.dfy` defines ghost state without a method body. Neither is counted as a logged proof pass. Other existing axioms, external declarations and termination exemptions remain explicit trust boundaries.

The baseline took 26.70 seconds. Coverage job 61260179 completed in 3m34s; each command has its own wall time, GNU time resource report, named CSV, stdout/stderr and source/profile binding. No timeout or frontend failure occurred in these successful qualification runs. These times are observations, not a performance benchmark.

The full 29-file container/baseline transfer and 47-file coverage transfer are retained. The coverage review checks runtime/transfer pins, full source identities before and after, installed tool files against the pinned archive, command and toolchain bindings, raw hashes, exact warning diagnostics, named units and direct/adapter agreement. Eight offline tests cover missing/altered source, configuration changes, stale/missing evidence, malformed CSV, omitted units and false summary success.

Earlier host-library and HTTP/2 image-pull failures are preserved separately and are not proof scores. The source snapshots and upstream contracts are unchanged outside the exact host-authored negative-control patches.

See [coverage-001/review-001.json](coverage-001/review-001.json), [profile.json](coverage-001/profile.json), [full raw results](coverage-001/results/) and [native baseline](container-003/results/native-baseline/).

## Vest native baseline and pending coverage gate

Job **61304625** completed in 13m56s. The native commands use the exact upstream-pinned Verus `0.2026.10.26.d17fbd0`, Rust 1.99.1 and Z3 4.16.0, under the immutable Trixie environment. Both exit zero with unchanged source and lockfile. No model calls.

| Native report | Verified | Errors | Timed entries | Distinct friendly labels |
| --- | ---: | ---: | ---: | ---: |
| `vstd` dependency | 2,102 | 0 | 1,888 | 1,888 |
| `vest_lib` | 3,279 | 0 | 3,182 | 3,070 |
| `vest_dev` | 340 | 0 | 340 | 339 |

The library command reports `vstd` and `vest_lib`; the development-root command independently reports all three. Do not add the repeated dependency baselines as independent tasks. Verus's verified counts and timed entries measure different things. Friendly labels can repeat; the versioned scorer retains their multiplicities instead of discarding duplicates or calling each label a unique proof obligation.

The library command takes 242.23 seconds, with no warnings. The development-root command takes 249.79 seconds and retains **five upstream warnings**: one attribute on an already external item and four derived Clone implementations without Verus specifications. This is not a zero-warning root baseline. Cargo's “generated 5 warnings” line is a summary, not a sixth warning.

All **41 transferred files**, raw JSON/stdout/stderr, GNU time resource logs, versions, tool-archive closure and source checks are saved in [vest-container-004](vest-container-004/). [The native review](vest-container-004/baseline-review-001.json) records the actual observations. Earlier download, missing-linker and Z3-library setup failures remain preserved and are not proof scores.

The frozen [Vest coverage phase](vest-coverage-001/README.md) passed eleven offline tests both locally and on Cannon, including exact native replay, repeated-label multiplicities, missing provider/module evidence, stale run IDs, changed source/commands/tools and corrupted or missing output. The rejected initial uniqueness assumption is retained separately. Job **61311690** is submitted once on nonpreemptible shared, with seven fresh controls and at most two concurrent commands. Each has its own source copy and fresh target directory; Verus uses three threads per invocation, matching the native baseline. **Coverage qualification remains pending its actual results.**
