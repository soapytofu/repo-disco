# Pinned real-repository qualification results

Verifier-only. No model calls. Dafny-VMC and Vest are qualified for their declared pinned scopes. All native baseline and coverage jobs are complete, with full raw evidence retained. This does not authorize model collection or qualify arbitrary edits.

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

## Vest native baseline and completed coverage gate

Job **61304625** completed in 13m56s. The native commands use the exact upstream-pinned Verus `0.2026.10.26.d17fbd0`, Rust 1.99.1 and Z3 4.16.0, under the immutable Trixie environment. Both exit zero with unchanged source and lockfile. No model calls.

| Native report | Verified | Errors | Timed entries | Distinct friendly labels |
| --- | ---: | ---: | ---: | ---: |
| `vstd` dependency | 2,102 | 0 | 1,888 | 1,888 |
| `vest_lib` | 3,279 | 0 | 3,182 | 3,070 |
| `vest_dev` | 340 | 0 | 340 | 339 |

The library command reports `vstd` and `vest_lib`; the development-root command independently reports all three. Do not add the repeated dependency baselines as independent tasks. Verus's verified counts and timed entries measure different things. Friendly labels can repeat; the versioned scorer retains their multiplicities instead of discarding duplicates or calling each label a unique proof obligation.

The library command takes 242.23 seconds, with no warnings. The development-root command takes 249.79 seconds and retains **five upstream warnings**: one attribute on an already external item and four derived Clone implementations without Verus specifications. This is not a zero-warning root baseline. Cargo's “generated 5 warnings” line is a summary, not a sixth warning.

All **41 transferred files**, raw JSON/stdout/stderr, GNU time resource logs, versions, tool-archive closure and source checks are saved in [vest-container-004](vest-container-004/). [The native review](vest-container-004/baseline-review-001.json) records the actual observations. Earlier download, missing-linker and Z3-library setup failures remain preserved and are not proof scores.

The frozen [Vest coverage phase](vest-coverage-001/README.md) passed eleven offline tests both locally and on Cannon, including exact native replay, repeated-label multiplicities, missing provider/module evidence, stale run IDs, changed source/commands/tools and corrupted or missing output. The rejected initial uniqueness assumption is retained separately. Job **61311690** completed on nonpreemptible shared in **27m29s**. All seven fresh controls matched their expected outcomes. Each used its own source copy and fresh target directory; at most two commands ran concurrently with three Verus threads each, matching the effective native baseline setting. There was one submission, no requeue and no automatic retries.

| Coverage invocation | Native exit / proof result | Harness decision |
| --- | --- | --- |
| Unchanged adapter baseline | 0; all three crate reports pass | Accept declared scope; exact native inventory agreement |
| Broken provider, native and adapter (two invocations) | 101; `theorem_serialize_parse_roundtrip` assertion fails | Reject; `vest_lib` fails and Cargo never reaches `vest_dev` verification |
| Client-only `focus` with the same broken provider | 0; all 340 root verified counts pass | Reject full scope: dependency proof reports are absent |
| Unregistered failing file | 0; original three crate reports pass | Reject: required `omitted_failure` result absent |
| Registered failing file, native and adapter (two invocations) | 101; `omitted_failure` assertion fails | Reject; complete intended inventory includes the failing unit |

Native and adapter results agree on the unchanged scope, the broken provider and the registered failing module. The `focus` output includes passing results for the four concrete dependent-format roundtrip clients, but no verified provider; this cannot count as workspace success. The registered case has 340 root passes plus one actual failure. The omitted case has the same existing passes but lacks that required result. These are deliberately injected coverage controls, not natural repository bugs or model repair results.

The scorer preserves five upstream root warnings and rejects any unexpected warning set for an otherwise positive scope result. One rejected native provider-control run additionally reports a Cargo cache last-use **database locked** warning; it still emits the expected named assertion failure. The complete warning and its cause remain in raw stderr. The corresponding adapter run has the same proof outcomes without that cache warning. No result was rerun or rescored to remove it.

The [frozen offline review](vest-coverage-001/review-001.json) reconstructs all seven source/command/tool/run-ID/raw-result bindings and compares actual unit labels, multiplicities, summaries and diagnostics. All 56 transferred files are retained in [the coverage archive](vest-coverage-001/); the installed Verus archive closure is identical to the reviewed baseline. Eleven offline tests pass locally and on Cannon. Changed source or contracts, command bypasses, stale IDs, missing/altered raw evidence and incomplete inventories are rejected. This host-authored exact-candidate policy is not a general model patch guard.

Observed command wall times range from 135.01 to 341.49 seconds, with no timeouts or frontend failures. Per-command GNU time peak RSS ranges from 1,143,576 to 2,292,556 KiB; Slurm reports 4,752,428K for the concurrent batch. Native sequential baselines record 2,283,824 KiB (`vest_lib`) and 2,267,032 KiB (`vest_dev`). Compilation is included; source staging and post-run hashing are outside command time. These are resource observations, not a speedup or cross-language performance comparison.

Qualification covers the pinned default-feature `vest_dev` module tree and its verified `vest_lib`/`vstd` dependencies, under the recorded upstream external/trusted definitions and warnings. It does not cover every staged file, every workspace crate, alternate features, arbitrary new edits, verifier soundness or all runtime behavior. Future real-repository model tasks still need a frozen edit policy and declared required proof inventory; no such model run or paid authorization was added.
