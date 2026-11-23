# First returned growth output: stopped resource-limited cohort

Job **63018923** completed its frozen execution policy on November 23, 2026:
one model response returned, one native check ran, and the pilot stopped on the
candidate's verifier resource failure. Its eight-slot ledger is closed. Seven
slots were never dispatched and cannot be reassigned. **There is no complete
eight-call or four-lineage score.** The earlier credential/access failures and
all historical model scores remain unchanged.

| Measurement | Observed value |
| --- | ---: |
| Returned responses / unique request IDs | 1 / 1 |
| SDK retries / ambiguous outcomes | 0 / 0 |
| Input / output / total tokens | 2,217 / 73 / 2,290 |
| Accepted additions among observed responses | 0/1 |
| Complete-pilot / lineage-completion rate | Unmeasured: stopped cohort |
| Native invocations | 1 |
| Required named units present | 268/268 |
| Original upstream units passed | 267/267 |
| New MoveToFront unit | Resource exhaustion; CSV outcome Failed |
| Native elapsed time | 74.024 seconds |
| Slurm elapsed / allocated CPUs | 314 seconds / 1 |

Only Dafny-VMC lineage 1's first stage was attempted. Vest and both second-stage
tasks were unattempted. No accepted model parent exists. The completed provider
request establishes that this invocation worked with the supplied key; it does
not guarantee future availability. The result is an actual failed extension
candidate, not an infrastructure-only absence of model output.

## Candidate and concrete counterexample

The admitted response implements the new function as:

```dafny
if k == 0 then
  xs
else
  var prev := MoveToFront(xs, k - 1);
  var swapped := Model.Swap(prev, k - 1, k);
  swapped
```

The fixed ordered-sequence postcondition requires
`[xs[k]] + xs[..k] + xs[k+1..]`. For `xs = [0,1,2]` and `k = 2`, direct
unrolling yields `[1,0,2]` at k=1, then **[1,2,0]** at k=2. The required result
is **[2,0,1]**. Length and multiset are preserved, but the requested order is not.

The [source-bound analyst trace](diagnostics/counterexample-001.py) and its
[output](diagnostics/counterexample-001.json) bind the exact saved candidate and
response hashes. It is a manual translation of this particular implementation
and the fixed Swap semantics, not a general Dafny evaluator, native verifier
rerun, model repair or change to the original native classification. The failure
occurred despite the exact target contract and full existing Swap source being
visible in the frozen prompt. It is one observation, not a general capability
estimate.

## What native verification recorded

Dafny 4.4.0 returned exit **4**, with **267 verified, 0 errors, 1 out of resource**.
All 268 required named CSV units were present; only
`RepoDiscoGrowthShift.MoveToFront (well-formedness)` was unsuccessful. Its CSV
resource count is 100,023,172 under CLI limit 100,000; those two units of measure
are distinct. The command finished within its 300-second wall cap. There was no
process timeout, missing unit, frontend error or new warning. All three exact
upstream warnings remained, and all 91 original files stayed byte-identical.

The current runner deliberately treats every verifier resource category as
terminal, so it stopped before requesting Vest or another independent lineage.
The [unchanged saved-evidence reviewer](review-001.stdout) passes and confirms
that this is an incomplete cohort. The behavior follows the frozen policy; the
policy is too conservative for collecting independent outcomes when a bounded
solver-resource failure has complete, trustworthy native evidence.

The prospective follow-up is a separate, tested policy for that narrow failure
class: retain it as unaccepted, block its child and continue other prespecified
lineages. Source/inventory ambiguity, missing logs, signals, process timeouts,
environment errors and provider errors must still stop dispatch. No resource
limit, acceptance threshold, prompt or previous score is relaxed by this
diagnosis. Any later collection is a new frozen allocation, not a restart here.

## Complete evidence and budget

The [156-file transfer](transfer-001.json) includes the full response and request,
source workspace, source/tool bindings, raw CSV/stdout/stderr/resources, ledger,
job logs and accounting. The [collection review](collection-review-001.json)
checks those hashes, protected originals, native outcomes and request accounting.
The live native command used about 95% of one core and peak RSS 575,252 KiB;
the full Slurm job used 90.562 CPU seconds and peak batch RSS 714,540 KiB. Job
overhead and provider waiting are separate from native verification time.

The [new-budget snapshot](../research-budget-20261123-002.json) records one
request used, eight slots allocated (seven unused and closed), and 92 calls
still unallocated under Sophie's new 100-call ceiling. No further model or
native calls were made by this review or counterexample trace.
