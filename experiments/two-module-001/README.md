# two-module-001: dependency-aware verification and protected repair

A minimal two-file Dafny repository validates the first repository-level infrastructure step. `Arithmetic.Increment` promises `y == x + 1`; `Client.IncrementTwice` calls it twice and promises `y == x + 2`. The client depends on the provider's contract. This is an assistant-authored fixture, not a generated repository corpus or an independent benchmark.

## Verifier-only results

Slurm job **54468117** on Cannon ran 12 checks on October 21, 2026, with **zero model calls**. All 12 matched the declared expectations. Versions and timestamps are captured in [environment.json](verification-001/environment.json).

| Fixture | Provider only | Client only | Whole repository |
| --- | --- | --- | --- |
| Baseline | Pass | Pass | Pass |
| Provider implementation changed to `y := x - 1` | Fail | **Pass** | Fail |
| Provider contract weakened to `y >= x` (diagnostic control) | Pass | Fail | Fail |
| Assistant-authored reference repair | Pass | Pass | Pass |

The client-only command loads the provider but does not verify its implementation. It can therefore pass using an unproved imported contract. The whole-repository command explicitly uses `--verify-included-files`; this is the acceptance criterion. The weakened-contract fixture is a diagnostic control, **not an allowed repair**. All four fixtures keep `Client.dfy` byte-for-byte unchanged.

Dafny documents that included files are not verified by default unless explicitly passed or enabled with `--verify-included-files`: [reference manual](https://dafny.org/latest/DafnyRef/DafnyRef.html#sec-include-directives).

## Repository representation

[repository-manifest.json](repository-manifest.json) records the two module/file IDs, entry point, dependency edge, imported alias, exported method contracts, two provider call sites, client assertions, and repair policy. The fixture has dependency depth one and no shared helper lemmas. It establishes the representation for later experiments; it does not yet vary depth, size, or proof reuse.

Verification state is recorded separately for each source snapshot in [results.json](verification-001/results.json), keyed by variant, scope, and source hashes. The aggregate Dafny obligation counts are **not** individual-specification success rates. This prototype measures module-scope verification and full-repository completion only.

## Protected repair pilot

The user authorized up to **5 new Claude calls**, separate from the completed 50-call format pilot. The runner stops at the first protected candidate that passes provider, client, and whole-repository verification. It sends the broken provider, unchanged client, repository map, and original/previous failure feedback. It does not send the reference solution.

`repair_guard.py` enforces a deliberately narrow fixture-specific grammar: exact module, method signature, and ensures clause; one arithmetic assignment to `y` using `x` and integer literals. No extra declarations, statements, comments, or attributes are allowed. It is **not a general Dafny parser**. Arithmetic expressions that are syntactically allowed can still be wrong; Dafny decides correctness. The client is copied unchanged into every accepted candidate directory.

Six offline tests check acceptance of the reference body, rejection of contract weakening, assumptions, extra methods, and verification attributes, plus acceptance of a syntactically allowed but incorrect expression to ensure the guard is not an oracle for the answer.

**Model result: SUCCESS on attempt 1**, October 21, 2026, Slurm job **54468692**. Claude Sonnet 4.6 (`us.anthropic.claude-sonnet-4-6`, Bedrock `us-east-1`) changed the provider body from `y := x - 1` to `y := x + 1`. The signature and contract were preserved, and `Client.dfy` remained byte-for-byte unchanged. Provider, client-only, and whole-repository checks all exited 0; whole-repository output was **2 verified, 0 errors**. The pilot stopped immediately, using **1 of the authorized maximum 5 calls**; the other four were not dispatched.

Usage: **1,110 input + 56 output = 1,166 tokens**; billing cost not captured. This is a model-generated repair, separate from the assistant-authored reference control above. The assistant read the generated source and confirmed it matches the baseline apart from whitespace. See [preservation review](model-preservation-review.json), [call ledger](model-repair-001/ledger.json), [exact prompt](model-repair-001/attempt-01/prompt.json), [response](model-repair-001/attempt-01/response.json), and [whole-repository output](model-repair-001/attempt-01/whole_repository-stdout.txt).

The [protocol](model-repair-001/protocol.json) records versions, original repository revision, and the 4,096-output-token cap. [Model batch stdout](model-batch-54468692.log) and [stderr](model-batch-54468692.err) capture execution. The key handoff was deleted at load, and the runner cleared its environment at completion. No credential is archived.

## Evidence and reproduction

- [Original fixtures](fixtures/) and [exact executed snapshots](verification-001/fixtures/).
- [Concise trial log](TRIALS.md).
- [Per-check outcomes, commands, hashes, and timings](verification-001/results.json); [summary](verification-001/summary.json).
- [Raw verifier output](verification-001/checks/), [batch stdout](batch-54468117.log), and [batch stderr](batch-54468117.err).
- [Verifier runner](run_verification.py), [model runner](run_model_repair.py), [edit policy](repair_guard.py), and [offline tests](test_repair_guard.py).

From the repository root with the documented Dafny/Z3 environment active:

```bash
python experiments/two-module-001/test_repair_guard.py
python experiments/two-module-001/run_verification.py --output outputs/two-module-verification-new
```

Use a new output directory; existing evidence is never overwritten. The model runner's original staged environment uses `outputs/two-module-001/verification-001` as its precondition and the repository-root credential helper at `experiments/repair-003/runner.py`. Model runs require a separate explicitly bounded budget and private credential handoff. The runner refuses to overwrite an existing output directory and records each dispatch before making a request; it does not silently retry or automatically resume.

## Interpretation and remaining work

This validates the whole-repository verifier boundary and protection of a simple API/client pair. The fault and repair are elementary, and the model can solve them from the local provider contract alone. A successful repair is therefore an end-to-end infrastructure result, **not evidence of difficult cross-module reasoning**.

Next: generalize the manifest/context builder and edit protection beyond this single fixture; introduce tasks whose solutions actually require dependency or shared-lemma context; build matched controls with comparable module/specification counts and approximate size; then vary dependency depth, API reuse, and shared proofs as planned in Weeks 5–6. The multi-module milestone remains partial until these capabilities are generalized.
