# Eight-call clarified-syntax smoke pilot — proposed, not authorized

Recommend **at most eight new Claude requests**, one response per task, no retries,
repair feedback, replacement samples or reassignment. **Zero calls made.**

## Scope and fixed order

All four deep development task families, shared and separate, with exactly the
clarified statement-syntax-v1 prompts and unchanged body-json-v2.1 parser. Deep
tasks exercise more involved statement structures while keeping depth fixed
within each pair. This does not sample shallow tasks or estimate a depth effect.

| Order | Family | Condition |
| --- | --- | --- |
| 1 | Conditional preconditions | Deep/shared |
| 2 | Map transfer | Deep/separate |
| 3 | Sequence offset induction | Deep/separate |
| 4 | Interval witness | Deep/shared |
| 5 | Conditional preconditions | Deep/separate |
| 6 | Map transfer | Deep/shared |
| 7 | Sequence offset induction | Deep/shared |
| 8 | Interval witness | Deep/separate |

Each pair is four positions apart; two families start shared and two separate.
Selection includes every deep configuration regardless of past outcomes. Each
trial starts a fresh context with full source and map, without reference solutions,
previous responses or verifier feedback.

## Budget and prerequisites

Eight requests total, one SDK attempt each, no connectivity calls. Same model and
settings: Claude Opus 4.5 via Bedrock, temperature 1.0, maxTokens 4096. Aggregate
**output-token ceiling: 32,768**; input tokens are additional. This is neither an
expected-use estimate nor a dollar quote.

Execution requires a tested bounded runner, runtime hash freeze and explicit new
eight-call authorization bound to scope/runtime. Inspect existing ledger/output/
submission state and submit once on a live-confirmed nonpreemptible compute
partition. Dafny runs only on compute. No requeue, automatic resume or reassignment.
Stop on ambiguous requests, persistence/integrity failures or verifier infrastructure
errors. Syntax and proof failures are saved outcomes, not repair permissions.

No live runner, authorization file, credential access or submission was created for
this planning step. Reconnection/key instructions can follow runner preparation.

## Reporting and decision gate

Primary outcome: parser/guard admission out of eight planned trials. Also report
strict whole-workspace verification out of eight; distinguish syntax/schema/guard
errors, proof failures, timeouts and infrastructure errors. Save all messages,
responses, extraction decisions, source/contract hashes, request IDs, usage and raw
verifier logs to GitHub, excluding credentials.

For syntax readiness require eight unambiguous responses, **8/8 parser/guard
admission**, intact protected source/contracts and a completed verifier success
or proof failure for every admitted candidate. Any syntax failure pauses scaling
for offline diagnosis; no silent repair or rescoring. Even 8/8 is a small development
check, not a reliable rare-error rate or generalization result.

Review proof outcomes by family: 0/2 and 2/2 are inspection signals, not reliable
difficulty estimates. A fresh full 32-call run is **never automatic** and needs a
reviewed scope and separate authorization. Do not pool these eight deep-only trials
into that later evaluation. Main 192-call collection remains deferred. Previous
experiments and scores remain unchanged.

## Frozen artifacts and offline checks

[frozen-001](frozen-001/README.md) contains exact prompts, sources, parser, previous
verifier-evidence links, fixed order and [scope.json](frozen-001/scope.json).
Freeze SHA-256: `fd215bd1ddf7035a0e1e9c1c248e090425a00996b5d721840820b3fb8205b80e`.

Four test methods passed: structural selection/order balance; reproducible freeze
and tamper rejection; exact parent prompt/source/parser/settings preservation; and
trial hashes, eight-call cap and absent execution artifacts. These supplement the
clarified bundle's nine parser test methods. No new model or Dafny runs.

```sh
python3 -B experiments/monorepo-syntax-smoke-001/test_scope.py
```

[offline-tests.log](offline-tests.log) records checks; scope-review.json pins the
plan/code/log and bundle freeze. prepare_scope.py refuses to overwrite a freeze;
tests reproduce it in a temporary directory.
