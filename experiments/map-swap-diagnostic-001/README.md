# Separate map-swap and parser diagnostics

**No new model calls. The original varied-calibration score remains 27/32.**
This experiment investigates the four deep-map proof failures and the shallow
map body-policy rejection without modifying the original pilot, its frozen
prompts/guard, or any original candidate and score. Verification results are
pending; all hypotheses below are prospective.

## Six verifier-only checks

| Diagnostic | Parent | Change | Expected |
| --- | --- | --- | --- |
| `deep_shared_both` | trial 05 (same proof as 24) | Add original-map observations at both `k` and `j` inside the existing quantified proof | Strict pass |
| `deep_separate_both` | trial 15 (same proof as 30) | Same two calls in each of the two helper bodies | Strict pass |
| `deep_shared_k_only` | trial 05 | Add only the observation at `k` | Proof failure |
| `deep_shared_j_only` | trial 05 | Add only the observation at `j` | Proof failure |
| `quantifier_original` | trial 27 | Accept the exact saved response under a separate quantified-expression policy; no proof text edits | Strict pass |
| `quantifier_false_control` | trial 27 | Add `assert forall fresh :: fresh == 0;` to one helper under the new policy | Proof failure |

The deep-map hypothesis is that the outer swap at query `q == k` needs the first
swap's value at `j`, and conversely at `q == j`. The original calls instantiate
only the current `q`. [cases.json](cases.json) and [responses](responses) record
the exact additions; all sources are under [fixtures](fixtures). These are
analyst-authored sufficient-edit hypotheses. Single-fact controls test this
particular proof, not minimum necessary calls for all possible proofs. Repeated
identical originals are reused as existing evidence, not independently rerun.

## Separate parser revision

[policy/body_guard.py](policy/body_guard.py) copies the frozen old guard and adds
one narrowly scoped syntax branch: `forall fresh :: expression`. The single
binder must be fresh, cannot shadow parameters/locals/module aliases, and is
removed from scope after its expression. Existing size, nesting, edit-boundary,
allowed-call and immutable-source rules remain. Typed/multiple binders, trigger
attributes, hidden calls and assumption/verification bypasses remain outside
the admitted language. Syntax admission does not establish a proposition's truth.

The [old guard copy](policy/old_body_guard.py) and unchanged
[JSON extractor](policy/extract_response.py) remain available for comparison.
This is a diagnostic policy, not a change to the original pilot or a newly
approved future collection protocol. The saved trial 27 body strings and raw
response are used byte-for-byte; semantic validity still requires Dafny.

## Offline validation and preservation

Seven test methods pass: exact six-case construction; all 32 saved responses
(31 old-admitted candidates unchanged, one newly admitted exact body); all 110
semantic fixture reconstructions plus 16 hidden-export rejections; quantifier
scope/limit attacks; immutable-source/envelope protection; AST evidence that
only the version and one expression branch change; and isolated fake-process
runtime checks. See [offline-tests.log](offline-tests.log) and
[test_design.py](test_design.py). No test dispatches a model or real verifier.

[pre-submission-tests-001](pre-submission-tests-001/README.md) preserves an initial
local test failure in remote-script quoting, fixed before staging or submission.
No mathematical fixture or model evidence was changed by that fix.

[original-pilot-sha256.json](original-pilot-sha256.json) pins every original pilot
file; [original-input-sha256.json](original-input-sha256.json) pins copied source
and response origins. The compute runner checks its manifest and all candidate
hashes, verifies full workspaces once each with the existing strict warning
policy, records all diagnostics, and has no automatic retries or requeue. It
runs only in a Slurm compute allocation on a live-confirmed nonpreemptible
partition. No API transport, keys, or paid scope is involved.

Offline reproduction: `python3 -B experiments/map-swap-diagnostic-001/test_design.py`.
The preparation script intentionally refuses to overwrite existing inputs.
