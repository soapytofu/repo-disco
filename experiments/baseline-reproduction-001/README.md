# Dafny baseline reproduction preparation

Prepared October 28, 2026. **Zero-model preflight submitted as job 55802277. No model calls made.**

## Proposal milestone versus exact paper reproduction

The proposal's Weeks 1–2 asks for **a baseline generation/evaluation run**, not
reproduction of every published numerical result. First complete a bounded run
on the pinned public snapshot. The exact-paper comparison below remains separate.
A different eligible count is a disclosed deviation, not a reason to block every
small run. The user subsequently asked to run the proposed at-most-20-call smoke.

`baseline_smoke.py` prepares exact prompts after preflight completes, using this
checkout's repair prompt, CodeOutputParser and diff logic. Explicit smoke settings:
Opus 4.5 via Bedrock, temperature 1.0, maximum 4,096 output tokens, no explicit top-p
or thinking configuration, SDK total attempts one. These are our settings, not
claimed paper evaluation settings. Six runner and ten request-adapter tests pass
with fake transports. The actual Cannon boto3/botocore 1.43.115 Stubber check
and langchain-core 1.6.10 parser import also passed without network requests
(see sdk-preflight.log). All 71 staged runtime files match local hashes.
No model requests have been made yet.

`bounded_requests.py` durably reserves each request, checks per-call deadlines,
and closes after ambiguous failure. Single owner only; no independent concurrent
worker budgets. Old frozen implementations remain unchanged. The fixed smoke-001
output refuses restart. Ground-truth solutions never enter model context.

After preflight review, run `python baseline_smoke.py prepare --dataset PATH
--preflight PATH`, review/publish frozen-smoke-001 and bind authorization to its
hash. Then `python baseline_smoke.py run` runs only on a compute node and consumes
the private key handoff without logging it. External include tokens are
conservatively rejected before candidate verification, with a separate outcome.
Every verified candidate still needs manual contract/implementation review;
verification alone is not faithful-annotation success.

SDK references: [Converse](https://docs.aws.amazon.com/boto3/latest/reference/services/bedrock-runtime/client/converse.html),
[Bedrock API keys](https://docs.aws.amazon.com/bedrock/latest/userguide/api-keys-use.html).

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
   with the paper's problem set. Resolve mismatches before claiming exact paper
   reproduction; disclose deviations in the bounded smoke.

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
- The later run request covers the proposed at-most-20-call smoke. The full
  2,220-call comparison remains unapproved. Never retry uncertain requests.

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

## Scheduling adjustment (October 28)

At the user's request, pending job 55802277 was updated in place from
shared/sapphire to **test alone**. No duplicate submission, cancellation, resource
reduction, or time-limit change. Requeue remains disabled. Live cluster inspection
confirmed test PreemptMode=OFF, PriorityTier=5 and 12-hour maximum; both small
verifier-only jobs fit its limits. Original submission files are preserved; the
update command and before/after scheduler state are in scheduling-adjustment-001.json.
Harvard forbids combining test with other partitions. The paid continuation still
targets shared/sapphire.

Reference: [FASRC running jobs](https://docs.rc.fas.harvard.edu/kb/running-jobs/#test).

## Reviewed preflight and frozen smoke

Job 55802277 completed on test in **12m11s**, zero model calls. All 1,567 input
hashes, report classifications, source/tool versions and deterministic ordering
were checked by review_preflight.py. The pinned legacy filter yields **555**
eligible inputs, matching the paper count; exact paper identity remains unknown.
There are 72 eligible inputs with non-proof exits. The fixed first 20 contain
17 proof failures and three parse failures; these are retained, not replaced.

The legacy success heuristic searches for the substring `0 errors`, rather than
requiring exit zero or parsing the final error count. legacy-classification-audit.json
separates warning-related nonzero exits and substring false positives. This is
preserved for reproduction and reported alongside strict outcomes; it must not
be treated as sound proof success. Candidate/specification review remains required.

frozen-smoke-001 contains the exact twenty sources, initial diagnostics, final
prompts, explicit settings and code hashes. Ground-truth sources are excluded
from prompts. The input dataset's Apache license is retained as DafnyBench-LICENSE.txt.
Full preflight logs and archive hashes are saved. Both preflight gates are now
reviewed, and the bounded combined continuation is ready for one submission.

## Completed bounded baseline

Job 55807561 completed all twenty frozen requests without retries. Legacy score
7/20; strict exit-zero score 6/20; nine patch rejections, three proof failures,
one warning-only nonzero exit and one remaining front-end failure. See
[specification-review.md](specification-review.md) and the full smoke-001 archive.
This satisfies the initial bounded evaluation-run milestone, not full paper reproduction.
