# Alternative proof admission and semantics

Sixteen **analyst-authored** alternative candidates, one per current calibration
workspace. No model calls and no new task instances. Current contracts, clients,
providers and the output grammar are unchanged.

- Allocation selects the upper feasible endpoint: min(b, t-c), then conserves the total.
- Map swap handles equal keys explicitly; in deep distinct-key mode it observes only the relevant inner value for each query before observing the outer swap.
- Clamp handles upper/lower regions in reverse order and relies on the recovered facts without explicit input-order proof branches.
- Prefix splitting handles an empty suffix first, then an empty left prefix, and applies the recursive hypothesis before local unfolding facts.

Each synthetic JSON response passes the existing tolerant extraction and body
registry, producing the exact archived candidate bytes. Three offline test methods
pass, including protected boundaries and an isolated fake verifier process. The
16 actual compute checks completed as job **59355663** on nonpreemptible test in
52 seconds: **16/16 strict successes, zero errors and warnings**. Cannon also
passed all three offline tests. Exact-source review checked 120 protected files
and 24 body boundaries against the unchanged parent fixtures. Full responses,
extraction decisions, source archives, diagnostics and scheduler logs are saved;
see verification-001-review.json and readiness-review.json. Any failure will be retained separately;
these proofs cannot be counted as model successes or minimum-length solutions.
Prior model scores and the 126 current primary controls remain unchanged.
