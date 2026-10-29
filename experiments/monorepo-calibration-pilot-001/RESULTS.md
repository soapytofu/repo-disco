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
8/8 ceiling. A separately versioned [verifier-only diagnostic](diagnostic-001/README.md)
completed: **11/11** extractable newline/expression candidates verified in job
56022487 (33s), with zero new calls. Original scores remain **18/32**. The three
JSON-wrapper rejections remain unevaluated; do not report 29/32 as the original
calibration score or a new unbiased comparison.

## Next gate before scale-up (proposal only)

1. Use a new, explicitly versioned output protocol that returns helper **bodies**
   for host-owned insertion into immutable files. This removes file-suffix copying
   from the reasoning task; retain exact contracts/imports/attributes and strict
   JSON decoding. Do not silently repair ambiguous or double-escaped payloads.
2. Admit bounded pure inline if expressions as well as statement branches, and
   preflight both valid forms plus adversarial bypass attempts before refreezing.
   The diagnostic guard is evidence for this change, not a replacement production
   policy for the completed run.
3. Strengthen semantic obligations before repeating calibration: e.g., finite-map
   aliasing cases and interacting invariants, relational joins requiring explicit
   intermediate-witness reasoning, or a sequence obligation beyond standard
   append induction. These are design proposals, not validated new fixtures.
4. Run verifier controls first, freeze a new calibration version and request a new
   model budget. Do not spend the 192-call main budget or reuse exhausted calls.

The four development instances and two samples per cell are insufficient for a
causal depth/sharing claim. Accepted-source AST/hash evidence and all original
failures remain available for further analysis without modifying the experiment.
