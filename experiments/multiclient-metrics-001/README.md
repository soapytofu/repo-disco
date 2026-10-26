# Multi-client call-use and contract-dependence audit

Offline analysis of previously reviewed evidence. **No new model calls or verifier runs.** The existing `scripts/proof_usage_metrics.py` now has an additive multi-client mode; its original single-client interface/results remain unchanged. Eight test methods (three legacy, five multi-client) pass, covering repetition, repository scope, missing/duplicate/conflicting evidence, unknown aliases/definitions and invalid ablation outcomes.

`depth-input.json` records the two clients for all eight model trials, using explicit repository-variant IDs. The output has **eight scoped target instances** (four depth/condition variants × two targets), not sixteen new targets and not eight independent research tasks. Shared composition helpers are used by both clients; separate helpers each by one. **Finish is observed in both clients in every condition**, including separate. No ablation evidence exists for these particular saved model proofs in this audit, so dependence is null, not zero. Proof-prerequisite depth is also null rather than inferred from call order.

`branch-input.json` separately records four reference targets (two conditions × two clients) and all 16 helper/target interventions from the completed contract-ablation job. The observed usage and measured fixed-proof sensitivity agree: two shared A helpers each affect both clients; separate A/B helpers each affect their one client; unused shared B helpers affect none. Reference evidence is explicitly separated from model-generated proofs.

Inputs link each record to reviewed result JSON. `source-hashes.json` pins the consumed evidence files. The aggregate function validates identity/completeness and does not independently execute or attest proof logs; `build_audit.py` checks saved statuses and constructs the audited inputs. A complete ablation matrix must include unaffected targets, so missing measurements cannot silently become zero. Symbols are scoped to a repository variant; same spelling across variants is not proof of the same definition. Counts represent syntax and fixed-proof sensitivity, not dynamic execution frequency, proof minimality or model performance benefits.

Reproduce from repository root:

```bash
python3 experiments/multiclient-metrics-001/build_audit.py
python3 scripts/proof_usage_metrics.py experiments/multiclient-metrics-001/branch-input.json --multiclient
python3 -m unittest discover -s tests -p test_proof_usage_metrics.py
```
