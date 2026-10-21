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

Model execution status and results will be recorded separately from the deterministic reference repair. A private key handoff is required before dispatch; it is deleted on loading and never added to the archive.

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
