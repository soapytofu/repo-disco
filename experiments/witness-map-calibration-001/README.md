# Proposed calibration: separated witnesses and overwrite/delete

Prepared November 6, 2026 Eastern. **16 new calls proposed; zero dispatched; execution is not authorized.** This is a prospective development difficulty/format check for two new semantic instances, each with shallow/deep interfaces and shared/separate editable proofs. It is not the 192-call main study or a held-out evaluation.

## Scope and budget

- **2 semantic instances × 4 variants × 2 fresh samples = 16 requests.** There are eight exact payloads, each reused without modification for its second sample. Eight calls would provide only one sample per variant; two samples permit a small within-prompt variability check. They still do not support a general causal sharing claim.
- Use the same pinned Bedrock Claude Opus 4.5 model ID, region, temperature 1.0 and maximum 4,096 output tokens as the preceding pilot. The maximum is **65,536 output tokens plus input**, not a dollar estimate. Exact request/prompt byte sizes are recorded; bytes are not token counts.
- One SDK attempt per reserved slot, no feedback, retries, requeue, automatic restart or reassignment of unused slots. Any future execution needs explicit approval and a separately reviewed bounded runner tied to this freeze. No provider connectivity request is included or permitted by this proposal.

[Plan](plan.json) · [Eight exact request payloads](frozen-001/requests/) · [Sixteen ordered slots](frozen-001/trials.json) · [Freeze and input hashes](frozen-001/freeze.json)

## Evidence and matching

The new tasks passed [64 verifier controls](../witness-map-strengthening-001/README.md): eight strict reference successes, 48 proof failures, eight hidden-export failures. [Eight alternative proofs](../witness-map-strengthening-001/alternative-proof-001/README.md) also passed strictly through the new envelope and guard. The interval task needs two common witnesses separated by a positive gap. The map task handles both equal and distinct update keys before deletion and must track values through intermediate maps.

All requests contain the nine-file **empty** workspace, a source-derived import/include map, allowed call signatures and the same bounded syntax instructions. Reference bodies, alternative proofs, negative controls, prior answers, reviewer dependency annotations, trial IDs and sample numbers are excluded from the payload. Contracts and both clients remain fixed. Provider-stage annotations are task-relative: witness 1/3 stages and map 2/4 stages for shallow/deep, not numerical depth parity across families or proof-minimality bounds.

Shared mode edits one body; the second helper forwards to it. Separate mode edits two bodies that may be identical. Source and output sizes differ, providers remain common, and the forwarding call adds an edge for one shared client. See [reference structure and limitations](../witness-map-strengthening-001/REFERENCE-STRUCTURE.md). These differences must be reported alongside completion rates rather than treated as a pure equal-work sharing effect.

## Order

Each eight-trial block covers all variants and alternates semantic family. At every absolute position, block 2 reverses family, depth and sharing relative to block 1. No identical request is adjacent. This is partial counterbalancing: the within-family cell order repeats between blocks and a 16-trial pilot does not balance every carryover interaction. All conversations are fresh and independent of prior answers.

## Primary outcome and stopping rules

Require the frozen single-object envelope, exact editable keys, unchanged proof strings, immutable source/contract hashes, and strict whole-workspace Dafny exit zero with `--verify-included-files All.dfy` under the pinned Dafny/Z3 toolchain (60-second limit). Allow surrounding prose/fences only when exactly one unambiguous JSON object is present. Reject duplicate keys, competing/nested objects and malformed JSON. No response rewriting or warning exemptions.

For each semantic instance × depth × sharing cell report planned, reserved, returned, extracted, body-admitted and strictly verified counts out of two. Keep absent/unattempted slots visible. Separate envelope rejection, body-policy rejection, truncation, precondition, assertion/postcondition, frontend, termination, warning-only and infrastructure outcomes. Record source hashes, response/request IDs, token use, latency, full stdout/stderr and whether separate bodies are identical.

A completed incorrect or malformed answer consumes its slot. Stop future execution on ambiguous transport/persistence errors, hash drift, missing request evidence, or verifier infrastructure/timeouts; do not retry or salvage slots. Old 18/24, 29/32 and 1/8 studies keep their original primary scores. This prospective policy is not a retroactive rescore or a basis for pooling those studies.

Before scaling, inspect genuine proof failures and possible ceiling/floor behavior by instance. If these tasks saturate, keep them as regression anchors rather than inflating the corpus with renamed copies. Mixed outcomes can guide task selection but do not by themselves estimate a population effect. Select additional independent semantic instances and reserve genuinely unseen families before main collection.

## Offline validation

Five test methods pass. `prepare.py` reproduces every frozen byte, validates order/limits, checks exact seed/specification/policy hashes, and reconstructs both original and alternative references against reviewed strict verifier records. It performs no network, model or Dafny invocation. The freeze includes policy code, task metadata, settings, requests and order; no live dispatcher or authorization file exists.

```sh
python3 -B experiments/witness-map-calibration-001/prepare.py
python3 -B experiments/witness-map-calibration-001/test_plan.py
```

[Raw offline test log](offline-tests.log). Freeze SHA-256: `ac38dd5c49d89afa70c4fa1700b6af4ec6317df639bacb66acd9257b429a4732`.
