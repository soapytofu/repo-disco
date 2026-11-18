# Remaining real-repository growth controls

This verifier-only package runs the **23 remaining analyst controls**, once each: 11 on Dafny-VMC and 12 on Vest. It preserves the exact overlays approved by the two source-bound reference gates. The completed `pair-reference` and `batch-reference` invocations have no dispatchable input here. There are no model prompts, paid transport, authorization, accepted model revisions or model calls.

The aggregate reference gate is copied as `reference-gates/aggregate.json`, SHA-256 `0999050882566d8630dec4566ed5526e05fbabcd9f4f1092c9c9322322a82207`. Its exact per-project gates and source catalogs are copied alongside it. `plan.json` fixes the order, each source overlay, the required and expected-observed native inventories, named outcomes and stopping rules. Prior experiments and their evidence are unchanged.

| Project | Remaining controls | Native cap per case | CPU / memory | Aggregate Slurm cap |
| --- | ---: | ---: | --- | ---: |
| Dafny-VMC | 11 | 300 seconds; 100,000 resource limit | 1 CPU / 2 GiB | 90 minutes |
| Vest | 12 | 900 seconds | 1 CPU / 4 GiB | 240 minutes |

These settings match the newly qualified growth references. The Dafny limit differs deliberately from the older 20,000-resource repair policy; no prior score changes and no future model policy is implied. Vest uses one Cargo build worker and one Verus thread, recorded as a concurrency change from the earlier qualification baseline. Native images, closures and baseline inventories remain pinned. `ops.py` confirms a live `test` or `shared` partition has `PreemptMode=OFF`, is up, and permits the complete aggregate wall bound before a single exclusive submission. Both scripts prohibit requeue.

## What the controls measure

Dafny checks reference/alternative stable moves, insufficient moves, a pair-selection alternative and insufficient pairs, a failed move parent with a passing pair caller, and an explicitly included versus omitted failing module. Every case retains all 267 original named units. Registered additions contribute the actual revised-namespace `MoveToFront` and, when applicable, `PickPair` well-formedness units. The detached control's correctness unit is required even when deliberately omitted from the native command.

Vest checks reference/alternative frame proofs, wrong headers and consumption, alternative/insufficient batch proofs, a failed frame parent with a passing batch caller, and omitted frame/batch modules. Every case retains the exact **5,410 original timed occurrences across 5,300 owning-crate/module/function/mode keys**, including repeated and externally named items. Frame registration adds its proof unit; batch registration adds the frame proof, batch proof and four recursive batch spec units. The six fixed frame spec definitions remain source-bound and explicitly unlogged; absence from a report is not a logged pass. An unregistered frame source receives its own unregistered label.

A matched negative requires the precise intended failed unit with all required providers and other named outcomes accounted for. Dafny's summary verified count must also agree with the passed CSV rows; a contradictory summary cannot match a negative. The unproved-parent controls specifically require a failed parent and a passing child; a child proved under an unproved contract never becomes whole-workspace success. An omission matches only when the native command otherwise passes its exact intended observed scope and the exact required target is absent. Unknown, extra, missing or multiplicity-changed units are retained as mismatches. Source and resource settings do not establish necessary proof dependence, minimum edits or model difficulty.

## Execution and evidence boundaries

Each case gets a fresh source checkout, output directory, intent, native invocation and—on Vest—a distinct empty Cargo target. The complete default Vest package command is forced for every case; cached Cargo success cannot substitute for the three required native crate reports. Source inventories and tool/image closures are checked before and after each invocation. stdout, stderr, resource output, CSV/JSON, exact overlays, commands, source hashes, environment, accounting and observations are retained. No parent repository is promoted or changed.

Well-classified proof failures, Rust/Dafny frontend failures and verifier-resource outcomes are retained and the next **distinct fixed case** may run. There is no retry or resume. Parser/integrity/execution exceptions halt. Negative process return codes, 124/137/143 and timeout flags halt before another invocation. The explicit ambiguous categories also halt: `ENVIRONMENT_OR_BUILD_ERROR`, `ENVIRONMENT_OR_SOLVER_ERROR`, `FRONTEND_OR_EXECUTION_ERROR`, `INCOMPLETE_OR_UNCLASSIFIED`, `NO_VERIFICATION_REPORT` and `UNCLASSIFIED`. The stopped record preserves the exact undispatched tail; no slots are reused.

Fetching requires the exact parent job and all relevant step rows to have explicitly allowed terminal states. Similar-prefix IDs cannot substitute for the parent. Before writing accounting or an archive, a read-only pass hashes and sizes every regular transfer file and rejects links/special files. Local free space must cover the uncompressed source bytes plus the greater of 64 MiB or 25% headroom. The single archive must match that exact estimate; an insufficient-space result changes neither endpoint. A changed transfer inventory fails before archive creation. This is a preflight, not a partial-fetch or retry mechanism.

`review.py` replays complete or explicitly stopped evidence. It binds both the project identity and exact execution/job/runtime/profile/raw/source records. An integrity-error or partial archive remains available for separate manual review rather than being reported as completed control evidence. Engineering expectation matches are not model-success counts.

## Preparation and provenance

`copy-provenance.json` records byte-identical sources; `adaptation-provenance.json` records the reviewed predecessors and the changed interfaces. Copied native readers and capture implementation remain unchanged. The tests use exact saved baseline inventories plus synthetic outcomes and fake transport; they provide no new mathematical evidence. They specifically cover the 26 Vest externally named occurrences under their owning reports, full-scope omissions, unproved parents, source mutation, stale/tampered records, exclusive case state, interruption/empty-report stopping and read-only disk checks.

`offline-review-001/replay-failure-001.json` preserves a focused preparation failure: Python tuple versus JSON array equality in Dafny replay. Canonical serialized comparison corrects it without changing the parser, any source fixture or prior result. The passing 31- and 33-test records are retained. `review-history-001` reconstructs the first preparation freeze before the narrow summary/CSV consistency correction; the final 34-test suite adds that regression. A manifest-only isolated preflight is required after the final freeze, then root independently reviews and publishes before staging. This file does not itself authorize a model study.
