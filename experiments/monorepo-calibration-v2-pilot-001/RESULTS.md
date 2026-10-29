# Calibration results (development data)

32/32 requests reserved; 32 saved completed responses; 32 unique request IDs. Strict whole-workspace successes: **1/32 planned trials**. No SDK retries: True.

Every trial uses its original frozen prompt/order/settings and a fresh seed. No repairs, retries, feedback, replacement samples or main-corpus requests.

| Family | Shallow/shared | Shallow/separate | Deep/shared | Deep/separate | Total |
| --- | ---: | ---: | ---: | ---: | ---: |
| conditional_preconditions | 0/2 | 0/2 | 0/2 | 0/2 | 0/8 |
| interval_witness | 0/2 | 1/2 | 0/2 | 0/2 | 1/8 |
| map_transfer | 0/2 | 0/2 | 0/2 | 0/2 | 0/8 |
| sequence_offset | 0/2 | 0/2 | 0/2 | 0/2 | 0/8 |

## Failure categories

- OUTPUT_REJECTED: 31
- VERIFIED: 1

Guard rejection reasons (raw responses retained; no post-hoc repair):

- `Unexpected proof token`: 31

## Usage and interpretation

Saved token usage: `{"cacheReadInputTokens": 0, "cacheWriteInputTokens": 0, "inputTokens": 81492, "outputTokens": 5386, "totalTokens": 86878}`. No dollar estimate is inferred from token totals.

One development instance per family and two samples per cell. Shared/edit-count and per-family depth differences are disclosed. Tasks and output policy both changed from the first pilot; before/after differences do not isolate either change. Descriptive development calibration only; no causal, held-out or population claim.

Parser/guard failures are part of end-to-end completion, but must be distinguished from proof failure. A verifier pass establishes the protected contract, not task difficulty. Review both 8/8 family ceilings and 0/8 floors before scaling. The main 192-call corpus is still gated and has no new authorization.

All exact messages, provider responses, request IDs, extraction decisions, candidate source, guarded parent/accepted hashes and raw verifier stdout/stderr are archived under model-001. results-review.json and model-001-sha256.json bind the review to saved bytes.

## Separate offline syntax audit

[output-syntax-audit.json](output-syntax-audit.json) and its reproducible
[audit script](audit_output_syntax.py) inspect the same saved bytes without repair
or rescoring. All 32 responses have valid JSON and the exact filename/body schema.
Every rejected trial first supplies `then` where the frozen statement grammar
expects `{`: expression-style conditionals were used around lemma-call statements.
Other syntax or proof problems may remain beyond that first error; they have not
been repaired or evaluated. No additional verifier or model calls were made.

Trial 28 (interval witness, shallow/separate, sample 2) uses braced conditionals
and calls End.Direct with the selected endpoint in each branch. Both helper bodies
were accepted with the original contracts and other files intact; whole-workspace
verification returned exit 0. This is the only admitted/verified candidate.

The next gate is a non-paid review of prompt syntax instructions and neutral
statement-versus-expression examples, followed by offline protocol validation.
Do not scale the main corpus or interpret the 31 syntax rejections as failed proof
reasoning. Any future prompt changes require a new freeze and separate call budget;
this run and its original 1/32 score remain unchanged.
