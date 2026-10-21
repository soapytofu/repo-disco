# Experiment log

A concise record of what we tried, which program changed, and what the evidence supports. Last updated October 21, 2026.

## Integer-maximum program: generation → extension → repair

These are successive experiments on **one program family**, not independent benchmark problems.

| Experiment | Date | Question | Model / provider | Outcome |
| --- | --- | --- | --- | --- |
| [pilot-001](pilot-001/README.md) | 2026-10-14 | Can we generate and verify an integer maximum utility? | `gpt-5.6-luna` / OpenAI | **PASS:** 2 verified, 0 errors |
| [extension-001](extension-001/README.md) | 2026-10-14 | Can we extend it with algebraic properties? | `gpt-5.6-luna` / OpenAI | **FAIL — parse error:** declarations split a method signature from its body |
| [repair-001](repair-001/README.md) | 2026-10-20 | Can Claude repair the failed extension using verifier feedback? | `us.anthropic.claude-sonnet-4-6` / AWS Bedrock | **FAIL — parse error:** malformed diff anchors led to incorrect brace deletion |
| [repair-002](repair-002/README.md) | 2026-10-20 | Can a fresh attempt follow clarified anchor syntax with strict validation? | `us.anthropic.claude-sonnet-4-6` / AWS Bedrock | **FAIL — malformed edit rejected; input unchanged.** 885 input / 166 output tokens |
| [repair-003](repair-003/README.md) | 2026-10-20 | Can a complete-program response repair the same input? | `us.anthropic.claude-sonnet-4-6` / AWS Bedrock | **PASS:** 4 verified, 0 errors after verifier-only recheck; 541 input / 372 output tokens |

All three repair trials start from the original failed extension. They do not continue one another's modified output.

**What the programs contain**

- **Generation:** `Max(a, b)` returns one of its inputs and is at least as large as both. `TestMax` checks those properties. [Verified code](pilot-001/verified-program.dfy).
- **Extension:** adds `MaxCommutative` and `TestMaxAlgebra`, attempting commutativity, idempotence, and associativity. The file fails parsing, so these additions are **not verified**. [Failed code](extension-001/extended-program.dfy) · [Verifier error](extension-001/verifier-output.txt).
- **Repair:** Claude proposed moving the separated method body, but malformed diff anchors were silently ignored by the patch code. The resulting file still fails parsing. [Failed repair](repair-001/failed-repair.dfy) · [Diagnosis and evidence](repair-001/README.md).
- **Fresh repair-002:** the clarified prompt still produced malformed anchors, which the fixed reader rejected before any change or new Dafny verification. [Recorded prompt and result](repair-002/README.md).
- **Complete-program repair-003:** one model request produced a complete source file retaining the intended specifications. The first verifier call timed out; the unchanged file then passed with a longer limit. [Verified output and evidence](repair-003/README.md).
- **Diagnostic candidate (not a model trial):** adding the two missing anchor delimiters restores the intended block arrangement. [Candidate](repair-001/anchor-normalization-candidate.dfy); **PASS — 4 verified, 0 errors**, reported from Cannon on 2026-10-20. [Verifier output](repair-001/anchor-normalization-verifier-output.txt). Original contracts and intended algebraic checks are retained; no additional model call.

## Paired repair-format pilot

| Experiment | Date | Question | Model / provider | Outcome |
| --- | --- | --- | --- | --- |
| [format-comparison-001](format-comparison-001/README.md) | 2026-10-20–21 | Does response format affect repair reliability across five small Dafny cases? | `us.anthropic.claude-sonnet-4-6` / AWS Bedrock | 50 calls: complete programs **25/25 verified**; custom diffs **13/25 verified, 12 patch rejections**; 28,600 tokens |

Five cases × two formats × five repetitions. The maximum case reuses the earlier pilot; these are not 50 independent problems. All 38 verified candidates match reviewed reference repairs apart from whitespace. [Per-trial log](format-comparison-001/TRIALS.md) · [Raw evidence and limitations](format-comparison-001/README.md) · [Proposal timeline and next milestone](../docs/research-progress.md).

## Two-module repository prototype

| Experiment | Date | Question | Outcome |
| --- | --- | --- | --- |
| [two-module-001](two-module-001/README.md) | 2026-10-21 | Can the harness distinguish client-only verification from full-repository validity and protect a two-module API? | **12/12 expected verifier outcomes**, 6 offline edit-policy tests; zero model calls in the deterministic run. Claude repair pilot authorized up to 5 calls, awaiting private credential handoff. |

The implementation-bug control passes client-only verification but fails whole-repository verification; the weakened-contract control fails the unchanged client. Neither a local pass nor a weakened specification counts as an accepted repair. This is a minimal infrastructure fixture, not a repository benchmark.

## Setup checks

These establish that the tools work; they are not research benchmark results.

| Check | Recorded result | Evidence |
| --- | --- | --- |
| Dafny sample `language/dafny/examples/max.dfy` | 1 verified, 0 errors | Terminal output reported in setup; [instructions](../docs/setup/README.md#3-dafny-4110-and-z3) |
| Diff / prompt formatter tests | 17 passed | Terminal report |
| Dafny verification tests | 8 passed | Terminal report |
| OpenAI connection | Successful | Terminal report; no generation in this check |
| AWS Claude connection, 2026-10-20 | Successful; 13 input + 5 output tokens | Terminal report; [test and output](../docs/setup/README.md#small-connection-test) |

The setup sample and generated pilot are separate files, despite both involving maximum utilities.

## Engineering validation

[patch-validation-001](patch-validation-001/README.md), 2026-10-20: the patch reader now rejects malformed or unmatched edit directives, and prompts explicitly require both anchor delimiters. **39 tests passed on Cannon; the assisted candidate remained at 4 verified, 0 errors.** No model calls were made. This is an infrastructure validation, not another generation/repair trial.

## How to record future experiments

Copy [the short record template](TEMPLATE.md) into a new experiment directory. Add one row above and link the actual input/output program, resolved configuration, model response, and verifier output. Retain failed attempts as well as successes.

- Use a distinct experiment ID and name the parent experiment.
- Record the exact model ID, provider, attempt budget, source revision, and environment versions.
- Record token usage and measured cost when available. Write **not captured** when unavailable; do not infer cost from an output-token limit.
- Distinguish a verifier pass from a review that the specifications and intended task were preserved.
- Keep secrets out of all records. Raw checkpoints remain in ignored `outputs/`; readable evidence belongs here.
- Do not rerun an experiment solely to reconstruct missing metadata. State the gap and capture it on subsequent runs.

These pilots do not yet constitute a baseline reproduction, a model comparison, or a multi-module evaluation.
