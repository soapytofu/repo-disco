# Eight-trial depth × sharing pilot results

Job **55298220** completed on shared, node holy7c08505, in 4m02s (2026-10-26 UTC; October 25 evening Eastern). Exactly eight requests were dispatched, with eight distinct request IDs and no automatic retries. All 24 verifier checks passed. The execution ledger, full raw responses, prompts, guarded source, input snapshot, usage and verifier stdout/stderr are in `model-001/`; scheduler logs are stored alongside it.

| Depth | Shared | Separate |
| --- | ---: | ---: |
| diamond | 2/2 | 2/2 |
| nested | 2/2 | 2/2 |

All eight responses passed the frozen tolerant extraction and edit guard. None was strict JSON-only; surrounding prose/fences were accepted under the preregistered parser. This is primary success under this pilot's protocol, unlike the earlier post-hoc extraction diagnostic. Protected imports, client contracts and provider source were unchanged; exact prompt hashes and archived source hashes were checked. `model-review.json` records the review.

The four diamond responses match their references ignoring whitespace. All four nested responses contain the same six calls per client as the references but move the independent third Lift before the first Join; these are valid alternative orderings, not new helper schemas or shorter proofs. `observed-calls.json` records exact call sequences and reference comparisons. Call order alone does not establish the dependency graph.

Usage: **6,952 input + 8,891 output = 15,843 total tokens**. Input tokens are exactly matched between sharing conditions within each depth (858 diamond, 880 nested); task depth changes source length. Two repeats per cell and one template family do not support general inference or model rankings. Both conditions retain shared Finish and underlying definitions. The perfect scores show successful completion on these tasks, with no measured sharing advantage or depth-related success drop. All eight authorized calls are exhausted.

## Next work, without model calls

Stop increasing this same call-chain template merely to seek failures. Build a structurally different family with conditional preconditions or inductive helper synthesis, plus verifier-only controls that distinguish valid alternatives from omitted obligations. Add neutral naming and held-out family controls before a future separately authorized model batch. The present client-call-only edit policy cannot evaluate helper-proof synthesis; any such task needs a separate guard/protocol and cannot be mixed into these frozen results.
