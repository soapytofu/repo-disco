# Fresh growth cohort under bounded resource-outcome policy

Job **63033780** was submitted once on November 23, 2026 and started at
04:20:15 Eastern on nonpreemptible `shared`, node holy7c24304. It uses one CPU,
8 GB and a four-hour limit, with no requeue or restarts. Collection and native
verification are **in progress**; no complete-cohort score is reported yet.

The fresh allocation is at most eight model calls under Sophie's approved
100-new-call ceiling. There are two independent lineages each for Dafny-VMC and
Vest, at most two additions per lineage, one response per stage, no retries or
slot reassignment. A failed parent blocks its child. The second prompt requires
the actual accepted parent source and native evidence. Other independent
lineages continue after a fully audited bounded Dafny resource failure; missing
or ambiguous evidence still stops dispatch. Frozen prompts and acceptance
requirements are unchanged.

[Human approval and readiness](approval-receipt-001.json),
[hash-bound authorization](authorization.json),
[fresh pre-submission inspection](pre-submit-inspection-001.json),
[single submission receipt](submissions/model.json), and
[initial scheduler state](job-inspection-001.json) are preserved. Inspection
matched all 4,189 inputs, both container images and 287 Dafny/3,873 Vest tool
files. The handoff was checked by metadata only before the authorized runner
loads it; its contents are never logged or published.

[Budget snapshot 003](../research-budget-20261123-003.json) allocates 16 slots in
total across the two new cohorts, with 84 still unallocated. Before this run,
there was one returned request in the earlier closed allocation; its seven
unused slots remain closed. The earlier incorrect MoveToFront result stays
visible in [execution-004](../execution-004/COLLECTION.md). This is a fresh
cohort under a changed stopping policy, not recovery of that ledger or a retry
of its candidate.

After terminal completion, report every attempted stage, blocked child, request
ID and SDK retry count, all exact candidate/parent hashes, the full named native
inventories and warning/resource categories, and full raw logs. Give a complete
four-lineage metric only for a fully accounted collection; keep any partial
cohort distinct. No positive score is selected or inferred while the job runs.
