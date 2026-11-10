# Rejected pre-execution preparation draft

No model or verifier calls. The initial seven offline tests passed but tested a
handwritten fresh quantifier binder rather than the literal example in syntax.txt.
Review found that the displayed `forall k` example shadows the map task's `k`
parameter, so that example would be rejected by the existing body guard. This
unpublished draft is preserved for provenance and must not be dispatched.

The final proposal uses a fresh `key0` binder. The test now extracts the actual
inline statement examples from syntax.txt and parses each under every task's
registry. No task fixture, parser grammar, prior model result or verifier evidence
changed. `bundle/` is the rejected draft; use ../frozen-001 for the current proposal.
