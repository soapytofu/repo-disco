# Pipeline task validation

**All 45 verifier-control expectations matched; no model requests for this study
yet.** These results validate four development workspaces before the proposed
32-call repair comparison. They are not model performance results.

| Group | Strict positive controls | Ordinary proof failures | Hidden-export resolution failures | Job |
| --- | ---: | ---: | ---: | --- |
| Witness pipelines | 6 | 16 | 2 | `60708384`, test, 74 seconds |
| Map pipelines | 4 | 15 | 2 | `60707245`, test, 64 seconds |

Both jobs used a live-confirmed nonpreemptible partition, one submission and no
requeue/retry. Every positive workspace verified with zero errors and warnings.
The four reference scopes contain 12, 12, 17 and 21 named units, respectively.
All ordinary negative outcomes were proof failures confined to eligible helpers;
no parse, warning-only or infrastructure failure counted as one.

The initial intersection and inverse-map faults fail `HelperB.Prove`; the
conserved-sum and composition faults fail `HelperA.Prove`. The other helper and
both client units pass locally, conditional on supplied lemma contracts. Neither
client is certified under the frozen declared dependency closure while its helper
chain fails. This does not mean the client theorem is mathematically false, nor
does the declared graph establish necessary proof dependence.

Controls that repair only one module confirm the intended fault location. Four
map controls produce bytes identical to canonical reference/faulty cases and
therefore reuse explicitly linked evidence, with **no extra verification calls or
independent-observation count**. Witness one-module controls use distinct valid
alternative bodies; all 24 witness workspaces are distinct.

The [maps review](reviews/maps/review-001/results-review.json) and
[witness review](reviews/witness/review-001/results-review.json) check 269 protected
file comparisons, 90 body boundaries, 430 archived input copies and 622 raw inventory
files. All 636 transferred files match their hashes. Named reference scopes,
source hashes, raw stdout/stderr/base64, CSV, tool versions, accounting and
submission records are saved under [maps](maps/) and [witness](witness/).

The separate [per-file output policy](protocol/) reconstructs 41 admissible control
workspaces exactly (82 bodies) and rejects four hidden-call controls. Eighteen
offline policy tests and three compatibility tests against the unchanged live
runner pass. Its new policy identity/hash is distinct from the retained adapter
ABI version. All imports, signatures, contracts, providers and clients remain
protected; no particular reference proof or helper-call order is required.

The exact [32-trial prompt/order/source freeze](pilot/) and independent request
audit are complete. A single data admission through the existing 128-call window
ledger remains pending. The earlier 32 model calls remain
unchanged, with 96 available. This study offers two eligible proof bodies and
mostly localized seeded defects, not unrestricted file discovery or demonstrated
large-repository scaling. It does not estimate a causal sharing/depth effect or
held-out performance. Reserved tree/transition families remain untouched.
