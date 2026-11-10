# Separate map-swap and parser diagnostics

**No new model calls. The original varied-calibration score remains 27/32.**
This experiment investigates the four deep-map proof failures and the shallow
map body-policy rejection without modifying the original pilot, its frozen
prompts/guard, or any original candidate and score. **Complete:** both added-fact
repairs and the unchanged parser-rejected response verify strictly. Two one-fact
controls and the corrected false assertion fail proof checking as intended.
The [combined review](diagnostic-review.json) links six current checks across
two jobs, preserving the first run's malformed control. The table below records
the initial pre-run expectations; the last control was explicitly revised.

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

## First compute run: five expected outcomes, one malformed control

Job **59527654** completed all six checks on nonpreemptible `test` in 41 seconds.
Both added-fact repairs and the unchanged trial 27 response verified strictly:
14 obligations, zero errors and no warnings each. Both one-fact ablations failed
the original quantified postcondition as intended. The false-assertion control
used `fresh`, a reserved Dafny keyword: the new guard admitted it syntactically,
but Dafny rejected the binder before proof checking. That parse error is preserved
and is not counted as a successful negative reasoning control.

[verification-001](verification-001), [review](verification-001-review.json),
[stdout](verify-59527654.log), [stderr](verify-59527654.err) and
[accounting](accounting-59527654.txt) retain the full failed-run evidence. A
deliberate [revision-002](revision-002/README.md) changed only this control's
binder to `badKey0` and ran that one control; the five unchanged reviewed
observations are reused, not rerun or represented as independent new trials.

## Final findings and evidence

- **Missing map facts:** adding `O2.SwapAt(m, k, j, k)` and
  `O2.SwapAt(m, k, j, j)` repairs the shared proof and both separate bodies.
  Each complete workspace verifies 14 obligations with zero errors and warnings.
  Either single addition alone leaves the original quantified postcondition
  unproved in the tested shared body. These are sufficient repairs of these
  saved proofs, not a minimum-proof claim or new model successes.
- **Output-policy limitation:** the exact saved trial 27 raw response and proof
  strings verify 14 obligations, zero errors and warnings under the separate
  diagnostic guard. No proof rewrite is needed. The original policy rejection
  and 27/32 model score remain unchanged; this is post-hoc diagnostic evidence.
- **False assertions still require proof:** corrected-control job **59528781**
  completed in six seconds on nonpreemptible `test`, returning exit 4 with an
  assertion failure. It also emits one missing-trigger warning, recorded
  separately; it is not a warning-only outcome or a strict pass. The original
  `fresh` binder parse error remains archived. The guard checks bounded syntax
  and scope, not all Dafny keyword/type rules or logical truth.

The combined evidence contains **three strict diagnostic passes and three
expected proof failures**. There were seven actual verifier invocations: six
in the initial run and one deliberately corrected control. No successful or
unchanged proof was rerun, and no retry loop was used.

[diagnostic-review.json](diagnostic-review.json) records exact input and output
hashes, all **1,846 unchanged original pilot files**, 645 original parent inputs,
807 transferred evidence files, 52 protected-file comparisons and 11 body-boundary
checks across both runs. The original guard/envelope are unchanged. Both original
deep shared responses have identical bodies, as do both deep separate responses;
the tested representatives cover those saved texts without claiming independent
new trials for their duplicates.

Reproduce this offline cross-run audit with
`python3 -B experiments/map-swap-diagnostic-001/review_diagnostics.py`;
[preservation-review.log](preservation-review.log) records its result. It checks
the saved evidence without invoking Dafny or a provider.

The corrected run's [review](revision-002/verification-001-review.json),
[full sources and verifier log](revision-002/verification-001/),
[stdout](revision-002/verify-59528781.log), [stderr](revision-002/verify-59528781.err),
[accounting](revision-002/accounting-59528781.txt) and
[submission](revision-002/submission.json) are retained separately. All code,
local/remote offline logs, original responses and the initial test/runtime failure
evidence remain available. No new model calls were made.
