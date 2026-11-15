# Compression fixed-point control results

Verifier-only job **60696022** completed on nonpreemptible `test` in **48 seconds**. All **20 expected outcomes** matched: four reference/alternative successes, twelve ordinary proof failures, two termination failures and two hidden-export resolution failures. Every positive workspace has zero errors/warnings and a strict zero exit. No model calls were used.

The protected provider proves that a compressed sequence is clean; the editable helper must inductively prove clean sequences are fixed points. The primary fault recurses before establishing the tail invariant and fails a precondition. Both correct proof orders pass. Missing boundary facts, omitted or wrong recursion, a bad base case, and a nondecreasing call are recorded separately. Clients use this helper to derive compression idempotence on direct and concatenated inputs.

The review checked exact source bytes, full named-lemma verification scope, immutable provider/client success, 130 protected-file comparisons and 30 helper-body boundaries. These are analyst-built development controls, not model results, an independent held-out family, or evidence of necessary proof depth. Separate mode requires two bodies and permits copying.

Evidence: [review](results-review.json), [complete source/stdout/stderr/CSV archive](verification-001/), [archive hashes](verification-001-sha256.json), [submission](submission-001.json), [accounting](accounting-60696022.txt), [stdout](verify-60696022.log), [stderr](verify-60696022.err), and [transfer inventory](transfer-001.json). The pre-verification fixture metadata remains unchanged. Reproduce the review using [../review_verification.py](../review_verification.py).
