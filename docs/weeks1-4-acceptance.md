# Weeks 1–4 acceptance review

**Assessment: initial proposal milestones complete as of October 28, 2026.**
This is an evidence-based implementation/milestone assessment, not a claim that
the research question is answered or that the entire published baseline is
reproduced. Timeline source: Sophie Zeng's HCRP Research Proposal F26, page 5,
“Time Frame,” read again at this checkpoint. Weeks are proposal-relative.

| Proposal requirement | Completed evidence | Scope |
| --- | --- | --- |
| Set up Formal Disco and Dafny | [Setup guide](setup/README.md), initial generation/repair logs, pinned Dafny/Z3 and cluster environment records | Working reproducible research environment |
| Reproduce a baseline generation/evaluation run | [Baseline reproduction smoke](../experiments/baseline-reproduction-001/README.md): pinned DafnyBench, 1,567 verifier preflight records, 20 frozen model trials; 7 legacy successes, 6 strict exit-zero results | Bounded baseline evaluation, not every paper result; legacy scoring and specification-fidelity caveats separately audited |
| Finalize initial repository representation and variables | [Consolidated protocol review](controlled-corpus-design.md): source manifests/hashes, declared import map, contracts/edit scope, revisions, trial identities and distinct measurement definitions | Full source plus declared map; no automatic retrieval or inferred proof-dependency claims |
| Implement multi-module context and whole-repository verification | [Two-module prototype](../experiments/two-module-001/README.md), [repository backend](../experiments/repository-backend-001/README.md), [candidate integration](../experiments/repository-candidate-001/README.md) | Included-file verification, protected edits and immutable original snapshots |
| Implement and validate repository repair | [Repository agent](../experiments/repository-agent-001/README.md): 12 scripted verifier expectations and four contract rejections; then four live first-attempt repairs with guarded accepted revisions | Feedback path tested in scripted controls; live multi-step recovery remains unmeasured. Atomic HEAD applies to cooperating local POSIX writers |
| Begin scaling generation | [Repository extension pilot](../experiments/repository-extension-001/README.md): 14 verifier controls, four actual Claude calls, four verified new client modules across two seed repositories | Initial contract-guided client extension; fixed interfaces and visible seed examples, not open-ended repository/specification synthesis |

The proposal asks for a baseline generation/evaluation run and the **beginning**
of scaled generation during Weeks 1–4. The completed small runs meet that initial
scope. Neither the size of the primary corpus nor broad model comparison is a
Weeks 1–4 completion requirement; those belong to later phases. This conclusion
is not based on counting hand-built controls as generated data.

## Results that must remain qualified

- Baseline strict verifications include one redundant non-null-precondition cleanup.
  Trial 08 has no sortedness/permutation postcondition in the original specification;
  trial 20 only lower-bounds the divisor sum. See the [manual source audit](../experiments/baseline-reproduction-001/specification-review.md).
- The live agent's four successes and the four extension successes are development
  integration results on small tasks. They do not establish general reasoning ability,
  a sharing benefit, statistical significance or generalization to unseen families.
- Each extension starts independently from its fixed seed. Four new modules yield
  four verified repository variants across two seeds; they are not four new families.
- All previous failures, parser rejections and original scoring records remain saved.
  No prompt, source or result was silently corrected after collection.

## Next work: Weeks 5–6

1. Specify the primary corpus size and family-level development/held-out split before
   collecting more data. Inspected composition/branching/inductive families remain
   development families.
2. Build matched task sets varying dependency depth, API reuse and shared proofs,
   preserving target semantics and disclosing source/token/edit-count differences.
   Use harder obligations to avoid the current ceiling results.
3. Run a separately budgeted generation/validation batch with the existing logging,
   immutable-source and verifier gates; retain rejected candidates in the denominator.
   Use import, observed-call and contract-ablation evidence as separate measurements.

Baseline configuration comparisons, training trajectories and open-model fine-tuning
remain Weeks 7–8; held-out evaluation and final analysis remain Weeks 9–10. No new
paid batch or training run is authorized by this completion assessment.
