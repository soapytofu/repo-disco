# Pinned real-repository qualification results

Verifier-only. No model calls. Dafny-VMC is qualified for the declared scope; Vest is still in its pinned setup/baseline phase.

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

Vest: archive checksum, Verus release identity and Rust toolchain setup are being evaluated in job 61259311. No Vest qualification claim yet. Its initial partial-download failure remains saved.
