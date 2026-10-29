# Calibration results (development data)

32/32 requests reserved; 32 saved completed responses; 32 unique request IDs. Strict whole-workspace successes: **18/32 planned trials**. No SDK retries: True.

Every trial uses its original frozen prompt/order/settings and a fresh seed. No repairs, retries, feedback, replacement samples or main-corpus requests.

| Family | Shallow/shared | Shallow/separate | Deep/shared | Deep/separate | Total |
| --- | ---: | ---: | ---: | ---: | ---: |
| conditional_preconditions | 0/2 | 0/2 | 0/2 | 0/2 | 0/8 |
| finite_map_frames | 2/2 | 2/2 | 2/2 | 2/2 | 8/8 |
| relational_join | 2/2 | 2/2 | 1/2 | 2/2 | 7/8 |
| sequence_induction | 0/2 | 2/2 | 1/2 | 0/2 | 3/8 |

## Failure categories

- OUTPUT_REJECTED: 14
- VERIFIED: 18

Guard rejection reasons (raw responses retained; no post-hoc repair):

- `Ambiguous or malformed JSON wrapper`: 3
- `Protected source changed`: 5
- `Unknown expression name`: 6

## Usage and interpretation

Saved token usage: `{"cacheReadInputTokens": 0, "cacheWriteInputTokens": 0, "inputTokens": 72712, "outputTokens": 28883, "totalTokens": 101595}`. No dollar estimate is inferred from token totals.

One development instance per family and two samples per cell. Shared/edit-count and per-family depth differences are disclosed. Descriptive calibration only; no causal, held-out or population claim.

Parser/guard failures are part of end-to-end completion, but must be distinguished from proof failure. A verifier pass establishes the protected contract, not task difficulty. Review both 8/8 family ceilings and 0/8 floors before scaling. The main 192-call corpus is still gated and has no new authorization.

All exact messages, provider responses, request IDs, extraction decisions, candidate source, guarded parent/accepted hashes and raw verifier stdout/stderr are archived under model-001. results-review.json and model-001-sha256.json bind the review to saved bytes.

## Manual output-compliance audit

All 18 guard-admitted candidates verified; no scored trial reached a proof or
frontend failure. Five rejected responses differ outside their bodies only by a
missing final newline: appending just that LF makes the existing guard accept.
Six use inline if-then-else expressions (present in the task contracts but not
supported by the frozen body grammar). Three are rejected by the frozen JSON
wrapper rule. output-compliance-audit.json records the exact response hashes and
replay evidence. The original score remains **18/32**, not a proof-solving rate.

Do not scale to the 192-call main corpus yet. These output-policy effects explain
the conditional floor and much of the sequence variation; map tasks also show an
8/8 ceiling. A separately versioned, verifier-only diagnostic of the eleven
extractable newline/expression responses is being prepared; it will not replace
original scores, consume calls or retry model requests.
