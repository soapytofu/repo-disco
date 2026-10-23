# Matched reference-sharing control

**Completed October 23, 2026: all 22 checks matched expectations.** Zero model calls. User-authorized rerun 54811436 completed on `shared` in 68 seconds (exit 0:0, compute node holy7c04301). [Full check table](VERIFICATION.md) · [Raw rerun evidence](verification-002/) · [Summary](verification-002/summary.json).

The original job 54811286 was preempted after 10 checks; its partial evidence remains in `verification-001/`. No original logs were overwritten. The rerun used a fresh directory and completed without retries or requeue.

This follows shared-proof-001 with a tightly matched *reference proof* control. Both conditions have identical provider source containing two equivalent exported lemmas, `ConcatFactA` and `ConcatFactB`. The shared reference calls A in both client proofs; the separate reference calls A in ClientA and B in ClientB. Conditions differ in exactly one same-length helper name at one call site. Modules, contracts, provider definitions, and source byte counts match. Model tokenizer counts have not been measured.

The 22 verifier checks test references, weakening A's guarantee, and weakening B's guarantee for each condition. Clients are verified separately and jointly; each weakened provider is also verified independently. Verified outcomes:

| Condition / mutation | ClientA | ClientB |
| --- | --- | --- |
| Shared / reference | Pass | Pass |
| Separate / reference | Pass | Pass |
| Shared / weaken A | Proof failure | Proof failure |
| Shared / weaken B | Pass | Pass |
| Separate / weaken A | Proof failure | Pass |
| Separate / weaken B | Pass | Proof failure |

The aggregate must fail when either client fails. All weakened providers must still verify. A failure must be a proof error, not a parser or name-resolution error. The runner snapshots all input and raw diagnostics and refuses to run on a login node.

## What this control can and cannot show

This isolates the dependency footprint of the *fixed reference calls* while matching source size. Because both helper contracts are equivalent and visible in both conditions, a future model could choose either helper for either client. It therefore does **not** establish an unavoidable shared-versus-unshared reasoning treatment, and should not be presented as a ready model benchmark or proof of a causal effect on completion rate.

A future comparison must explicitly decide whether reuse is an observed outcome (allow either valid helper and measure chosen reuse), or a constrained treatment (restrict exports or allowed calls, documenting the additional API difference). Do not quietly conflate these designs. Shared-proof-001 remains the simpler verified example of both reference clients depending on a single exported lemma.

Three offline tests check exact condition matching, mutation isolation, and the expected 22-check matrix. Reproduce with `python3 experiments/sharing-control-001/test_matching.py`. No credentials or model SDKs are used.

### Scheduling adjustment

At the user’s request, pending job 54811436 was updated in place to allow either `shared` or `sapphire`, both confirmed live with `PreemptMode=OFF`. Its requested wall time was shortened from 20 to 10 minutes (the earlier 16-check task took 49 seconds); 2 CPUs and 8 GB RAM remain unchanged. No duplicate job was submitted. The original submission script is preserved; `status.json` records the scheduler override. This can improve scheduling opportunities but does not guarantee a start time.

## Evidence review

All 22 recorded exit codes matched the predeclared matrix. Every negative result was a postcondition proof failure, not a name-resolution or parse error. Both weakened providers verify independently. All compute-node fixture bytes match the published fixtures, all recorded source hashes match, and verifier stderr is empty for all checks. The three offline matching tests also pass. These findings establish the different dependency footprints of the fixed reference proofs; the equivalent-helper caveat above still applies.
