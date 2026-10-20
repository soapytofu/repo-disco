# Experiment log

A concise record of what we tried, which program changed, and what the evidence supports. Last updated October 20, 2026.

## Integer-maximum program: generation → extension → repair

These are successive experiments on **one program family**, not three independent benchmark problems.

| Experiment | Date | Question | Model / provider | Outcome |
| --- | --- | --- | --- | --- |
| [pilot-001](pilot-001/README.md) | 2026-10-14 | Can we generate and verify an integer maximum utility? | `gpt-5.6-luna` / OpenAI | **PASS:** 2 verified, 0 errors |
| [extension-001](extension-001/README.md) | 2026-10-14 | Can we extend it with algebraic properties? | `gpt-5.6-luna` / OpenAI | **FAIL — parse error:** declarations split a method signature from its body |
| [repair-001](repair-001/README.md) | 2026-10-20 | Can Claude repair the failed extension using verifier feedback? | `us.anthropic.claude-sonnet-4-6` / AWS Bedrock | **FAIL — parse error:** malformed diff anchors led to incorrect brace deletion |

**What the programs contain**

- **Generation:** `Max(a, b)` returns one of its inputs and is at least as large as both. `TestMax` checks those properties. [Verified code](pilot-001/verified-program.dfy).
- **Extension:** adds `MaxCommutative` and `TestMaxAlgebra`, attempting commutativity, idempotence, and associativity. The file fails parsing, so these additions are **not verified**. [Failed code](extension-001/extended-program.dfy) · [Verifier error](extension-001/verifier-output.txt).
- **Repair:** Claude proposed moving the separated method body, but malformed diff anchors were silently ignored by the patch code. The resulting file still fails parsing. [Failed repair](repair-001/failed-repair.dfy) · [Diagnosis and evidence](repair-001/README.md).
- **Diagnostic candidate (not a model trial):** adding the two missing anchor delimiters restores the intended block arrangement. [Candidate](repair-001/anchor-normalization-candidate.dfy); **PASS — 4 verified, 0 errors**, reported from Cannon on 2026-10-20. [Verifier output](repair-001/anchor-normalization-verifier-output.txt). Original contracts and intended algebraic checks are retained; no additional model call.

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

## How to record future experiments

Copy [the short record template](TEMPLATE.md) into a new experiment directory. Add one row above and link the actual input/output program, resolved configuration, model response, and verifier output. Retain failed attempts as well as successes.

- Use a distinct experiment ID and name the parent experiment.
- Record the exact model ID, provider, attempt budget, source revision, and environment versions.
- Record token usage and measured cost when available. Write **not captured** when unavailable; do not infer cost from an output-token limit.
- Distinguish a verifier pass from a review that the specifications and intended task were preserved.
- Keep secrets out of all records. Raw checkpoints remain in ignored `outputs/`; readable evidence belongs here.
- Do not rerun an experiment solely to reconstruct missing metadata. State the gap and capture it on subsequent runs.

These pilots do not yet constitute a baseline reproduction, a model comparison, or a multi-module evaluation.
