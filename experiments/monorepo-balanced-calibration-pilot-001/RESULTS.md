# Balanced clarified-syntax calibration results (development data)

32/32 requests reserved; 32 saved completed responses; 32 unique request IDs. Strict whole-workspace successes: **29/32 planned trials**. No SDK retries: True.

Every trial uses its original frozen prompt/order/settings and a fresh seed. No repairs, retries, feedback, replacement samples or main-corpus requests.

| Family | Shallow/shared | Shallow/separate | Deep/shared | Deep/separate | Total |
| --- | ---: | ---: | ---: | ---: | ---: |
| conditional_preconditions | 2/2 | 2/2 | 2/2 | 2/2 | 8/8 |
| interval_witness | 2/2 | 2/2 | 0/2 | 1/2 | 5/8 |
| map_transfer | 2/2 | 2/2 | 2/2 | 2/2 | 8/8 |
| sequence_offset | 2/2 | 2/2 | 2/2 | 2/2 | 8/8 |

Parser/guard admission: **32/32 planned trials**.

## Failure categories

- PROOF_FAILURE: 3
- VERIFIED: 29

## Review before scale-up

- conditional_preconditions: 8/8 floor/ceiling requires review
- map_transfer: 8/8 floor/ceiling requires review
- sequence_offset: 8/8 floor/ceiling requires review

## Usage and interpretation

Saved token usage: `{"cacheReadInputTokens": 0, "cacheWriteInputTokens": 0, "inputTokens": 95044, "outputTokens": 5332, "totalTokens": 100376}`. No dollar estimate is inferred from token totals.

One inspected development instance per family, four structural variants and two fresh samples per variant. Shared/separate output workloads differ; depth is reference-relative. All prompts, source and parser bytes match the clarified bundle. Prior results are not pooled; no causal prompt-change, held-out or population claim. All earlier budgets are exhausted and cannot be reused.

Parser/guard failures are part of end-to-end completion, but must be distinguished from proof failure. A verifier pass establishes the protected contract, not task difficulty. Review both 8/8 family ceilings and 0/8 floors before scaling. The main 192-call corpus is still gated and has no new authorization.

All exact messages, provider responses, request IDs, extraction decisions, candidate source, guarded parent/accepted hashes and raw verifier stdout/stderr are archived under model-001. results-review.json and model-001-sha256.json bind the review to saved bytes.
