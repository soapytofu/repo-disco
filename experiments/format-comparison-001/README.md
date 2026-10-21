# format-comparison-001: complete-program versus custom-diff repairs

**Completed October 21, 2026.** A 50-call pilot with Claude Sonnet 4.6 on AWS Bedrock compared two output formats on five small, single-file Dafny repair problems. Complete-program responses passed verification in **25/25** trials; custom-diff responses passed in **13/25**, with **12 patches rejected before verification**. No API errors or verifier timeouts were recorded.

This informs the repair interface for our next prototype. It does not establish repository-level reasoning performance or reproduce Formal Disco's published evaluation.

## Design and results

Each case received five independent single-request attempts in each format. Format order alternated by case and repetition; it was not randomized. Each attempt received the same broken source and original verifier feedback for its case, not previous responses. The shared instructions required preservation of declarations, preconditions, postconditions, and assertions. Format-specific instructions differed, including examples for the custom diff; prompt lengths therefore differ.

| Case | Defect | Complete program | Custom diff |
| --- | --- | --- | --- |
| `abs_wrong_branch` | Absolute-value branch signs reversed | 5/5 | 0/5 |
| `clamp_missing_upper_bound` | Missing upper clamp | 5/5 | 0/5 |
| `max_body_placement` | Method signature separated from body | 5/5 | 3/5 |
| `min_missing_brace` | Missing method closing brace | 5/5 | 5/5 |
| `sum_missing_invariant` | Missing arithmetic loop invariant | 5/5 | 5/5 |
| **Total** | | **25/25 (100%)** | **13/25 (52%)** |

All five broken inputs failed verification, and their reference repairs passed before model requests. See [baseline validation](baseline-validation.json) and [case sources and verifier output](cases/). The maximum case reuses the earlier extension/repair pilot; these are not five held-out benchmark problems.

Ten rejected patches omitted indentation in deletion directives for absolute value or clamp. Two maximum patches contained malformed anchors. The strict patch reader rejected all 12 without materializing an edited program. These are interface failures, not evidence that Dafny rejected the proposed mathematical repairs.

All 38 materialized candidates passed Dafny. On October 21, the assistant read the five distinct successful outputs and checked that all 38 match the corresponding reviewed references after whitespace normalization. The programs retain the original declarations and task obligations, with the intended branch, bound, body-placement, brace, or invariant repair. This review supplements the automatic preservation screen and did not make additional model calls. See [preservation review](preservation-review.json).

## Configuration and usage

- Model: `us.anthropic.claude-sonnet-4-6`; Bedrock region: `us-east-1`.
- Output cap: 4,096 tokens per request; provider-default temperature; no fixed random seed.
- Exactly 50 dispatched requests; SDK total attempts 1; no automatic model or verifier retries.
- Dafny 4.11.0 / Z3 4.12.1; verifier limit 60 seconds per candidate.
- Starting repository commit: `c7f70f6bb1de4936c7727946f6b7506b5c0ef379`.
- Recorded usage: **21,785 input + 6,815 output = 28,600 tokens**. Billing cost was not captured.
- Exact package versions, input hashes, and original settings: [protocol](run/protocol.json).

## Execution history and unattended operation

The run began on October 20 and paused after five calls for interactive review. Allocation 54226017 subsequently expired; no sixth request was dispatched then. On October 21, Slurm job **54461782** resumed at call 6 without interactive pauses and completed call 50. The original protocol retains its original five-call pause setting; the [resume metadata](run/resume-20261021T225413-810048Z.json) records the switch to unattended execution.

The unattended runner writes an atomic ledger before each dispatch, counts an interrupted request against the budget rather than repeating it, and holds an exclusive run lock. It stops on an API error, a suite `STOP` file, or the 50-call cap. Slurm's two-hour limit is an additional execution bound. Four offline checks cover resuming after call 5, an interrupted call, an exhausted budget, and an API-error stop; all passed. No paid requests were used for those checks.

The private credential handoff was deleted when the resumed runner loaded it. The runner cleared its environment at normal completion. No credentials are included in this archive.

## Evidence and reuse

- [50-row trial log](TRIALS.md), [machine-readable summary](summary.json), and [final call ledger](run/ledger.json).
- [Planned trial order](run/plan.json); each numbered folder includes the exact prompt, response, parsed text, result, and—when a patch could be applied—candidate source and verifier output.
- [Batch stdout](run/batch-54461782.log) and [stderr](run/batch-54461782.err).
- [Original interactive runner](run/runner.py), [executed unattended runner snapshot](run/unattended-runner-20261021T225413-810048Z.py), [resume entry point](run_comparison_unattended.py), and [Slurm submission script](resume.sbatch).
- [Offline resume tests](test_unattended_resume.py): run `python3 experiments/format-comparison-001/test_unattended_resume.py` from the repository root.

The archived runners and submission script preserve the original Cannon paths under `outputs/format-comparison-001`. The completed ledger is evidence, not a fresh-run configuration. Do not reset it to rerun calls. A new experiment needs a new run ID, explicit call budget, and recorded configuration; the credential loader also depends on `experiments/repair-003/runner.py`.

## Interpretation and next step

Use complete-file responses as the practical default for the initial two-module prototype, then revisit edit formats as repository size grows. A 48-percentage-point difference here is descriptive: there are only five underlying problems, repeated samples are grouped by problem, one problem was reused, and this comparison covers one model and a custom diff format. Do not generalize it to all diff-based agents or claim multi-module success.

Next: finalize a repository manifest, create a verified two-module dependency, record per-module and full-repository verification, and introduce one controlled cross-module break for an end-to-end repair pilot. See the [timeline and next milestone](../../docs/research-progress.md).
