# Four varied development calibration tasks

**Complete: 126/126 current verifier controls matched. Zero model calls.**

See [RESULTS.md](RESULTS.md) for the final table, evidence lineage and limits.
Use [revision-002](revision-002/README.md) for current fixtures; the root fixtures
and first 32-check archive are preserved history. These implement the four C1
proposals in [the active corpus plan](../../docs/corpus-family-split-plan.md).
All reserved tree/transition-family tasks remain untouched.

| Task | Semantic target | Interface contrast |
| --- | --- | --- |
| D3-C1 bounded allocation | Choose two bounded integers with a fixed total | Direct numeric witness certificate versus bounds/join/balance certificates |
| D4-C1 map swap | Swapping present keys twice restores the map, including aliasing | Whole-map observation versus domain and individual-value observations |
| D1-C1 clamp distance | Clamping cannot increase the distance between two inputs | Guarded value facts versus opaque region certificates followed by value recovery |
| D2-C1 prefix split | Split a bounded prefix aggregate across a sequence slice | Direct prefix unfolding versus an opaque step fact followed by exposure, plus explicit induction |

Each task has shallow/deep × shared/separate variants (16 workspaces). Shared mode
has one editable helper plus a fixed forwarding helper; separate mode has two
copyable helper bodies. Both modes use the same protected providers, clients and
contracts within each task. The wrapper changes graph depth and output workload;
this is not an equal-work cognition comparison. Numerical minimum proof depth is
unknown. The interface labels describe reference-relative factorization, pending
verifier and ablation review.

The original construction had 124 controls. Current revision 002 has **126**:
16 reference successes, 90 ordinary proof failures, four termination failures and
16 hidden-export resolution failures. All matched, with no parse errors or
warnings. Current results combine 24 unchanged original core observations,
eight revised map core observations and 94 targeted negatives. Eight superseded
original map core checks remain preserved; 134 actual verifier invocations total.

Nine construction/revision tests passed locally and on Cannon. A separate
[output compatibility policy](protocol/README.md) adds only task registries to the
existing bounded parser and reuses the exact tolerant JSON envelope. Eight
additional offline tests reconstruct 110 bodies exactly and reject all 16 hidden
export attempts. No model responses or paid prompt freeze are claimed here.

Verification is restricted to compute nodes, with live-confirmed nonpreemptible
`test`, exact Dafny 4.11.0/Z3 4.12.1, `--verify-included-files`, strict warnings and
one verifier invocation per control. The bounded SSH tools use the user-created
socket `repodisco-codex-12.sock`; no API key is needed or accessed.

All three jobs are complete and reviewed: 59351309 (original core), 59352546
(revised map core), 59352900 (targeted negatives). The map revision introduces an
opaque domain prerequisite after a reference-depth audit. Earlier evidence is
unchanged. [current-evidence.json](current-evidence.json) links every current
outcome to its original record; [structural-audit.json](structural-audit.json)
separates contract paths, import structure, forwarding and editable output size.

Full relevant raw logs and source hashes are published. Unrelated projects'
queue rows are omitted from scheduler receipts only, with before/after hashes in
scheduler-redactions.json. No model calls or API keys were used. Reserved test
families remain untouched; model difficulty and minimum proof depth are unknown.

The separate [alternative-proof check](alternative-proof-001/README.md) also passed
16/16 strict verifications. A [balanced 32-call proposal](../varied-calibration-plan-001/README.md)
is now frozen and tested, but no model execution is authorized or started.
