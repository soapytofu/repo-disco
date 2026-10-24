# Frozen depth × sharing pilot — preparation only

**Eight planned calls; zero authorized or made.** This archive contains no dispatcher. Execute only after separate user authorization and a reviewed bounded adapter. Never run an earlier experiment's dispatcher against this plan. All prior experiments remain unchanged.

Two task depths × two sharing conditions × two repetitions. Both clients must be completed in one response. All requests use identical instructions and full source in the same file order, without a dependency map, examples or conversation history. The second block reverses the first:

| Trial | Block | Depth | Condition |
| ---: | ---: | --- | --- |
| 1 | 1 | diamond | shared |
| 2 | 1 | diamond | separate |
| 3 | 1 | nested | separate |
| 4 | 1 | nested | shared |
| 5 | 2 | nested | shared |
| 6 | 2 | nested | separate |
| 7 | 2 | diamond | separate |
| 8 | 2 | diamond | shared |

This balances early/late positions (each cell's mean position is 4.5), sharing order within each depth, and depth order across blocks. It is deterministic counterbalancing, not randomization or full carryover balancing. Each request is independent; repetitions reuse the exact same prompt. Names are fixed, not counterbalanced in this pilot.

## Frozen inputs and execution settings

`plan.json` fixes the order and prompt hashes; `prompts/` stores four exact message arrays. `fixtures/` contains the empty client tasks and immutable providers, byte-identical to the validated tasks. `parser.py` is the unchanged tolerant-v1 parser. `protocol.json` fixes model ID, region, output cap, timeouts, failure handling, outcomes and zero execution authorization. `frozen-bundle.json` hashes the plan, protocol, prompts, sources, parser and validation code. Record this Git commit in any later execution authorization, snapshot every frozen input, and validate hashes before dispatching each trial.

Planned model: Bedrock `us.anthropic.claude-sonnet-4-6`, us-east-1, max output 4096 tokens, temperature/top-p omitted (provider defaults). No streaming, tools, automatic retries, repair turns or extra requests. The model alias/defaults can change server-side; record returned request/model metadata and run timestamps. Stop on API ambiguity or verifier infrastructure failure. An interrupted batch may contain fewer than eight calls; never silently retry or replace a dispatched trial. Any later request adapter must log dispatch before sending, cap the complete batch at eight, disable SDK retries, and require explicit execution authorization.

Verify All.dfy and both clients separately on compute nodes using `dafny verify --verify-included-files`, 60 seconds per entry. Use shared/sapphire without requeue. Preserve raw responses, extraction offsets, guard decisions, usage, request IDs, source hashes and every verifier stdout/stderr. Report truncated responses as observed; do not increase the cap mid-batch. The parser permits wrappers but performs no proof repair. Primary success requires all three verification checks; syntax/format/guard/proof failures are unsuccessful trials, while infrastructure failures and unattempted trials are separately identified.

## Offline validation and limits

The original task batch passed all 76 expected controls on Cannon (job 54977065). This preparation changes no Dafny source, so another compute verification run is unnecessary. Offline checks validate exact source embedding, block balance, every frozen hash, tamper rejection, parser identity and recovery of all four verified reference pairs through fenced JSON. Run `python3 validate.py` and `python3 test_freeze.py` from this directory. The reference regression test needs the neighboring sharing-composition-002 archive; references are never included in prompts.

Report all four cells separately, including tolerant extraction, guard acceptance, joint success, per-client success, token usage and paired-block outcomes. Strict JSON-only acceptance is descriptive only. Call count/dependency pattern is descriptive; any manually classified failure mechanism is exploratory. Do not change thresholds, parser, tasks or stopping rules after seeing responses.

This is a feasibility pilot, not a powered comparison: two responses per cell on one task family cannot establish general sharing benefits. Both conditions retain common Finish and definitions; only composition-helper identities differ. Depth also changes source/output length. The reference call counts are not proven minima. A later study should add held-out task families, neutral counterbalanced names and more independent instances, rather than treating repeated samples of these tasks as independent tasks.
