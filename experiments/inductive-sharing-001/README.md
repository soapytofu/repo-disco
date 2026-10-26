# Inductive provider-proof sharing (verifier-only development)

**Current validated fixture: revision-003.** Job 55305635 passed all **16/16 intended outcomes** on shared in 42 seconds: six reference successes and ten intended proof failures. Original failed runs remain preserved below. No model calls. See [final verification review](revision-003/VERIFICATION.md).

Job **55304418 failed**: all six reference checks fail postcondition proof, while ten negatives have expected exit status. This fixture is **not ready for a model pilot**. Raw evidence and original source are preserved in verification-001; review-001.json records the failure. A deliberate revision with explicit base/unfolding facts is being verified separately. **No model calls.** Three offline design tests pass. Sixteen expected checks are fixed in checks.json; no verified-outcome claim is made until reviewed.

This family moves the missing proof into the provider. Total recursively sums an integer sequence. The target helper proves Total(s+t) = Total(s)+Total(t) by recursion on s. Automatic lemma induction is explicitly disabled in the protected signature, so the candidate must supply an appropriate proof step. The reference recursively calls on s[1..] and t, then establishes the slice-concatenation identity. Dafny still performs normal unfolding and SMT reasoning; this does not disable all proof automation.

Both clients are immutable. ClientA uses the helper to sum two sequences; ClientB composes two applications for three sequences. In shared both call AppendA, with one missing helper body. Separate contains AppendA and AppendB, with two missing bodies and ClientB bound to B. There is no unused B helper in shared: included-file verification would otherwise require proving it too and erase the intended synthesis-work difference.

This intentionally changes the number of helper proof bodies and provider source length. It is a proof-maintenance/synthesis comparison, not a perfectly length-matched context-only treatment. The duplicate helper proof can be copied, so do not assume separate is cognitively harder. Total and other infrastructure remain shared. The family is development material, not held-out after inspecting these references.

## Controls and evaluation

Six positive checks verify each reference repository and each client with included files. Ten negative checks cover empty helper bodies, deleting the recursive step, recursion with the wrong second argument, and a nondecreasing recursive call in each condition; separate also tests repairing only A or only B. Every negative is expected to fail proof verification, not parsing. In particular termination failures are valid proof failures but should be distinguished from postcondition failures in the review. Whole-repository verification includes provider obligations even when checking a single client; partial-helper failures must not be mislabeled as client-specific dependency evidence.

All includes, imports, definitions, attributes, signatures, pre/postconditions, decreases clauses and client bytes remain fixed within each condition. Only selected helper proof bodies vary. The existing call-only and branch-client guards are unsuitable: a future synthesis guard must protect all surrounding provider bytes, allow the specific recursive proof constructs, reject assumptions/axioms/verification-bypass attributes and verify the entire included repository. No model pilot or guard for this family is yet frozen or authorized.

## Revision history

Revision-002 (job 55305080) failed because my body-replacement generator left extra closing braces. This is an implementation bug, not a negative finding about inductive proof ability. All submitted bytes and diagnostics are preserved. Revision-003 uses balanced-brace spans to replace bodies in the original fixtures, checks brace balance plus unchanged signatures/clients, and is submitted separately as job 55305635. No model calls were made, and no reference-success claim is made while this correction is pending.
