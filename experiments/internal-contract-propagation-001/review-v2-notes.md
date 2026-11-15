# Named-scope review correction

The first reviewer correctly preserved the six strict successes and twelve proof
failures, but accepted named scope for only nine cases. It assumed every function
declaration produces a CSV unit. The arithmetic `Kernel.Endpoint` definition is
total integer arithmetic and a conditional, with no precondition or specification;
the actual pinned Dafny run logs only `Helper.Transfer` and `Client.Target` for
those nine workspaces. This was a reviewer coverage assumption failure, not an
additional mathematical failure.

`review_v2.py` reuses the complete immutable v1 source, raw-byte, manifest,
diagnostic and named-unit validation. `review-v2-scope.json` permits absence only
for `Kernel.Endpoint` in `capped_endpoint_return_migration`, with the exact
`Kernel.dfy` SHA-256
`4508c49460dcd0b728d9438545a35e3f772bf0409622b34154d06af940f0c4be`.
That definition is recorded as **unlogged**, never as a passed provider unit.
If an Endpoint unit is present, its outcome is checked normally. Both method
correctness units and all three map-provider declarations remain mandatory.

Six synthetic tests pass, covering the narrow exception, missing map or method
units, unexpected source/context, bad hash metadata, duplicate/malformed CSV and
an observed Endpoint failure. The unchanged all-logged synthetic archive also
retains its original interpretation.

The v2 offline review of the same job `60723362` accepts all 18 expected named
outcomes: six strict successes, eight client failures with a locally verified
helper, and four helper failures with a locally verified client under the assumed
helper contract. It checked 72 sources, 18 public prefixes, 36 body boundaries,
86 archived inputs and 165 raw archive files. There are nine observations of the
one unlogged definition and 27 passed logged map-provider units. No new verifier
or model calls occurred.

`review.py`, its tests and manifest, and `reviews/review-001` are preserved exactly.
`reviews/review-002/evidence-sha256.json` is byte-identical to the v1 evidence
inventory. The versioned correction does not change any source, contract, raw
verification result, model result or paid execution policy.
