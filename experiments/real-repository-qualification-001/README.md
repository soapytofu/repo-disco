# Dafny-VMC and Vest: pinned verifier qualification

Requested November 16, 2026. **Verifier-only; no model collection or paid calls.**
Qualification requires successful native baselines, reviewed coverage controls,
source-bound result classification, integrity checks and runtime evidence.
Setup completion alone never establishes proof success.

## Pinned sources and intended scope

| Project | Source commit | Toolchain | Declared baseline |
| --- | --- | --- | --- |
| Dafny-VMC | `e3631f8d335bf7ec3648b13976fa2a96a2a5406e` | Dafny 4.4.0, exact Ubuntu 20.04 release used by upstream `scripts/prep.sh`; bundled Z3 4.12.1 | `scripts/verify.sh` inputs: `dfyconfig.toml`, `docs/dafny/ExamplesRandom.dfy`, `tests/Tests.dfy`, `tests/TestsRandom.dfy`; resource limit 20000. CSV logging added for coverage evidence. |
| Vest | `333d61c1f0a2a5accc6962ee9a4ae05619fd0dcc` | Verus `0.2026.10.26.d17fbd0`, commit `d17fbd0c58abf0d5e86825ea64b96aba72b1b31f`, Rust 1.99.1; archive checksum from pinned `verus.json` and official release metadata | `cargo verus verify` for `vest_lib` and `vest_dev`, default features, locked dependencies, toolchain checking, distinct fresh target directories. JSON and expanded timing instrumentation added. |

Vest's other crates and nondefault feature configurations are outside this initial
scope. Dafny-VMC's native scope contains existing `{:verify false}`, extern,
axiomatized and termination-exempt code. Vest has existing external proof bodies.
These are fixed trust boundaries, not newly proved obligations. `trust-inventory.json`
records lexical review candidates with original file/line context; it is not a
complete static-analysis or soundness certificate.

`source-manifest.json` pins all 3,572 files in the two original public archives.
Both complete snapshots were staged unchanged. Most source is also vendored here
with upstream licenses; generated Vest HTML docs, benchmark binary corpora and a
GitHub illustration are excluded from Git publication by this directory's explicit
`.gitignore`. Their hashes and the pinned public archive URL remain recorded.
The verified `vest_lib` and `vest_dev` source, Cargo metadata, lockfile and scripts
are published. No runtime build products or large toolchain binaries enter Git.

## Baseline phases and preserved setup failures

Six offline runner checks passed locally and in Cannon's environment. The first
source transfer exceeded its coordinator timeout but finished remotely. A read-only
recovery check validated every source/runtime pin without retransferring files.
An offline preflight invoked before staging finished failed before tests or job
submission; `preflight-ordering-note.json` records it. No verifier ran during these
preparation checks.

- **Host Dafny-VMC, job61253728:** setup found the exact Dafny version, but the
  native verifier exited 1. Its bundled Z3 requires `GLIBC_2.29` and
  `GLIBCXX_3.4.26`, absent on Cannon's Rocky 8 host. Raw logs contain solver errors,
  skipped obligations and a subsequent Dafny exception. This is an environment
  failure, not a mathematical score or baseline pass. Job exit 0 only means the
  capture program saved the verifier's nonzero result.
- **Host Vest, job61253729:** download exited 28 after 240 seconds, receiving
  381,541,221 of 487,532,246 archive bytes. Verification did not start. The original
  partial bytes are pinned and retained remotely; full download logs are saved.
- **Container phase 002:** deliberate environment correction, with the first
  failures preserved. The same Dafny and Z3 binaries and all upstream source bytes
  are retained. Microsoft `dotnet/runtime:8.0-noble` is resolved to the immutable
  amd64 manifest in `container-002/image-pin.json`; the resulting SIF hash is
  recorded only after a successful pull. Job 61254231 failed before verification
  when MCR cancelled an HTTP/2 stream; full failure logs are retained.
