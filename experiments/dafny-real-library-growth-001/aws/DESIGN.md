# AWS MPL: executable frame reader → encryption-context entry reader

Status: source-informed **draft; all new native outcomes UNKNOWN**. No model,
provider, native verifier, credential or Slurm calls were made in preparing this
directory. Root owns qualification, execution, budgets and publication.

## Recommended scope

Use AWS's existing Dafny byte/UTF8/type APIs to add two executable functions:

1. **ReadU16Frame** in a new StandardLibrary module. Read an unsigned big-endian
   two-byte length, return exactly that many payload bytes and the remaining
   suffix, or fail on a missing length/truncated payload. The fixed contract
   requires success **if and only if** a complete frame is present.
2. **ReadContextEntry** in a new material-provider application module. Starting
   from the actual accepted first-stage source, read two frames, validate both
   byte strings with the existing UTF8 predicate, and return a singleton
   `AwsCryptographyMaterialProvidersTypes.EncryptionContext` plus the untouched
   remaining suffix. The fixed contract requires success **if and only if**
   both frames are complete and both payloads satisfy the existing UTF8
   predicate. Empty keys and values are valid.

This is a new executable parser pair, not two additional ghost lemmas. It
complements the existing serializer's key-length/key/value-length/value layout.
It does **not** parse a complete canonical context, its pair-count prefix,
ordering, duplicate-key policy or aggregate size policy. It does not change
cryptographic primitives, existing service operations or upstream public APIs,
and establishes no cryptographic/security property.

The second addition is a new application-layer caller located beside the
existing serializer. No existing public service is claimed to call this new
reader. Integrating it into a production service is a separate task. Exact
module registration and intended verification roots remain host-owned.

This framing shape overlaps previous development work on Vest. These AWS tasks
are inspected development tasks, not an independent held-out semantic family
or a language comparison.

## Source evidence and pin

