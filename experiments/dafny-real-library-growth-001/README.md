# Executable growth on two additional Dafny source projects

Prepared November 23, 2026 under Sophie's instruction to qualify the suggested
Dafny projects, run a small pilot, then proceed within the existing 100-new-call
ceiling. This experiment is in preparation. **No model request has been made.**

## Two selected component scopes

| Project / source pin | First addition | Second addition | Verification scope |
| --- | --- | --- | --- |
| Dafny standard library, release v4.11.0 / `fcb2042d6d043a2634f0854338c08feeaaaf4ae2` | Append all values to an existing mutable dynamic array | Append a rotated sequence and return its exact appended interval | Three unchanged library source files, plus the current additions |
| AWS Cryptographic Material Providers Library / `dab800a2a610253659d113ee6e4bf8a70b86d13a` | Read a U16 length-prefixed byte field with exact remaining suffix | Read one encryption-context key/value entry using the accepted field reader | 102 unchanged source files in the selected include closure, plus the additions |

The additions are executable Dafny methods/function-methods under fixed host
contracts. The AWS task reads a single entry, not a complete canonical context,
and does not change or establish cryptographic security. The declared component
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

The preceding budget snapshot has 16 slots allocated, seven returned requests
and 84 slots unallocated. Earlier closed slots are not reused. The user's new
instruction authorizes this work within that ceiling; it does not authorize
silently changing a frozen task after seeing responses.

Report accepted additions / attempted, completed lineages / planned, conditional
second-stage success, observed parent reuse, failure categories, request/token
counts and verification resources. This is a small development feasibility
study, not held-out evaluation, unrestricted repository generation or a causal
comparison of languages, depth or proof sharing.
