# Cross-module monorepo calibration: first family

**Verifier-only construction; zero model requests.** This implements the clarified
[Weeks 5–6 monorepo scope](../../docs/weeks5-6-corpus-plan.md): one workspace with
trusted provider stages, editable helper proofs and two immutable clients.

Four conditional variants are constructed: shallow/deep × shared/separate. The
helper establishes safety after dependent normalization/reflection of two inputs.
A four-way branch must supply correctly normalized arguments to visible contracts.
Shallow mode exposes a direct provider rule; deep mode exposes a three-stage
prerequisite chain and hides the direct rule. All task files live in the same
monorepo snapshot, with no cross-repository dependency management.

Shared mode edits HelperA.Prove only; fixed HelperB forwards to it. Separate mode
edits both independent helper proofs. Two clients, provider sources and target
contracts are identical across conditions. Matching differences (source bytes,
editable-body counts, the shared forwarding edge, and import depth) are explicit
in matching-audit.json. The depth label refers to provider contract composition
inside the target helper, not total import depth or provably minimal proof length.

build_conditional.py generates sources, tasks.json and checks.json. Four offline
design tests passed, checking exact generation, immutable client/spec matching,
import/include-map integrity and targeted negative mutations. preflight.py checks
all source hashes before running Dafny with --verify-included-files on compute.
It imports no model client and accesses no credentials.

Verifier-only job **55978267** was submitted once on test (PreemptMode=OFF),
2 CPUs/8GiB/30 minutes, no requeue. **26 expected outcomes:** four reference
successes, twenty proof failures, two name-resolution failures for hidden Direct.
All expected outcomes matched; full reviewed evidence is retained below.

This starts **4 of 16 calibration variants**. The sequence-induction, relational
join and finite-map families remain to build. Candidate-output guards and exact
32-call prompt freeze are not ready, and no model calls are authorized.

## Reviewed verifier results

Job 55978267 completed on test in **1m14s**, exit 0. All **26 expected outcomes**
matched: four references verified, twenty negative controls failed proof checking,
and two hidden-shortcut controls failed name resolution. No parse errors occurred.
These are verifier controls, not model-performance results. No API calls occurred.

The archive includes exact fixture bytes, runner/backend hashes, every raw
stdout/stderr record and environment/submission logs. review_results.py checks
all archived fixture hashes against the staged manifest and live source copies,
client/provider immutability, expected exit codes and diagnostic categories.
results-review.json and verification-001-sha256.json record the review. The offline
review matcher was corrected from an assumed “does not exist” phrase to the actual
“unresolved identifier: Direct”; source and verifier evidence were not changed or
rerun. The original preflight matcher had accepted the actual diagnostic correctly.

The four references establish fixture validity. They do not establish how often
models solve these tasks or that no shorter proof exists. Guards must prohibit
revealing opaque trusted definitions or accessing internal imports before model
trials are allowed. Three other calibration families, final guards and prompt
freezing remain open; the proposed 32-call calibration is still unauthorized.
