# Dafny baseline reproduction preparation

Prepared October 28, 2026. **No model calls authorized or made; no job submitted.**

## Target and scope

First reproduce the **Claude Opus 4.5 DafnyBench logical-annotation baseline** in
Formal Disco §4.3 / Appendix A. This is a bounded downstream evaluation target,
not reproduction of the entire paper, its training, or open-ended generation.
The paper reports 555 annotation problems and caps Opus at four independent
attempts. The generation experiment is separate: 100k README seed pool, 10k Claude
task attempts, 48 worker processes, 10,000 output tokens, 0–2 documentation snippets.
Its missing original README pool remains a separate blocker for exact generation
reproduction. Finishing this evaluation must not silently mark that work complete.

Sources: [Formal Disco v1](https://arxiv.org/html/2607.04631v1),
[DafnyBench](https://github.com/sun-wendy/DafnyBench).

## Exact inputs pinned now

- DafnyBench commit `0cd28feed9cd0179b07fdb9d002f8c39063658e4`.
- 782 hint-removed files and 785 ground-truth files. Every path, byte count and
  SHA-256 is in `dataset-manifest.json`; local `dataset-audit.json` confirms them.
- Dataset checkout is outside the publishing repo at
  `research-notes/baseline-inputs/DafnyBench`; source code is not duplicated here.
- Formal Disco/RepoDisco code revision `c306a47a3d5935ef0d93b793eada954471d16280`.
  It contains local patch/parser changes, so a match to the paper's original code
  revision must also be confirmed before claiming an exact published reproduction.
- Proposed installed verifier: Dafny 4.11.0, Z3 4.12.1, 10-second timeout with
  5-second kill grace, matching this checkout's single-program execution path.
  These versions/timeouts are not yet confirmed as the paper's settings.

`run-plan.json` is the machine-readable **non-executable plan**, not a Hydra launch
configuration. Null sampling/token fields represent unresolved settings, not
permission to accept provider defaults silently. Model is the checked-in Opus 4.5
Bedrock ID, region us-east-1; availability is not yet checked in the lab account.

## Stage 1: zero-model preflight

1. Reconnect Cannon; transfer this preparation and the pinned dataset to
   `~/formal-disco/experiments/baseline-reproduction-001` and
   `~/formal-disco/inputs/DafnyBench` respectively. Preserve `.git` in the dataset.
2. Create `outputs/baseline-reproduction-001`; check existing local/remote job and
   output state before submitting `preflight.sbatch` once. No automatic retries.
3. The job hashes all input files, records tool versions, and verifies originals
   and hint-removed inputs in separate temporary directories with four CPU workers.
   No providers are imported and no key is needed.
4. Keep all raw diagnostics. Eligibility reproduces the pinned backend's
   SUCCESS exclusion; syntax errors and timeouts are separately listed, not silently
   discarded. Ground-truth results are diagnostic and do not change eligibility.
5. Freeze `eligible.json` and the first 20 deterministic hash-ordered problems for
   a smoke run. Matching the number 555 is necessary but does not prove identity
   with the paper's problem set. Resolve mismatches before paid execution.

The original cache is filename-based. This preflight does not reuse it; source
hashes and tool versions are attached to the new records. Ground-truth solutions
must never enter model prompts. Preflight validates inputs, not model performance.

## Stage 2: resolve exactness and freeze the live configuration

Ask Nada/Gabriel for (do not send automatically):

> For the Opus 4.5 DafnyBench annotation baseline, could you share the dataset/code
> revisions, the 555 evaluated problem IDs (or evaluation JSON), Dafny/Z3 versions
> and timeout, and the resolved inference settings (output-token cap, sampling and
> any thinking configuration)? For generation reproduction, is the 100k README
> seed file and its run configuration available?

Until those are available, label a run a **reimplementation on a pinned public
snapshot**, not an exact numerical reproduction. Report deviations explicitly.
Do not substitute Sonnet for Opus silently. Pin prompts using the baseline repair
prompt, example diff, CodeOutputParser and patch semantics. Each attempt uses the
original input and original feedback; no accumulating repair history. Stop at the
first verified success, as `FixerTask._fix` does. The generic config's 32 attempts
is inappropriate for the paper's Opus baseline; use four.

Before execution integrate a tested durable invocation ledger around the actual
model transport. It must disable SDK retries, count reservations before requests,
stop the entire run after ambiguous API failure, and cap total requests even when
upstream task code catches exceptions. The offline gate prototype is not yet this
live adapter. Keep task verdicts and source/specification audits separate: the
upstream diff evaluator can modify more than annotations, so report any weakening
rather than assuming verification proves faithful annotation repair.

## Call budget and stop rules

- Preflight and plan validation: **0** model calls.
- Proposed smoke run: **20** problems × one attempt = **at most 20** calls.
- Full Opus baseline, if the exact set is 555: **at most 2,220** calls (555 × 4).
  Early success reduces actual use. With N confirmed eligible problems, cap is 4N.
- The smoke requests can count as each problem's first attempt in the full run
  only if model, prompts and settings remain frozen; then the full cap still totals
  2,220, not 2,240. If settings change, preserve smoke evidence separately and
  explicitly authorize the replacement budget.
- No dollar estimate until output cap, access route and current pricing are known.
- No paid calls under this preparation request. Never retry uncertain requests.

## Acceptance and reporting

Archive the exact eligibility list, resolved config, requests/responses, request
IDs, usage, attempted patches, resulting sources and verifier outputs. Report
success at the first attempt and by attempts 2 and 4, plus syntax/patch/timeout/API
categories. Follow the paper's estimator when matching its figure; do not label
an adaptive repair trajectory as independent pass@k. Compare with the original
result only after resolving settings/data differences. New results need not match
exactly because sampling is stochastic. No training is needed for this Opus
baseline; reproducing fine-tuned Qwen results is a different project stage.

## Building the repository agent afterward

1. Start with a **single sequential repository-repair worker** on frozen tasks:
   snapshot manifest and files, build context, propose allowed edits, run frozen
   guards, then verify the whole candidate repository.
2. Add an immutable accepted-revision record and one atomic manifest-pointer
   update after success. Reject stale bases; never update files individually and
   leave a partially accepted repository. Preserve failures without promotion.
3. Connect the bounded live request ledger, task/attempt IDs and raw evidence.
   Smoke-test with fake responses and verifier controls before a paid pilot.
4. Compare single-file baseline and repository worker under matched call/token
   budgets and appropriate task scope. A DafnyBench annotation score alone is
   not a matched baseline for multi-module tasks; define that comparison separately.
5. Only then add extension tasks, generation of new modules, dependency-aware
   context selection and broader family-level evaluation. Parallel workers and
   fine-tuning come after the sequential loop is reliable.

Existing components: `language/dafny/repository.py`, `candidate.py`, frozen task
parsers/guards and multi-client metrics. Missing core piece: durable accepted
repository revision/promotion and an end-to-end bounded model worker. Do not
claim the current isolated integration tests implement that full agent.
