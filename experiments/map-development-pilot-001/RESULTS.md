# Map development: interrupted 16-call cohort

November 12, 2026. Job **60045391** stopped after **10 dispatches**, in 3m16s on
nonpreemptible test. Request 10 raised `ServiceUnavailableException`; its ledger
entry is ambiguous/unsaved, with no saved response, request ID or token usage.
The runner closed and made no retry or replacement. **Six planned slots remain
undispatched; this is not a completed 16-call study.**

Nine returned responses have unique provider IDs and zero reported SDK retries:
**six strict passes, two proof failures, one body-policy rejection**. All nine
JSON envelopes extracted; eight candidates reached Dafny. Recorded usage for those
nine is 31,786 input + 5,072 output = **36,858 tokens**. Failed-request usage is
unknown; do not infer it was free or never reached the provider.

| Instance | Interface | Sharing | Returned / planned | Strict passes | Other evidence |
| --- | --- | --- | ---: | ---: | --- |
| Fresh move | Shallow | Shared | 1/2 | 1 | One slot undispatched |
| Fresh move | Shallow | Separate | 1/2 | 1 | One slot undispatched |
| Fresh move | Deep | Shared | 1/2 | 1 | One slot undispatched |
| Fresh move | Deep | Separate | 1/2 | 1 | Second dispatch has service error |
| Restriction/merge | Shallow | Shared | 1/2 | 1 | One slot undispatched |
| Restriction/merge | Shallow | Separate | 1/2 | 1 | One slot undispatched |
| Restriction/merge | Deep | Shared | 2/2 | 0 | One policy rejection; one precondition failure |
| Restriction/merge | Deep | Separate | 1/2 | 0 | One precondition failure; one slot undispatched |

## What was observed

All four returned fresh-move responses strictly verify, including deep-interface
proofs that explicitly recover intermediate values and establish fresh-key
membership. These are four observed cells, not eight completed trials.

Restriction responses 08 and 09 call
`Certify(Restrict(m,keep), Restrict(n,keep))` **before** the two
`RestrictKeys` calls. The certificate requires disjoint restricted domains,
which are not yet established at that point. The verifier reports only that
precondition failure: both editable helpers in separate response 08 and HelperA
in shared response 09. Reordering is a proposed analyst diagnostic, not an
automatic repair or change to either model score.

Response 04 is rejected at the second `ensures` in its `forall` proof block.
The frozen bounded grammar permits one postcondition expression there; it
successfully admits quantified Boolean assertions in other responses. The
rejected candidate was **not verified**, so this outcome alone establishes no
mathematical success or failure. Its early certificate call has the same visible
ordering pattern, which remains unverified for this response.

All four returned separate responses copy identical helper bodies. There is no
independent discovery-of-reuse result.

## Target-level findings and fidelity

The eight admitted candidates have valid per-declaration CSV evidence. In the
six accepted workspaces, every editable helper and both dependent clients verify.
In the two proof failures, editable completion is 0/2 and 0/1 respectively,
and dependency-closed client completion is 0/2 in both.

Both supplied clients still verify **locally** against declared contracts in all
eight candidates. That is conditional modular verification, not model-completed
work or accepted whole-repository correctness. No partial editable-helper success
with whole-workspace failure was observed in this small batch. Consequently,
these results do not yet support the proposal's local-versus-global degradation
hypothesis.

Review replayed every returned edit and inspected all admitted proofs. It checked
**60 protected-file comparisons and 12 body boundaries**, including imports,
exports, signatures, contracts and fixed clients. The explicit `assert false`
branch in response 05 is proved unreachable under the domain facts; it is not an
assumption or verifier bypass. No admitted candidate produced warnings or parse
errors. Every source hash, request payload/order, runtime pin and all 653
transferred archive files matched. Original experiments/scores remain unchanged.

## Interpretation and next work

This supplies a concrete prerequisite-ordering failure on a distinct map
operation, while fresh-move composition succeeds in the observed cells. It is
useful mechanism evidence, not a reliable overall success-rate estimate or a
causal depth/sharing result: the cohort is incomplete, only two map instances are
included, and editable workload differs by sharing condition.

Preserve this partial cohort intact. A separately archived, verifier-only
reordering diagnostic can test sufficiency without more model calls. Any later
collection requires reconciliation and a separately explicit scope; the stopped
runner cannot resume, retry request 10 or silently reassign its unused slots.

## Full evidence

- [Independent request/source/metric review](results-review.json) and
  [manual source audit](source-audit.json).
- [Full raw archive](model-001/): request ledger, exact prompts, provider responses,
  candidates, guarded edits, CSV logs, stdout/stderr, accepted records, authorization,
  code/settings and environment.
- [Transfer hashes](transfer-001.json), [archive hashes](model-001-sha256.json),
  [Slurm accounting](accounting-60045391.txt), job stdout/stderr and submission
  evidence are retained alongside the archive.
- `python3 -B review_results.py` reproduces the saved-evidence review without
  a model or verifier call. It explicitly reports `all_completed: false`.
