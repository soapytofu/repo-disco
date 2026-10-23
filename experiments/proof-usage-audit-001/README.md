# Observed proof-call audit

October 23, 2026. Read-only analysis of the completed composition-pilot-001 ledger; no new model calls or verification jobs.

All 12 successful trials call lemmas in **two distinct provider modules**. Resolving client aliases yields:

| Repository task | Recorded call sequence |
| --- | --- |
| range_precondition | Bounds.MakeReady; Transform.EvaluateShift |
| relation_lifting | OrderFacts.Transitive; Reachability.Lift |
| sequence_composition | SequenceFacts.LengthConcat; SequenceProperties.FromPositive |

The 12 trials represent only **three distinct client targets**. None of the six repository-scoped provider lemmas is observed supporting multiple distinct client targets. This is a limitation of a corpus with one client target per repository, not evidence that the model cannot reuse shared proofs. Repetitions and context conditions must not inflate a shared-lemma reuse metric. Identically named symbols in different repositories must not be merged without evidence of shared identity.

`results.json` preserves resolved call sequences per trial, provider coverage, and target counts. Source ledger: `experiments/composition-pilot-001/pilot-001/ledger.json`; source maps: that run's `inputs/*/dependency-map.json`. The original archive's SHA-256 manifest covers those inputs.

Reproduce from the repository root:

```sh
python3 scripts/proof_usage_metrics.py experiments/composition-pilot-001
python3 tests/test_proof_usage_metrics.py
```

Three tests pass, including duplicate-trial rejection, alias resolution, repository-scoped identity, and preventing repetitions from inflating target counts. The analysis trusts the recorded successful calls; the separate preservation review already checked accepted candidate source. Call order is not interpreted as a proof-prerequisite graph, and proof depth remains unknown.

Next schema requirement: represent repository ID, client target lemma ID, provider definition ID, and intended prerequisite edges explicitly, allowing multiple client lemmas within one repository. The current utility deliberately supports the existing one-target-per-task archive only. A multi-client fixture and deterministic lemma ablations are required before claiming shared-proof dependence.
