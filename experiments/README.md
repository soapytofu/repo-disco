# Experiment log

A concise record of what we tried, which program changed, and what the evidence supports. Last updated October 23, 2026.

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
| [two-module-001](two-module-001/README.md) | 2026-10-21 | Can the harness distinguish client-only verification from full-repository validity and protect a two-module API? | **12/12 expected verifier outcomes**, 6 offline edit-policy tests; zero model calls in the deterministic run. Claude repair succeeded on **1 call**; protected client unchanged; whole repository **2 verified, 0 errors**; 1,166 tokens. |

The implementation-bug control passes client-only verification but fails whole-repository verification; the weakened-contract control fails the unchanged client. Neither a local pass nor a weakened specification counts as an accepted repair. This is a minimal infrastructure fixture, not a repository benchmark.

## Exported-lemma context pilot

[context-pilot-001](context-pilot-001/README.md), October 21, 2026: an opaque-function proof task with a protected provider and an editable client proof. **12/12 control checks matched expectations; 7 offline checks passed.** Completed October 22: **API context 4/4 verified; local-only 0/4**, with all failures due to nonexistent guessed helper names. Eight calls, 3,883 tokens; no edit rejections or retries. [Model trial log](context-pilot-001/TRIALS.md). [Verifier control log](context-pilot-001/VERIFICATION.md).

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

These pilots do not yet constitute a published-baseline reproduction, a comparison across models, or a representative repository benchmark. The multi-module context pilots below are small controlled demonstrations.

## Three-task composition pilot (October 22)

[composition-pilot-001](composition-pilot-001/README.md) builds range/precondition chaining, relation lifting, and sequence-property composition tasks. Both conditions receive complete source/contracts; one adds only a structural import map. Six offline checks passed. All 15 corrected verifier controls matched expectations on October 23 after fixing export aliases; the original failed run is preserved. The completed 12-call pilot achieved full context **6/6** and full context plus map **6/6**; all accepted proofs matched references ignoring whitespace, with protected source unchanged. This ceiling result supplies no measured map advantage. [Trial log](composition-pilot-001/TRIALS.md). This work targets basic composition with known APIs rather than hidden-helper-name discovery.

## Multi-client shared-proof controls (October 23)

| Experiment | Model calls | Verified result | Interpretation |
| --- | --- | --- | --- |
| [shared-proof-001](shared-proof-001/README.md) | 0 | **16/16 expected outcomes**: both clients pass with one shared lemma; weakening its guarantee breaks both; removing one client call affects only that client | Dependence of two distinct client reference proofs on a shared provider guarantee |
| [sharing-control-001](sharing-control-001/README.md) | 0 | **22/22 expected outcomes** on the completed shared-partition rerun; original preempted evidence preserved | Matched fixed-proof dependency footprints; equivalent helpers permit alternative proofs, so this is not yet a forced model reasoning treatment |

## Reproducibility and metric audits

- [Import-map audit](map-audit-001/README.md): three composition maps each have import depth two. This does not infer proof depth.
- [Proof-call audit](proof-usage-audit-001/README.md): 12 successful composition trials represent three client targets, not 12 independent targets or evidence of cross-client sharing. The later multi-client controls above address that representation gap.
- [Archive integrity checks](../docs/archive-integrity.md): read-only SHA-256 verification, separate from scientific validity.
- [Matched corpus design](../docs/controlled-corpus-design.md): proposed controls and metrics for Weeks 5–6, not completed model findings.

## Reasoning-sensitive sharing controls

[sharing-reasoning-001](sharing-reasoning-001/README.md) confirms 46 intended verifier outcomes: reference proofs pass; omitted steps, wrong arguments, and unavailable preconditions fail; hidden alternate helpers produce separately classified resolution errors. The batch reported failure because of a four-case diagnostic wording mismatch (raw 42/46); offline review with a corrected matcher confirms 46/46 without rerunning Dafny. Raw evidence is preserved. No model calls. This validates the fixture, not a model reasoning or sharing-performance claim.

## Eight-call sharing pilot preparation and completion

[sharing-model-pilot-001](sharing-model-pilot-001/README.md) freezes eight proposed independent two-client trials (four shared, four separate), exact prompts and alternating order. Nine offline tests and 12 compute preflight checks pass; reference JSON repairs verify and both exact empty-proof inputs fail as expected. Full preflight logs are archived. The user later authorized eight calls; the bounded adapter completed exactly eight without retries. Both conditions had 0/4 accepted responses: all eight included prose before JSON and were rejected before verification. This is a format failure, not a proof-correctness result. Raw responses and the dispatch ledger are archived alongside the unchanged frozen plan.

## Depth × sharing pilot completed (October 25 Eastern)

[Eight-trial pilot](sharing-depth-pilot-001/RESULTS.md): diamond shared 2/2, diamond separate 2/2, nested shared 2/2 and nested separate 2/2. All 24 verifier checks passed using the frozen tolerant parser, with protected source unchanged. Eight distinct requests, no retries, 15,843 total tokens. This is another ceiling result, not evidence of a sharing advantage. Current work remains Weeks 3–4 repository infrastructure and Weeks 5–6 controlled-corpus preparation; published-baseline reproduction, broader held-out evaluation and multi-model comparisons remain outstanding. Next non-paid work should introduce different proof obligations rather than only longer versions of this template.
