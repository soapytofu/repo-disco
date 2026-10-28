# Sequence correction (revision 002)

Original job 56015268 exposed an out-of-range `s[1..]` in the definition of opaque
`StepReady`: `SplitReady` alone did not reveal nonemptiness. This revision adds
`|s| > 0 &&` before that predicate. Helper/client signatures, contracts, proof
bodies, exports and all other source bytes are unchanged.

Verifier-only job 56016216 on non-preemptible test reruns the 34 sequence controls,
no requeue and no model calls. Completed in 1m39s: all 34 expected outcomes reviewed (4 reference passes,
28 proof failures including 4 termination controls, 2 hidden-name failures).
Exact source hashes and diagnostics match the intended controls. The initial failed evidence stays
in the parent folder. build_revision.py reproduces the one-line change.
