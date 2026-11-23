# Executable growth on two additional Dafny source projects

Prepared November 23, 2026 under Sophie's instruction to qualify the suggested
Dafny projects, run a small pilot, then proceed within the existing 100-new-call
ceiling. This experiment is in preparation. **No model request has been made.**

## Two selected component scopes

| Project / source pin | First addition | Second addition | Verification scope |
| --- | --- | --- | --- |
| Dafny standard library, release v4.11.0 / `fcb2042d6d043a2634f0854338c08feeaaaf4ae2` | Append all values to an existing mutable dynamic array | Append a rotated sequence and return its exact appended interval | Three unchanged library source files, plus the current additions |
| AWS Cryptographic Material Providers Library / `dab800a2a610253659d113ee6e4bf8a70b86d13a` | Read a U16 length-prefixed byte field with exact remaining suffix | Read two consecutive raw byte fields using the accepted field reader | The three-file UInt / BoundedInts / Wrappers include closure, plus the additions |

The additions are executable Dafny methods/function-methods under fixed host
contracts. The current AWS task reads raw byte fields; it does not validate UTF8,
construct encryption-context maps, or establish cryptographic security. The declared component
scopes are not claims that all source in either upstream repository is verified.
AWS's pinned `libraries` submodule shares Dafny library ancestry; the two source
projects are not statistically independent samples of all real software.

Only the current new body may change. Upstream bytes, contracts, types, imports,
host registration and an accepted parent's source stay fixed. A second stage
must receive its actual same-lineage model parent. Direct implementations remain
admissible; observed calls to the parent are measured separately from proof
success. The first-stage analyst reference is never a fallback model parent.

## Qualification before collection

Source acquisition checked all seven selected Dafny release artifacts and all
300 AWS/submodule artifacts against their Git blob hashes. Complete source
receipts are in [source-acquisition](source-acquisition/). The two toolchains are
Dafny 4.11.0 and AWS's declared verification version 4.9.1; native runs use one
CPU and one verifier process. The upstream AWS Makefile would interpret a
zero computed process count as unlimited `xargs` parallelism, so qualification
uses explicit serial native commands instead.

The initial standard-library job **63085478** failed before any Dafny process:
the batch script changed to `SLURM_SUBMIT_DIR`, which was the SSH home directory,
despite `sbatch --chdir`. Its full evidence is retained under
[qualification-001](qualification-001/retrieved-stdlib/). A deliberate separately
versioned correction binds the execution directory explicitly. No automatic
retry, source repair, model call or score change occurred.

The original standard-library baseline subsequently passed all 56 logged units.
Its first new reference failed because a loop invariant read the current dynamic
representation before the freshness invariant established permission to do so.
The second method passed under that unproved helper contract, so the workspace
was rejected. A separate body-only revision reorders the existing invariant;
job **63088122** verifies all **58 / 60** first-/second-stage units with zero
errors or warnings. Original failures, source hashes and full logs remain in
qualification-002; corrected evidence is in qualification-003. The unchanged
baseline is reused, not rerun. The nine distinct controls in job **63088528**
all match their declared expectations: two valid alternatives, five proof
failures and two omitted-module cases rejected for incomplete coverage.
Every control preserves all 56 upstream passes. An actually failed AppendAll
with passing AppendRotated is correctly rejected as a workspace. The three
positive scopes and nine controls are reviewed in
[native-profiles/stdlib-002](native-profiles/stdlib-002/).

The first two AWS launches stopped during solver metadata checks. The saved second diagnostic establishes
that the Ubuntu-packaged Z3 requires system-library versions absent on Cannon.
Qualification-004 uses the Z3 project's checksum-pinned manylinux1 build of the
same **4.12.1** solver version, retaining the exact Dafny **4.9.1** package and
source/resource settings. Both diagnostic streams are now saved before checking
metadata success. The original launcher also used an unsupported `--version`
spelling; its unsaved solver stream cannot be reconstructed or attributed to
one cause. No model call occurred during these failures.

The broad 102-file AWS baseline in job **63088520** did not qualify. It emitted
array-initialization and nonlinear-arithmetic diagnostics in unchanged upstream
files, reached the 900-second native wall cap, and ended with Slurm
`OUT_OF_MEMORY` at 4 GB. Its CSV and native resource streams are empty; there is
no complete proof inventory or numerical proof score. Only the baseline ran;
both new references remained undispatched. All 440 transferred files and exact
diagnostics are retained in [qualification-004](qualification-004/retrieved-aws/).

Before any model collection, [aws/revision-002](aws/revision-002/) declares a
new, narrower three-file UInt component and replaces the encryption-context
entry task with a raw frame-pair reader. It retains the upstream source bytes,
Dafny/Z3 versions, verifier flags, one CPU, 4 GB and the same native time/resource
limits. Its three positive cases must qualify before nine distinct controls.
The broader failed scope is preserved and is not being repaired or rescored.

Passing references, meaningful broken bodies, omitted-module controls and a
passing client with an unproved parent must all be reviewed before collection.
Whole-scope acceptance needs exact named native inventories, inherited warning
classification, unchanged source/tool hashes and complete resources. Existing
AWS axioms and externs are inventoried and preserved; invoking their trusted
shortcuts from new bodies is forbidden. Hashing a staged file is not proof of
verification coverage.

## Bounded collection design

The intended new allocation is **at most 12 calls**: one two-stage pilot lineage
per project (at most four calls), followed by two more independent two-stage
lineages per project (at most eight). Settings and prompts stay fixed between
the pilot and expansion. Each stage gets one response, with no retry,
reassignment or repair feedback loop. A failed parent blocks its child.

Expansion requires complete pilot accounting, no unresolved infrastructure or
integrity error, and at least one accepted first addition across the two
projects. Otherwise the cohort stops and all unused slots remain closed.
Mathematical failures and fully evidenced solver-resource failures are retained
as failures, never repaired or rescored within this cohort. Provider ambiguity,
missing evidence and source/tool drift stop dispatch. Exact prompts, native
profiles, runtime and authorization must be frozen and reviewed before launch.

The current prospective budget reserves 12 new slots in addition to the earlier
16, for **28/100 allocated** and 72 unallocated. Seven earlier requests returned;
this experiment has made none. Earlier closed slots are not reused. The user's new
instruction authorizes this work within that ceiling; it does not authorize
silently changing a frozen task after seeing responses.

Report accepted additions / attempted, completed lineages / planned, conditional
second-stage success, observed parent reuse, failure categories, request/token
counts and verification resources. This is a small development feasibility
study, not held-out evaluation, unrestricted repository generation or a causal
comparison of languages, depth or proof sharing.
