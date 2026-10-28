# Baseline smoke-001 specification audit

Manual review of every applied source diff, with all original results preserved.
This audit assesses preservation of the supplied specification, not completeness
of that specification relative to the program name or natural-language intent.

| Trials | Review |
| --- | --- |
| 01 | Adds loop invariants and removes redundant `requires a != null` for non-null `array<int>`. Postconditions and executable code unchanged; semantically redundant contract cleanup, not byte-identical contract preservation. Strict exit 0. |
| 02, 07, 14, 20 | Adds loop invariants only; supplied contracts and executable code unchanged. Strict exit 0. |
| 08 | Adds termination measure only; supplied contracts and executable code unchanged. Strict exit 0. Original merge-sort code has no sortedness/permutation postcondition: this does not prove sorting correctness. |
| 03 | Adds invariants only; supplied contracts and executable code unchanged. Dafny reports two verified, zero errors, but exits 2 because the original redundant non-null comparison triggers a warning. Legacy success; not strict exit success. |
| 04 | Reconstructs malformed annotations and adds proof/termination annotations; still two proof errors. No success claim. |
| 10 | Removes an extra closing brace; still five proof errors. No success claim. |
| 15 | Empty effective patch, source unchanged; front-end errors remain. |
| 17 | Changes a helper postcondition to a different formulation and adds a recursive proof. Still two proof errors; not a contract-preserving annotation success. No equivalence claim. |
| 05, 06, 09, 11, 12, 13, 16, 18, 19 | Patch rejected before verification. No accepted candidate. |

All seven legacy-positive candidates were inspected in full. No new assumption,
axiom, verification-disable attribute, weakened postcondition, or executable-code
change occurs in those seven. Six exit zero, including trial 01's redundant
precondition cleanup; five exit zero while leaving declaration contracts unchanged.
Trial 20's inherited contract only lower-bounds the sum of common divisors; it does
not specify the exact sum. These limitations must remain visible in any summary.

The baseline's coarse FRONTEND_ERROR category for exit 2 conflates warning-only
rejection (03) with actual front-end errors (15); raw diagnostics are authoritative.
No candidate has been silently repaired, rerun, or rescored in the original logs.
