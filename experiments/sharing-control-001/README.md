# Matched reference-sharing control

October 23, 2026. Verifier-only fixture development, zero model calls. Job 54811286 was **preempted** on Cannon serial_requeue with automatic requeue disabled. 10 of 22 checks completed and all matched expectations; the full matrix is **not yet verified**. Partial evidence is preserved in `verification-001/` and the batch logs. No retry was submitted. Do not treat the expected matrix below as completed findings.

This follows shared-proof-001 with a tightly matched *reference proof* control. Both conditions have identical provider source containing two equivalent exported lemmas, `ConcatFactA` and `ConcatFactB`. The shared reference calls A in both client proofs; the separate reference calls A in ClientA and B in ClientB. Conditions differ in exactly one same-length helper name at one call site. Modules, contracts, provider definitions, and source byte counts match. Model tokenizer counts have not been measured.

The 22 verifier checks test references, weakening A's guarantee, and weakening B's guarantee for each condition. Clients are verified separately and jointly; each weakened provider is also verified independently. Expected outcomes:

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
