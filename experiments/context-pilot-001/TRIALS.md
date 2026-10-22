# Eight-call context pilot log

Completed October 22, 2026, Cannon job 54695919. Raw outcomes are preserved; the diagnosis column distinguishes name resolution from failed proof obligations.

| # | Condition | Repeat | Result / diagnosis | Helper call | Input / output tokens | Evidence |
| --- | --- | --- | --- | --- | --- | --- |
| 1 | local_only | 1 | NAME_RESOLUTION_ERROR | `MagnitudeNonnegative (not exported / nonexistent)` | 325 / 162 | [Result](pilot-001/01-local_only-r1/result.json) · [Diagnostics](pilot-001/01-local_only-r1/verifier-stdout.txt) |
| 2 | api_context | 1 | PASS | `EstablishLowerBound` | 407 / 84 | [Result](pilot-001/02-api_context-r1/result.json) · [Diagnostics](pilot-001/02-api_context-r1/verifier-stdout.txt) |
| 3 | api_context | 2 | PASS | `EstablishLowerBound` | 407 / 84 | [Result](pilot-001/03-api_context-r2/result.json) · [Diagnostics](pilot-001/03-api_context-r2/verifier-stdout.txt) |
| 4 | local_only | 2 | NAME_RESOLUTION_ERROR | `MagnitudeNonnegative (not exported / nonexistent)` | 325 / 155 | [Result](pilot-001/04-local_only-r2/result.json) · [Diagnostics](pilot-001/04-local_only-r2/verifier-stdout.txt) |
| 5 | local_only | 3 | NAME_RESOLUTION_ERROR | `MagnitudeNonnegative (not exported / nonexistent)` | 325 / 151 | [Result](pilot-001/05-local_only-r3/result.json) · [Diagnostics](pilot-001/05-local_only-r3/verifier-stdout.txt) |
| 6 | api_context | 3 | PASS | `EstablishLowerBound` | 407 / 84 | [Result](pilot-001/06-api_context-r3/result.json) · [Diagnostics](pilot-001/06-api_context-r3/verifier-stdout.txt) |
| 7 | api_context | 4 | PASS | `EstablishLowerBound` | 407 / 84 | [Result](pilot-001/07-api_context-r4/result.json) · [Diagnostics](pilot-001/07-api_context-r4/verifier-stdout.txt) |
| 8 | local_only | 4 | NAME_RESOLUTION_ERROR | `MagnitudeNonnegative (not exported / nonexistent)` | 325 / 151 | [Result](pilot-001/08-local_only-r4/result.json) · [Diagnostics](pilot-001/08-local_only-r4/verifier-stdout.txt) |
