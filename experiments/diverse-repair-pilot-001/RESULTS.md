# Diverse repair pilot results

Job **60343569** completed on nonpreemptible `test` in **6m17s**. All **24 authorized requests** returned with unique provider IDs and **zero SDK retries**. The closed ledger records 24 reservations and 24 dispatches, with no unused or reassigned calls. Usage: **47,956 input + 16,142 output = 64,098 tokens**.

## Primary outcome under the frozen protocol

| Development instance | Verifier diagnostics | Failure notice only | Total strict repairs |
| --- | ---: | ---: | ---: |
| Threshold composition | 4/4 | 4/4 | 8/8 |
| Excluded-value witness | 4/4 | 4/4 | 8/8 |
| Weave/unweave | 0/4 | 0/4 | 0/8 |
| Total | **8/12** | **8/12** | **16/24** |

Every family × sharing × feedback cell has two responses. Arithmetic and witness cells all achieve 2/2; sequence cells all achieve 0/2. Shared and separate each total 8/12. All eight primary failures are **envelope extraction rejections**, before the body guard and before Dafny; there are no submitted-candidate proof failures, warning-only exits or truncated outputs in this batch. Each of the 16 admitted candidates verifies six obligations with strict exit 0, zero errors and zero warnings. All 16 complete revisions were atomically promoted; the eight rejected trials retained their original HEAD.

There are **three semantic instances, six unique constructed failing workspaces and 12 unique payloads**, each sent twice. These are not 24 independent mathematical tasks. This batch shows successful repair of two constructed fault types, but **does not show an advantage from verifier diagnostics or sharing**. A tie on this small selected collection is not evidence of general equivalence. Do not pool these scores with the earlier natural map-failure repair comparison (4/4 versus 1/4), whose archives and scores remain unchanged.

## What changed in successful repairs

- Threshold composition: all eight repairs restore the missing intermediate saturation case, selecting `Below` or `Above` only when the corresponding precondition holds. Some use nested branches; others use a three-way chain.
- Excluded witness: all eight repairs choose endpoint `a` if it differs from `e`, otherwise endpoint `b`. The unchanged `a < b` precondition makes the second endpoint distinct. They call `Bounds` then `Finish`, preserving the original existential goal. This differs from the reference's `a+1` construction and is verified against the same contracts.
- Seven of the eight admitted separate-condition responses use byte-identical helper bodies. Across 16 admitted trials there are 15 distinct complete candidate workspaces. Copying is permitted; this does not establish independent proof discovery or a causal sharing effect.

The source review checks **96 immutable-file comparisons and 24 protected body boundaries** for admitted candidates, plus all 24 original revisions and their frozen source hashes. Declaration evidence records 24/24 editable-helper observations and 32/32 dependency-closed client observations for admitted candidates. These are components of the 16 workspace successes, not additional independent successes; rejected outputs receive no verification credit.

## Sequence-output limitation, separately diagnosed

The frozen extractor rejected five responses as `Multiple JSON containers` and three as `Malformed or duplicate-key JSON container`. Inspection shows that **all eight responses contain one valid fenced JSON object with the exact expected filenames**. The extractor fails earlier in explanatory prose: sequence indices/slices such as `[0]`, `[]` and `[1..]` resemble JSON arrays to its whole-response scan. This is an interaction between extra model prose and the conservative envelope scanner, not evidence that the final fenced JSON itself is malformed.

The [read-only content audit](content-audit.json) records exact response hashes, rejection offsets/snippets and fenced-object locations. All eight fenced bodies visibly include the missing tail-recursive call. **Their proofs have not been admitted or verified in this pilot.** The post-run audit makes zero API calls, creates no repaired candidate, and runs no Dafny. It does not change the parser, rescore responses, or convert these failures into successes. Any isolated extraction/verification diagnostic must retain these primary results and be labeled separately.

This prevents a substantive induction-repair comparison from this run. The useful next step is an offline, separately reported extraction diagnostic on the saved responses before spending further calls. Broader task selection and fresh evaluation remain necessary before a general feedback, sharing or depth claim. These are author-developed instances, not held-out families; fixed interfaces provide no numeric dependency-depth comparison.

## Evidence and reproduction

- [Frozen proposal](../diverse-repair-plan-001/README.md), [runtime freeze](runtime-freeze.json), [authorization](authorization.json), [submission](submission.json), [Slurm accounting](accounting-60343569.txt).
- [Reviewed per-trial results](reviewed-results.json) and [reproducible audit](review_results.py); `python3 -B experiments/diverse-repair-pilot-001/review_results.py` is offline and makes no calls.
- [Full raw model archive](model-001/): exact payloads and raw responses, provider IDs/usage, extraction decisions, candidates, full verifier stdout/stderr and byte-exact CSV, original and accepted store revisions, runtime/input copies, [closed request ledger](model-001/requests/ledger.json), environment and summary.
- [Model log](model-60343569.log), [stderr](model-60343569.err), [transfer inventory](transfer-001.json), [1,204-file raw archive manifest](model-001-sha256.json).
- [Source diffs](source-diffs.patch), [read-only content reviewer](audit_outputs.py), [implementation and prior-archive preservation](implementation-preservation.json).
- [20 local offline tests](runner-tests.log) and [20 Cannon offline tests](environment-preflight.log); fake SDK/processes only. Frozen proof policy, prompts, order and old experiment files remain unchanged; all 587 files in the preceding eight-call raw model archive match their published manifest.

The approved 24-call budget is exhausted. No retries, extra connectivity calls, alternative model runs or new experiment budget were used.
