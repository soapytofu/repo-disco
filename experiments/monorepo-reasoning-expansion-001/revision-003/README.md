# Explicit reverse-concatenation reference proof

The first semantic run passed 20/24 reference workspaces and all 24 expected
empty-proof failures. Four reverse-concatenation references failed their final
assertion; all original bytes and diagnostics remain in runtime-002.

This deliberate revision adds explicit base identities, the induction equality,
one-step equations and sequence concatenation reassociation to the reverse helper
bodies. It changes no providers, clients, helper declarations/contracts, decreases
clauses, or empty seed bytes. All other semantic instances are byte-identical.
The assertions also localize any remaining proof failure; this is not yet evidence
that the correction verifies or that reassociation was the only missing step.

Eleven offline tests pass: six construction invariants, two isolated-runtime tests,
and three revision tests for exact change scope, reusable prior evidence, and
byte-exact output-guard reconstruction of all 24 references. See offline-tests.log.
Revision tests need the archived sibling runtime-002 and parent protocol directory.

Only the four changed references will be verified in the first phase. The 44
unchanged outcomes (20 successful references and 24 empty-proof failures) are
reusable only because their nine source hashes match this revision exactly.
No previous outcome is rescored or replaced. After the four revised references
pass review, the distinct 116 targeted-negative cases may run once. No model
calls, automatic retries, or future model pilot authorization.

Submitted once as **57111126** on live-confirmed nonpreemptible shared, with no
requeue. The four revised references are pending; all previous evidence stays intact.

## Reviewed reference gate passed

Job 57111126 completed in 1m50s on holy7c04102 (shared): all four revised reference
workspaces verified, each reporting 11 verified and 0 errors. Their raw sources,
stdout/stderr, commands, source hashes and runtime manifest were reviewed and
archived under verification-001. No model calls.

`review_reference_gate.py` combines these four outcomes with the 44 previously
reviewed outcomes whose source bytes exactly match this revision. The resulting
reference-gate.json records 24 reference successes and 24 expected empty-proof
failures, with evidence paths, job IDs, artifact hashes and reuse flags. Reuse
creates no new independent trials. It also does not erase the prior four failures.

The distinct 116 targeted-negative controls were submitted ONCE as **57112358**
on nonpreemptible shared. The submission binds the reviewed reference-gate hash;
output is verification-002. Those outcomes are pending.
