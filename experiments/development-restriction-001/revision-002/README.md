# Explicit finite-domain correction

November 12, 2026. Core job **60035065** passed all eight expected outcomes in
43 seconds: four reference workspaces strictly verify 20 obligations with zero
errors/warnings; four empty-helper workspaces fail only their helper
postconditions. The 30 targeted controls also matched all expected outcomes on
job 60035790 in 2m11s: 26 proof failures and four hidden-export resolution errors.
**All 38 current expectations matched**, with no warnings or parse errors.
Zero model calls. [Detailed results](../RESULTS.md).

The sole Dafny source change from the preserved failed original is:

```diff
- map q | q in m || q in n :: if q in m then m[q] else n[q]
+ map q | q in m.Keys + n.Keys :: if q in m then m[q] else n[q]
```

This gives the frontend an explicit finite set bound. The mathematical domain is
the same union. Every other source file, including helper proofs, signatures,
contracts, clients and exports, has exactly the same bytes for each control.
[source-correction.json](source-correction.json) and
[parent-checks.json](parent-checks.json) pin that comparison. Nine offline methods
passed locally and on Cannon, including the source-change audit. All eight core
checks were rerun because the kernel bytes changed; no old failure was reused as
a success. The original version remains in the parent directory with full logs.

The current inputs and runtime are pinned by `manifest.json`. The experiment
scope and limitations in the [parent README](../README.md) still apply: one
development instance, four structural cells, copyable separate proofs, no measured
model difficulty or minimum-depth claim. Both phases and exact source hashes are
reviewed; their full input/output/scheduler archives are retained here.
