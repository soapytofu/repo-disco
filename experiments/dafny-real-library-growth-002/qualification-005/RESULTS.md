# Shift-based splice reference exceeds the fixed resource budget

Job **63168106** completed its single verifier observation. Splice's correctness
unit exhausted the **1,000,000 resource limit** (CSV resource count 1,037,148).
The other 59 native units pass, including all 58 inherited units. The native
summary has zero ordinary proof errors and one out-of-resource result; this is
**RESOURCE_FAILURE**, not success. There are no warnings or outer timeouts.

The full 56-file archive contains the exact source, CSV, stdout/stderr, versions,
resources and terminal accounting. The original expected PROOF_PASS and actual
failure remain preserved. No model request occurred.

Before model collection, the already-constructed `splice-alternative` will be
checked once under the same contracts, tools and resource limit. It snapshots
the array, clears it and appends the specified result. If successful, it can
establish task solvability without requiring the shift-based implementation.
The failed shifting reference will remain separate historical qualification
evidence; it will not be rerun, relabeled as passing or included as a passing
control. The fixed resource policy is unchanged.
