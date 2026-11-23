# Growth collection with bounded resource-failure outcomes

This separately versioned execution-005 retains the exact frozen growth prompts,
request gate, credential handling, evidence reviewer, parent protocol, native
commands, toolchains and limits from execution-004. It changes one collection
policy: a completed, fully evidenced Dafny solver-resource failure may be saved
as an **unaccepted outcome**, block that lineage's child and let independent
lineages continue. It never counts as proof success or creates an accepted parent.

The change responds to the [first returned growth candidate](../execution-004/COLLECTION.md).
That body has a concrete order counterexample; its full native check preserved
267 upstream passes and reported the new target out of resource. The original
runner stopped, with seven unused slots. Its complete archive, classification,
score and closed ledger remain unchanged. This package cannot resume that run.

## Exact boundary

`native_failure_policy.py` runs only after the existing source, tool, command,
scope and full-inventory audit. It requires all of the following:

- Dafny native exit 4, exactly one completed invocation, no outer/process timeout,
  complete resource capture, and no accepted/proof-passing result.
- Every expected named CSV unit present once, with Passed or Failed status.
- An exact extended native summary with zero ordinary errors and counts agreeing
  with the CSV. Every failed unit must have its own named out-of-resource
  diagnostic, bound to a source file in the checked workspace.
- Empty stderr, the exact inherited warnings, and no unknown stdout diagnostics.
  Source excerpt lines under recognized diagnostics are allowed.
- Matching raw and metadata hashes, the exact native CSV Results File path, and
  resource records showing exit 4 with no delivered signals.

The derived receipt retains the old parser's count-agreement field, which is
false for the resource-suffixed summary. It adds a separately checked agreement
for this summary form without editing the frozen protocol/parser. Passing
extractions are byte-identical to the inherited path. Only eligible negative
outcomes get the classification `BOUNDED_NATIVE_RESOURCE_FAILURE` and
`terminal=false`. They remain `qualified_pass=false` and cannot issue a parent.

Provider ambiguity/errors, malformed or missing evidence, source/tool drift,
unknown diagnostics, process timeouts, signals, OOM, frontend failures and any
unqualified resource category remain terminal. This policy does not infer that
a resource failure is mathematically incorrect, increase verification limits,
retry a candidate or weaken success. Actual source correctness requires separate
evidence; the old candidate's analyst counterexample is reported separately.

## Collection and budget

The fixed order is two independent lineages per project, each with at most two
additions: Dafny-VMC MoveToFront then PickPair; Vest frame proof then batch proof.
One fresh response per stage, no repair feedback loop, retries or reassignment.
A child receives the actual accepted parent source, never a reference fallback.
Vest is specification/proof-library growth, not executable parser generation.
Observed parent-API use is separate from successful verification.

Prompt manifest remains `9f2e4c9602b4ce98740f2a3fa1dcf7bbef07d2b0693db8d92d9cc55546820f0c`;
parent-protocol manifest remains `9cf8cc81bd55f83a591c04c2877ab9a0ece3927fcddc31f6f3d42d7953d42057`.
No model-visible counterexample, saved response, analyst solution or new feedback
is introduced. Past evidence is available only to offline host qualification.

Sophie authorized a total ceiling of 100 new calls, with confirmation before
exceeding it. [Snapshot 002](../research-budget-20261123-002.json) has eight
allocated, one used, seven closed unused and 92 unallocated. This prospective
fresh cohort requires its own recorded allocation of at most eight from the
92, a hash-bound fresh authorization, one exclusive submission and a private
handoff. No new budget question is needed within the already authorized ceiling.
The package itself creates no authorization, request or native execution.

## Validation and execution

Tests replay the exact old native evidence under the new negative-outcome
policy without rescoring it. Synthetic boundary tests reject mismatched counts,
missing named failures, raw/source drift, unknown diagnostics and incomplete
execution. A synthetic full-dispatch test checks that the failed first parent
blocks only its child, other lineages continue, and the complete saved-evidence
reviewer replays the outcome. Synthetic results are not mathematical evidence.
The inherited transport, guard, parent, one-attempt and SDK-error tests remain.
The inherited suite keeps its 600-second bound; the added resource-policy suite
has a separate 180-second bound and full log. Either failure fails preflight.
The outer remote preflight retains its 900-second process-group bound. These
are offline qualification limits; no model or native verification limit changes.

`preflight.py --draft` checks the explicit package before freezing. All tests
use saved evidence or fake transport/processes. The SDK probe uses dummy tokens,
empty temporary AWS configuration, intercepted HTTP and forbidden connections;
`--require-sdk` on Cannon requires all five scenarios. No credential or provider
connectivity check is part of preflight. Full logs and source hashes are retained.

The new remote directory is `~/formal-disco/outputs/real-repository-growth-001/execution-005/`.
`ops.py stage` and `ops.py preflight` use authenticated socket21 and hard timeouts.
Before each mutation root checks existing local/remote receipts, output and queue.
A live partition check must establish UP, PreemptMode=OFF and sufficient limits.
One node, one task, **one CPU, 8 GB, four hours**, no requeue. Dafny resource limit
100000/native wall300s; Vest one Cargo worker/one Verus thread/native wall900s;
provider read180s and total SDK attempts1. Native verifiers run only on compute
nodes. No automatic retry, resubmission or resource escalation is provided.

Publish every returned response and attempted/blocked stage with source and
parent hashes, raw native inventories/stdout/stderr/resources, request accounting
and scheduler logs. Fully accounted lineages have a separate completion metric;
an infrastructure stop has only partial-cohort results. Report this new cohort
separately from execution-004, and retain all unsuccessful outcomes. It tests a
small, selected real-source feasibility setting, not unrestricted generation,
held-out generalization or a causal language/structure comparison.
