# Corrected Dafny growth reference

Job **61753046** completed on November 18, 2026 with one CPU, one submission,
no requeue and the unchanged 100,000-resource/300-second native limits.
The native command exited **0** after **36.72 seconds**: **269 verified,
zero errors**, with exactly the three inherited upstream warnings.

All 267 original named units pass. The two added function well-formedness
units also pass: `RepoDiscoGrowthShift.MoveToFront` and
`RepoDiscoGrowthPick.PickPair`. No required or unexpected units are missing.
The native CSV reports these as well-formedness units; they are not method
correctness labels. The exact source/command/tool bindings and complete unit
inventory are in [reference-gate-dafny-001.json](reference-gate-dafny-001.json).

All 91 upstream files remain fixed. The two additions use the same contracts,
bodies, exports and decreases clauses as the preserved failed reference; only
the previously reviewed namespace/import lines changed. MoveToFront calls the
existing Swap and recurses. PickPair calls MoveToFront twice, using the adjusted
index for the remaining tail. This demonstrates the chosen compositional
reference, not that all valid solutions must use these calls.

The full 23-file transfer includes exact additions, source inventories,
stdout/stderr, CSV, resource use, tool evidence and accounting. Offline evidence
replay passes. Native CPU use was 94%, maximum RSS 644,556 KiB. The full Slurm
job took 48 seconds, used 73.4% of its one CPU and peaked at 683,844 KiB.
Native and full-job measurements are separate.

Original job 61747428 and its module-resolution failure remain unchanged in
`../qualification-001/`. The upstream trusted/unlogged definitions retain their
prior status; they are not additional logged passes. The historical model score
remains unchanged.

Together with the reviewed Vest reference, this supports preparation of the
remaining controls. It is analyst reference feasibility, not model-generated
growth or two sequential model acceptance events. The old edit policy still
binds the original Dafny namespaces and needs a separate compatible revision.
No model calls were made.
