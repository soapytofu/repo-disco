# Saved sequence proofs: exact extraction diagnostic

Verifier-only job **60694583** completed on nonpreemptible `test` in **48 seconds**. All **eight exact saved sequence proofs verify**, each with **11 verified obligations, zero errors, zero warnings and strict exit 0**. No new model calls, proof edits, retries or new primary model scores were involved.

| Original condition | Saved responses | Strict diagnostic successes |
| --- | ---: | ---: |
| Shared / verifier diagnostics | 2 | 2 |
| Shared / failure notice | 2 | 2 |
| Separate / verifier diagnostics | 2 | 2 |
| Separate / failure notice | 2 | 2 |

These eight responses represent seven distinct complete candidate workspaces from two fixed sequence-task variants. The diagnostic selects the sole explicit JSON fence, preserves its exact substring and every decoded body byte, and applies the original frozen body guard and original failing-base/empty-template adapter. The complete source files, contracts, providers, clients and decreases annotations remain protected. The additional recursive call was already present in the saved model outputs; no analyst supplied or changed a proof step.

This confirms that the eight observed sequence failures in the primary run were extraction failures on these inputs, rather than failures of their saved proofs. The **original primary result remains 16/24**, including eight envelope rejections. This selected retrospective diagnostic is not a fresh 24/24 model run, not a replacement score, and not evidence of a general feedback/sharing effect. Both feedback conditions succeed here, as they did on the admitted arithmetic/witness cases. A future extraction policy needs its own prospective freeze and adversarial validation; this one-fence diagnostic is intentionally narrow.

The review reproduces all payload selections and candidates, checks 52 immutable-file comparisons and 12 body boundaries, verifies the full named-declaration CSV scope, and confirms that all **1,204 original raw archive files** and **64 copied parent files** match their hashes. The original runtime, policies, responses, failed HEADs and score remain unchanged. Nine fake-process/offline tests passed both locally and on Cannon before submission.

Evidence:

- [Reviewed results](results-review.json), [reviewer](review.py) and [review log](review-001.log).
- [Full verification archive](verification-001/), including exact fixtures, payloads, parent responses, frozen policies, per-candidate stdout/stderr, raw CSV, runtime and environment.
- [300-file archive manifest](verification-001-sha256.json), [transfer inventory](transfer-core.json), [submission](submission-core.json), [accounting](accounting-60694583.txt), [Slurm log](verify-60694583.log) and [stderr](verify-60694583.err).
- [Extraction/protection checks](prepared-review.json), [local tests](offline-tests.log) and [Cannon tests](remote-offline-tests.log).

Reproduce the review locally with `python3 -B experiments/diverse-repair-extraction-diagnostic-001/review.py`. It reads saved evidence and makes no model or verifier calls.
