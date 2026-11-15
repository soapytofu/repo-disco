# Five analyst repairs: all verify, original score unchanged

**5/5 separately labeled analyst candidates strictly verify. Zero model calls.**
Job `60703825` completed in 27 seconds on the live-confirmed nonpreemptible `test`
partition, with no requeue or retry. The original model result remains **27/32**;
these are sufficient analyst edits to five saved failures, not new model successes
or a claim that the edits are minimal.

| Original trial | Only analyst change | Verified obligations | Errors / warnings |
| --- | --- | ---: | --- |
| 03, witness shared | Choose `u = max(a, c-gap)` instead of `u = a` | 9 | 0 / 0 |
| 15, witness separate | Same declaration change in both bodies | 9 | 0 / 0 |
| 05, arithmetic separate | Guard the two leading `O.Low` calls with their sum bounds | 7 | 0 / 0 |
| 09, arithmetic shared | Same guards on the two leading calls | 7 | 0 / 0 |
| 28, arithmetic separate | Same guards in both bodies | 7 | 0 / 0 |

The witness bodies retain `v := u + gap` and every subsequent statement. The
arithmetic bodies retain their later case proofs. All original lemma calls,
arguments and call order remain unchanged; only the leading declaration or
conditional guards change. The original frozen parser and body guards admit all
five candidates. All 29 protected files and eight body boundaries match exactly.

The [review](runtime-002/results-review.json) confirms the complete **1,845-file**
primary model archive is unchanged and all 91 copied parent inputs match. Source,
named provider/helper/client CSV results, raw diagnostics and scheduler bindings
were checked. All 358 files in the [retrieved archive](runtime-002/) match their
transfer hashes. Full parent requests/responses, exact edits, candidate sources,
verifier logs and accounting are preserved separately from the primary results.

## Packaging failure preserved

The first staged manifest omitted `frozen-001/policy/README.md`, although the
original policy freeze requires it. Three of six remote offline packaging tests
failed before any Dafny invocation; no job or model request was submitted for that
package. The original manifest, staging record and full failed log remain at the
experiment root and are copied under `runtime-002/first-package/`.

The deliberate `runtime-002` revision includes every frozen input. All 337
preexisting package files and 37 candidate sources remain unchanged. Its
manifest-only temporary staging test and six remote self-contained tests pass;
the three local original-archive/reviewer tests affected by the nested path also
pass. Scheduler and local archive-lookup paths are the only copied runtime source
changes. No mathematical repair was revised after observing these verification
results. The pinned pre-run READMEs retain the original pending status; this file
records the completed result.

These diagnostics support the observed endpoint and precondition explanations for
the five failures. They do not establish model repair success, independent
task-level success rates, necessary proof depth or a general feedback/sharing
effect. The active research window still has **32/128** model calls used.
