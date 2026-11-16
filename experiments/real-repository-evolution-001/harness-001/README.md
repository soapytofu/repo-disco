# Source coverage and native-verifier agreement gate

This separate Dafny 4.11.0 adapter addresses the entry-only and exit-category
limits documented in [the prior review](../verifier-review-001/README.md).
It does not modify any historical experiment, generic wrapper or score.
No model client, credential handling or paid execution is included.

## Acceptance boundary

`dafny_gate.py` requires a host-reviewed profile that pins every declared source
byte, the include closure, toolchain, exact verification inputs, and the required
named correctness/well-formedness units. Every declared file is passed explicitly
to Dafny, even if the entry point omits it. Each file must either have named proof
targets or an explicit reviewed explanation for having none. An include-only
file is not reported as a verified proof unit. This is a reviewed scope inventory,
not automatic proof discovery from filenames or hashes.

The scorer rejects missing, duplicate, unknown or incomplete proof units, mixed
summary/CSV outcomes, stale source/profile/run identities and changed commands.
Both provider and client targets must pass. Warning-only verification is distinct
from parser, resolution/type, proof, timeout, resource and execution failures;
only complete verification with zero warnings and exit zero is strict success.
Unknown formats fail closed. Raw stdout/stderr/CSV and hashes remain available.

An edit policy must run **before** creating a candidate profile. The model cannot
supply or alter its profile, expected targets, command or source pins. Our pinned
method policy is copied here solely to test known contract/bypass attacks on the
existing migration fixture. It is not an edit policy for arbitrary real projects.
Exact candidate hashes prevent substitution after admission; hashing alone does
not establish valid contracts or defend against a malicious evidence producer.

## Controlled validation

Thirteen offline tests pass locally and in Cannon's Python environment. They
exercise actual protected-method policy rejection, omitted inputs/targets, changed
sources, stale evidence, missing/duplicate CSV units, warning classification,
fake-process timeouts and runtime capture. They do not invoke a proof engine.

The live comparison is now complete: **seven of seven paired cases agree**, and
the additional entry-only omitted-module pass is correctly rejected as full-scope
evidence. Job61247644 made 15 native invocations with zero model calls. Full results
and scope limits are recorded in [RESULTS.md](RESULTS.md).

The frozen verifier-only job compares seven scopes through two independent
staging/invocation paths: direct native CLI and the adapter. The same Dafny/Z3
versions, source bytes and effective arguments are used. This compares integration,
not independent theorem provers. Cases cover a correct workspace, failed helper
with passing client, failed client with passing helper, omitted failing module,
warning-only output, parser failure and unresolved-member failure.

The omitted-module control also runs the entry-only native command once. Its
expected pass must be rejected as full-scope evidence, while explicit all-file
verification must find `Detached.Broken`. There are **15 native invocations**,
not model trials; no retries or requeue. All exact control sources, lineage,
deliberate mutations and expected categories are in `controls.json` and the
fixture manifest. A known saved warning candidate is reused without editing it
or altering its historical score.

Each invocation records wall time, GNU time's maximum resident-set-size metric, named
unit duration/resource counts, timeout/completion status, raw streams and source
bytes. Slurm accounting is archived separately. Resource counts are solver work
metrics, not CPU seconds; the memory metric is not summed concurrent process-tree
memory. No performance benchmark or runtime-stability estimate
is inferred from one observation per path. Timeout/resource categories are tested
with fake processes; this control job does not intentionally exhaust the cluster.

`runtime-manifest.json` and `fixture-manifest.json` are frozen before submission.
`compute_ops.py` uses exclusive submission/output locks, bounded SSH calls and a
live nonpreemptible-partition check. The initial read-only remote inspection used
an unsupported `text=True` keyword on system Python 3.6; it failed before staging
or submission. The corrected inspection used `universal_newlines=True`; no job
or verifier invocation was repeated. The actual worker uses the repodisco environment.

## Required real-project qualification

No online repository is qualified by these constructed controls. The current
adapter rejects other toolchain versions and Verus, and supports only the
reviewed simple include syntax. It does not cover project configuration files,
preverified libraries, build features or Verus crate scopes. Those need explicit
versioned adapters, not a relaxed success predicate.

For **each pinned real repository/component**, before any model collection:

1. Reproduce its native baseline and declared dependency proof scope; inventory
   axioms, extern/trusted files, termination exemptions and configuration.
2. Adapt the profile/scorer to that exact toolchain and source scope. Compare the
   native and harness results on original/correct/broken candidates, an omitted
   failing dependency, and a client passing under an unproved helper contract.
3. Validate its edit guard against contract/configuration/bypass changes and
   source substitution. Reject missing, stale, partial or unexplained evidence.
4. Publish the complete controls, raw evidence, qualification decision and runtime
   measurements. Require zero unexplained disagreements or false acceptance on
   this finite control set. Bind that qualification to any future frozen runner.

Verifier-only baseline/qualification runs on the real sources are necessary to
establish this gate; model evaluation waits until they pass. A later toolchain,
scope, policy or scoring change invalidates the corresponding qualification.
The four shortlisted projects remain unqualified, with zero new model calls
authorized. These controls cannot certify Dafny/Verus soundness or eliminate all
possible harness bugs.

See `RESULTS.md` for the actual compute outcome and any versioned review correction.
