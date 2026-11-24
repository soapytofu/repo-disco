# Fresh eight-call runner preparation

**Collection completed:** job 63440248 returned all eight responses; **3/8
accepted, four frontend failures and one solver-resource failure**, with zero
SDK retries. See [final results and full logs](COLLECTION.md). The preparation
checkpoint below is retained; its tests preceded the live collection.

The new prospective frontend policy is reviewed and frozen. **113/113 tests
pass locally, in the manifest-only isolated package and on Cannon**. Both actual
frozen-payload eight-slot simulations pass using only synthetic transports and
native observations. Full logs and receipts are in `reviews/`. The independent
15-test policy review also replays the original splice evidence exactly: it
would remain unaccepted and allow continuation under the new rule. The old
terminal score/ledger and every original payload remain unchanged.

Runtime SHA: `fbc37c8b30095998870ac6c40cc08c9974cdeb89e52d522ce906b41c3cb1310f`
(63 files). Four tasks, two fresh independent responses each, same forward/reverse
order, same model settings, same guards and native proof limits. Source/inventory,
provider, infrastructure and ambiguous failures remain stopping conditions.

The fresh eight-slot allocation raises the session ceiling allocated to 44/100,
leaving 56 unallocated. All four old allocations and their 14 closed unused slots
remain unchanged. User approval is recorded. The exact package is staged and
Cannon fake-process/import/smoke preflight passed without provider calls, native
verifier calls or private-handoff reads. No model request had run at this
preparation checkpoint. Collection results will be recorded separately.

See [scope](scope.json), [runtime freeze](runtime-freeze.json),
[preparation audit](preparation-review-001.json), [Cannon preflight](preflight-001.json),
[policy review](reviews/frontend-policy-review-001/README.md) and
[unchanged earlier results](../execution-001/COLLECTION.md).