Repository: [aws/aws-cryptographic-material-providers-library](https://github.com/aws/aws-cryptographic-material-providers-library).
Commit: [dab800a2a610253659d113ee6e4bf8a70b86d13a](https://github.com/aws/aws-cryptographic-material-providers-library/commit/dab800a2a610253659d113ee6e4bf8a70b86d13a),
committed November 17, 2026. Recursive tree
`906adf3ffb3f523e95e1faea416dfafbb6cc604a` was complete, not truncated.
[source-fetch-manifest.json](source-fetch-manifest.json) records all 184 Dafny
source files and 22 selected build/version/license files by Git blob SHA and
byte size. Snapshot inclusion is not proof coverage.

| Existing source | Why it matters |
| --- | --- |
| [StandardLibrary/src/UInt.dfy](https://github.com/aws/aws-cryptographic-material-providers-library/blob/dab800a2a610253659d113ee6e4bf8a70b86d13a/StandardLibrary/src/UInt.dfy) | `SeqToUInt16` accepts exactly two bytes and ensures reencoding equals its input. `UInt16ToSeq` and `HasUint16Len` define the actual representation/bound. |
| [StandardLibrary/src/UTF8.dfy](https://github.com/aws/aws-cryptographic-material-providers-library/blob/dab800a2a610253659d113ee6e4bf8a70b86d13a/StandardLibrary/src/UTF8.dfy) | `ValidUTF8Seq` is executable; `ValidUTF8Bytes` is the actual subset type. The reader uses this predicate, not the external Encode/Decode functions. |
| [CanonicalEncryptionContext.dfy](https://github.com/aws/aws-cryptographic-material-providers-library/blob/dab800a2a610253659d113ee6e4bf8a70b86d13a/AwsCryptographicMaterialProviders/dafny/AwsCryptographicMaterialProviders/src/CanonicalEncryptionContext.dfy) | Existing serialization constructs `UInt16ToSeq(length(key)) + key + UInt16ToSeq(length(value)) + value`. This supplies the application meaning; it is preserved unchanged. |
| [Generated material-provider types](https://github.com/aws/aws-cryptographic-material-providers-library/blob/dab800a2a610253659d113ee6e4bf8a70b86d13a/AwsCryptographicMaterialProviders/dafny/AwsCryptographicMaterialProviders/Model/AwsCryptographyMaterialProvidersTypes.dfy) | `EncryptionContext = map<Utf8Bytes, Utf8Bytes>`, with `Utf8Bytes = ValidUTF8Bytes`. The new reader returns this real type; the generated model is immutable. |
| [libraries/Wrappers](https://github.com/dafny-lang/libraries/blob/b486ff7faadbf306ed7e71386a2b0aeb1e38bd4d/src/Wrappers.dfy) | Actual `Result<value,error>` success/failure API, pinned through the AWS submodule. |

The reviewed upstream serializer already implements serialization, so proposing
another equivalent serializer would be weak growth. The selected new operation
reads a framed prefix and preserves its suffix. Native qualification must still
check syntax, contracts, actual proof inventory and executable behavior.

## Exact draft boundary

Draft reference overlays are under [draft/overlay/](draft/overlay/). These are
analyst reference solutions and must never be model context, model parents or
model successes. The native control proposal is [draft/controls.json](draft/controls.json).

The source-bound first native cases are prepared in
[cases-001/manifest.json](cases-001/manifest.json): `aws-baseline-001` has 102
explicit original source roots (1,303,397 bytes), `aws-stage1-reference-001` has
103 roots, and `aws-stage2-reference-001` has 104. The three anchors' recursive
includes are complete, and every original file matches the acquisition
receipt's Git blob hash and SHA-256. These are construction checks only;
every native outcome remains UNKNOWN. `build_cases.py` constructs exclusive
workspaces and performs no network or native execution.

Protected at both stages:

- Every upstream source byte, type, contract, import, trust annotation and
  selected proof-scope root; host registration is explicitly pinned separately.
- The added datatypes and the fixed structural/semantic predicates.
- The current function's signature, success-completeness contract and exact
  payload/map/suffix postconditions.
- The entire actual accepted first-stage source and receipt during stage two.

Only the current executable function body may change. No new axioms, assume
statements, verification bypasses, contracts or external bodies. No memory-size
axiom is introduced: lengths/slicing use mathematical `nat`, and the decoded
length is already an existing bounded `uint16`.

The future guard must also reject calls into existing axiomatized memory-bound
helpers, SortedSets extern enumerators, or UTF8 Encode/Decode as substitutes for
proof. Preserve the current reader API boundary: existing UInt conversion,
UTF8.ValidUTF8Seq and the actual accepted frame reader are legitimate calls.
Inheriting an upstream trusted declaration does not authorize a new candidate
to use it as an arbitrary-input proof shortcut.

An accepted first-stage reference is not a valid replacement for a failed model
parent. A failed parent blocks its child. API use is measured separately:
the reference calls `ReadU16Frame` twice, but a direct implementation satisfying
the same protected contracts remains mathematically admissible unless a
separately declared syntactic-use condition is selected before collection.
Calls alone do not establish necessary proof dependence.

## Toolchain and serial command requirements

[project.properties](https://github.com/aws/aws-cryptographic-material-providers-library/blob/dab800a2a610253659d113ee6e4bf8a70b86d13a/project.properties)
selects **Dafny verifier 4.9.1**, distinct from base/transpiler 4.9.0 and Rust
4.10.0. Record the exact verifier archive/hash, `dafny --version`, .NET runtime,
bundled Z3 binary/hash/version and full argv on the compute node. Do not silently
substitute the separate Dafny Standard Library project's 4.11.0 toolchain.

The pinned
[shared Makefile](https://github.com/aws/aws-cryptographic-material-providers-library/blob/dab800a2a610253659d113ee6e4bf8a70b86d13a/SharedMakefileV2.mk)
includes smithy-dafny commit `d0f6d61d3b030bb9cc7b93cee5e69fb591a246b6`.
Its [verification command](https://github.com/smithy-lang/smithy-dafny/blob/d0f6d61d3b030bb9cc7b93cee5e69fb591a246b6/SmithyDafnyMakefile.mk)
uses function syntax 3, non-Unicode characters, determinism, CSV logging,
100-second verification time limit, and allow-deprecation/external-contracts.
The StandardLibrary resource limit is 500,000,000; the material-provider
component limit is 90,000,000.

**Do not use `make verify CORES=1` alone.** The pinned formula computes
`DAFNY_PROCESSES = (CORES-1)/Z3_PROCESSES`; at one core that is zero, and
`xargs -P 0` permits unlimited file processes. Either override all three
variables (`CORES=1 DAFNY_PROCESSES=1 Z3_PROCESSES=1`) or use serial fixed argv.
The latter also avoids invoking Gradle just to derive `--enforce-determinism`.

For a predeclared explicit root file, the source-derived fixed argv is:

```text
dafny verify --cores 1 --enforce-determinism --unicode-char false
  --function-syntax 3 --log-format csv --verification-time-limit 100
  --resource-limit LIMIT --allow-deprecation --allow-external-contracts ROOT.dfy
```

Root must select and freeze one appropriate limit per declared component/scope,
a process wall timeout and Slurm bound before verification. Source limits above
are provenance, not evidence that a run succeeds. Any changed resource policy
is a separately reported qualification, not an unnoticed escalation.

The AWS libraries submodule is pinned at
`b486ff7faadbf306ed7e71386a2b0aeb1e38bd4d`; at minimum stage one needs
`libraries/src/BoundedInts.dfy` and `libraries/src/Wrappers.dfy`. Stage two
pulls the actual model's StandardLibrary, keystore, primitives, DynamoDB and KMS
include closure. Fetch source closure recursively and preserve all relative
paths. No generated Java/.NET/Rust release trees or cryptographic live services
are needed for these source checks. The upstream verification workflow explicitly
says the private encryption-specification submodule is unnecessary.

## Baseline and coverage gates before collection

Select a **dependency-closed declared component scope**, not all unrelated
repository projects. Start from the actual UInt, UTF8, CanonicalEncryptionContext
and material-provider type source anchors. Resolve every include and list each
required concrete implementation/proof root explicitly. A source merely reached
through an include can be available as a contract without its implementation
being checked; do not infer proof coverage from staging, hashes or an exit code.

1. Qualify the unchanged selected scope with the pinned native command. Record
   every raw CSV unit, fully qualified name, multiplicity, status, warning and
   resource outcome. Compare the direct command and harness on identical source,
   toolchain and bounds. Inventory existing axioms/externs and definitions that
   emit no proof unit; label these explicitly unlogged/trusted.
2. Verify both positive reference stages. Stage-one full scope must contain
   `ReadU16Frame`; stage two must retain all stage-one observations and contain
   `ReadContextEntry`. Exact emitted names and counts are currently UNKNOWN.
3. Only after positive feasibility, run distinct negative controls: unconditional
   failure, wrong payload/suffix, swapped key/value, omitted UTF8 checks,
   an unproved parent under a locally passing child, and a deliberately omitted
   stage-two root. Frontend errors do not count as expected mathematical failures.
4. Missing roots/units, changed protected sources, stale receipts and bypasses
   reject workspace acceptance even if the native command exits zero. A child's
   local success under an unproved parent contract never accepts the workspace.
5. Compile/run the fixed boundary examples if executable behavior is claimed,
   including empty key/value, short/truncated frames, invalid UTF8, a multibyte
   UTF8 key, and a nonempty remaining suffix. The examples in controls.json have
   not been executed. Do not call proof-only checks runtime tests.

Inherited trust matters. `MemoryMath` contains an axiom bounding values held in
memory; `SortedSets` contains external/axiomatized enumeration; UTF8 has external
Encode/Decode declarations. The new reader bodies avoid those calls, but an
included closure can retain inherited assumptions. Qualifying that closure does
not prove cryptographic implementations, platform externs or every AWS project.

## Intended report

For each actual model lineage, report returned response, guard/type/proof/resource
classification, stage acceptance, exact parent preservation, observed helper use,
native coverage and cost. Report blocked/unattempted children separately. Do not
select retries until a successful trajectory appears. This directory assigns no
call budget and opens no execution scope; root maintains the user's cumulative
ceiling and any separately frozen batch. Existing pilot scores, stopped ledgers
and reserved tree/transition families remain unchanged.

