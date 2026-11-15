# Exact-gap witness: verifier controls

Verifier-only job **60696260** completed on nonpreemptible `test` in **59 seconds**. All **20 expected checks** matched: four strict reference/alternative passes, fourteen ordinary proof failures and two hidden-export resolution failures. Positive candidates have zero errors and warnings. No model calls were used.

The source and diagnostic review confirms that the intended faulty proof fails, both constructive alternatives pass, and targeted missing-fact or incorrect-value controls fail at proof level. Hidden exports are reported separately as name-resolution failures. All named provider/client obligations remain verified in the proof-level negative checks; failed helper contracts prevent a whole-workspace success. Full exact source, raw stdout/stderr bytes, CSV, toolchain versions and scheduler records are preserved.

The review checked 130 protected-file comparisons and 30 helper-body boundaries. These are analyst-constructed development tasks, not new model outcomes or a causal sharing/minimum-depth finding. Separate mode requires two copyable bodies. The original fixture metadata remains unchanged as the pre-verification design record.

Evidence: [review](results-review.json), [complete raw archive](verification-001/), [hash inventory](verification-001-sha256.json), [submission](submission-001.json), [accounting](accounting-60696260.txt), [stdout](verify-60696260.log), [stderr](verify-60696260.err), and [transfer inventory](transfer-001.json). Review using [../review_verification.py](../review_verification.py).