- **Container phase 003, job 61255910:** keeps the exact immutable image digest
  and binaries, with `GODEBUG=http2client=0` selecting HTTP/1 download transport.
  [Go documents this setting](https://pkg.go.dev/net/http#hdr-HTTP_2). It is a
  deliberate transport correction, not an automatic verifier retry. The native
  Dafny baseline completed: 267 verified obligations, zero errors and three
  upstream trigger warnings, exit 0, 26.70 seconds. This supplies compatible OS libraries, not a substituted verifier.
- **Vest container phase 002:** prepared to copy and resume the pinned public
  partial download once, then require the exact upstream SHA-256 before unpacking.
  It uses the successful phase-003 container and HTTP/1 for the single resumed
  archive transfer. Rustup 1.28.2 and Rust 1.99.1 install into task-owned homes. Existing user
  installations and shell startup files are untouched. Its setup must finish
  before any Vest baseline can be scored. Job 61259311 completed setup and
  validated all three pinned version identities, but both native commands exited
  101 because the runtime image lacked `cc` for Rust dependency build scripts.
  No verification report was produced. All 60 transferred files are retained.
- **Vest container phase 003:** a deliberate build-environment correction uses
  immutable official `rust:1.99.1-slim-bookworm` image metadata, which supplies GCC
  and libc development files. The exact previously installed Verus and Rust are
  reused and version-compared; source and Cargo.lock remain unchanged. Cached
  dependencies are used offline, with distinct fresh target directories. This
  phase passed the compiler, Rust and Verus checks but failed the pinned Z3
  startup check: Bookworm lacks `GLIBC_2.38` and `GLIBCXX_3.4.31/3.4.32`.
  Job 61265172 and its full 28-file evidence are retained; no proof ran.
- **Vest container phase 004, job 61304625:** a newly pinned official Rust slim
  Trixie base supplies the identified glibc/C++ versions and compiler. The exact
  task-owned Verus, Rust and Z3 installations remain unchanged, with version
  equality checks before proof commands. Temporary image extraction now uses
  compute-local `/tmp`; final images and all logs stay in the versioned output.
  [Debian records glibc 2.41](https://packages.debian.org/trixie/libc6) and
  [GCC 14 C++ libraries](https://packages.debian.org/trixie/libstdc%2B%2B6).
  Both native commands now pass: `vstd` 2,102 verified, `vest_lib` 3,279 and
  `vest_dev` 340, all with zero errors. Five upstream warnings remain in `vest_dev`.
  Full 41-file evidence and the native review are saved.

All executions use compute nodes, live-checked nonpreemptible shared partition,
exclusive submission/output locks, fixed time/resource bounds and no requeue.
There are no automatic job/verifier retries. Environment phase changes are explicit
and versioned. No old model ledger or credentials are accessed.

## Coverage and scoring acceptance

After a native baseline is reviewed, its declared proof scope must be bound to
source/configuration hashes and named results. Subsequent adapter comparisons must
use the same toolchain, source and effective options. Controls must establish:

1. Correct scope/native agreement and rejection of deliberately broken proofs.
2. Detection of a failing file omitted from the command or Rust module graph.
3. Rejection of a client-only pass when its provider proof is absent or fails.
4. Rejection of altered contracts/configuration, new trust bypasses, stale source
   identity, missing named results or missing completion evidence.

Dafny CSV counts and Verus JSON function details are evidence, not a filename
inventory. The pinned Verus `main.rs`/`config.rs` excerpts in `reference/` document
the exact machine-readable interface and retain the upstream license. Cargo `focus`
is not full dependency verification. Any focused diagnostic must remain explicitly
ineligible for full-scope acceptance.

Raw stdout/stderr, tool versions, exit status, GNU time resource logs, per-unit
timing/resource data, source manifests and Slurm accounting are retained. A timeout,
skipped proof or infrastructure error must not be converted into a mathematical
failure rate or success. Runtime observations are not a performance benchmark.

See the versioned result folders and submission receipts for actual state. Neither
repository is qualified for model collection merely by this preparation.

## Reviewed Dafny-VMC result

[RESULTS.md](RESULTS.md) and [coverage review](coverage-001/review-001.json)
qualify the declared pinned VMC scope. Five fresh coverage invocations plus one
reused native baseline show exact agreement on 267 baseline units and a deliberately
broken `Swap`. Its `Shuffle` client still passes while `Swap` fails; full scope
therefore fails. A new failing file outside the upstream command's scope leaves
that command at exit zero, but is rejected for its missing required unit. Explicit
all-file invocation detects it. Eight offline tests passed locally and on Cannon.

This is a proof-scope qualification under the recorded upstream trust assumptions,
with three unchanged trigger warnings. It is not a zero-warning baseline, proof of
all upstream runtime code, or approval for arbitrary model edits. Future model
collection must bind a reviewed edit policy and this exact scope/toolchain; no
model runner or paid authorization has been introduced. Vest native baselines now
pass; its seven-command coverage phase is submitted as job 61311690 after eleven
offline checks passed locally and on Cannon. See [results](RESULTS.md) and
[the frozen control plan](vest-coverage-001/README.md).

## Connection and continuation

Socket 18 disappeared during the completed phase-003 job. The user reconnected
on socket 19; `phase_ops.py` now changes only the coordinator's transport. The
pinned original `ops.py` and all compute bundles remain unchanged. Never resubmit
an existing phase. The current job is the frozen Vest coverage phase, 61311690. Fetch once terminal
and review all seven controls; the successful native baseline has already been
retrieved and must not be polled or fetched again. `continuation-state.json`
records this handoff. No Bedrock key or model calls are needed.

For a fresh checkout, `source-manifest.json` records pinned public archive URLs,
archive hashes and every original file hash. Restore the excluded generated/docs
assets from those exact archives before using the strict full-snapshot staging
checks; never replace existing vendored files without verifying their hashes.
The one-use output/submission locks deliberately prevent rerunning an old phase.
