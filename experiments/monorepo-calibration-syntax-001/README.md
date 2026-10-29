# Offline syntax clarification: statement-syntax-v1

**Completed offline only. Zero model calls, zero new Dafny runs.** All nine test
methods passed. The body-json-v2.1 parser is byte-identical to the previous frozen
parser; the prior pilot remains **1/32 strictly verified**. No future model run is
authorized by this bundle.

## Prompt change

The previous run had 31 first syntax failures at `then` where `{` was required.
The new system message and all 16 task prompts explicitly distinguish:

- Statements: `if CONDITION { STATEMENTS } else { STATEMENTS }`; preserve inner
  branch braces and end every assertion/lemma call with a semicolon.
- Pure expressions: `if CONDITION then VALUE else VALUE`; never put lemma-call
  statements in these branches.
- Output: omit only the outer lemma braces; return exact JSON filename/body keys,
  with newlines escaped once, without declarations or extra wrappers.

Every task includes the same neutral example using `assert true` and constant
expressions. The example is explicitly not a solution and uses no task-specific
helper, mathematical fact, or reference proof. The rest of the source context,
file map, contracts, task metadata and inference settings are unchanged. These
instructions are clearer by inspection; model adherence has not been measured.

## Artifacts and validation

[frozen-001](frozen-001/README.md) contains the updated prompts, unchanged seeds
and parser, copied prior verifier evidence links, and the unchanged 32-slot order
with updated prompt hashes. Its SHA-256 is
`cfa8ae517c07751f45591ce52d91c3f63240dee167f9ffbdf83b5a282799cd32`.
The 32 slots are a possible future proposal, not permission to execute it. There
is no live runner, submission, authorization file or credential access here.

[offline-tests.log](offline-tests.log) and [validation.json](validation.json)
record nine test methods covering:

- Deterministic preparation, exact source/guard preservation, unchanged settings
  and counterbalance, and prompt/hash bindings.
- 112 positive syntax cases and 16 fenced examples across the 16 task variants.
- 128 malformed statement cases and 320 schema/bypass cases, plus resource bounds
  and seed-integrity rejection. These are parser checks, not semantic proofs.
- Exact reconstruction of all 16 previously verified references, with hashes
  checked against prior successful verifier logs. No reference was rerun.
- Replay of all 32 saved responses with identical old/new parser decisions and
  accepted bytes. All 443 raw archive file hashes remain unchanged. Rejected
  responses were neither repaired nor rescored.

Reproduce the tests from the repository root:

```sh
python3 -B experiments/monorepo-calibration-syntax-001/test_syntax.py
```

`prepare_prompts.py` reproduces the bundle in a fresh destination (the test does
this in a temporary directory). Its default command refuses to overwrite the
existing freeze. `offline-review-manifest.json` pins the preparation/test code,
log, report and bundle freeze used in this review.

## Next gate

Review this prompt-only revision before proposing any new calls. A future run
requires its own bounded runner/authorization bound to this freeze; the completed
32-call execution cannot be resumed or reused. Offline acceptance does not show
that a model will obey the syntax, solve the proofs, or exhibit a sharing/depth
effect. The main 192-call study remains deferred and unauthorized.
