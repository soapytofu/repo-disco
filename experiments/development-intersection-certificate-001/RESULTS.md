# Intersection or separation certificate: verified development task

**20/20 verifier-control expectations matched; zero model calls.** Job `60702410`
completed on the nonpreemptible `test` partition in 60 seconds. The original
README and runtime README remain pinned pre-run design records; this is the
current result.

| Controls across shared and separate workspaces | Expected | Observed |
| --- | ---: | ---: |
| Reference and alternative proofs | 4 strict passes | 4 |
| Empty or incorrect/incomplete proofs | 14 proof failures | 14 |
| Hidden direct-helper calls | 2 resolution failures | 2 |

Each successful workspace verified all 12 named units with zero errors and
warnings. Ordinary failures were confined to the editable `HelperA.Prove` and,
where applicable, `HelperB.Prove` bodies. Hidden `DirectWitness` calls produced
name-resolution failures, separately counted; no parse, warning-only or execution
failure was treated as an ordinary proof failure.

The task requires a certificate for every pair of nonempty closed integer
intervals: either a point in their intersection or a correctly oriented strict
separation. Touching endpoints must receive an overlap certificate. Reference and
alternative proofs use different branch orders and opposite endpoint choices.
Negative controls test touching-as-disjoint, an invalid witness, a reversed tag,
missing opaque membership/gap evidence and an unproved negative branch. The
immutable clients return ghost certificates; this is not executable search.

The [reproducible review](reviews/runtime-001/review-001/results-review.json)
checked 130 protected-file comparisons, 30 helper-body boundaries, 206 archived
input files and the complete 292-file raw evidence inventory. All 299 transferred
files matched their recorded hashes. Named provider and client obligations passed
for every non-frontend control. The complete [runtime and raw logs](runtime-001/)
include source snapshots, tool versions, stdout/stderr/base64, CSV, scheduler
accounting and the one-time submission record. The existing review logic is reused
through [a path adapter](review_verification.py); no source was reverified merely
to adapt the local review paths.

This implements the `D3-M1` positive/negative certificate obligation in a
fixed-interface repair form. It remains development material in the inspected
relational-witness ancestry. It does not complete four-cell corpus generation or
establish model difficulty, necessary proof depth, a causal sharing effect or
held-out performance. Shared mode has one editable body plus a forwarding helper;
separate mode has two copyable bodies. All earlier model scores remain unchanged.
