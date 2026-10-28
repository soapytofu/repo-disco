# Matched corpus planning record

**No model requests authorized. All 16 calibration variants are verified and the 32-trial proposal is frozen.**

The [Weeks 5–6 plan](../../docs/weeks5-6-corpus-plan.md) defines the matching policy,
family split, validity gates, analysis and budget. plan.json records checked counts.
Recommended: 32 calibration calls, then 192 main calls only after review (**224
proposed total**, no execution authorization). The main set contains 24 semantic
instances, 96 structural variants and 192 attempted trajectories, not 192 unrelated
problems. Accepted/deduplicated corpus size remains unknown.

Calibration guards and prompts are complete; the larger main corpus remains unbuilt and gated on calibration review.
This record does not change any prior frozen experiment or reuse an old budget.

Scope is now explicitly cross-module reasoning within one monorepo workspace.
The [calibration archive](../monorepo-calibration-001/README.md) now has sixteen
variants, 118 selected expected verifier outcomes, tested guards and exact frozen
32-trial prompts/order/settings. An initial sequence-fixture failure is preserved
alongside the corrected, verified revision. Model-call estimates are unchanged;
none of these preparation steps made model calls.
