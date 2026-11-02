# Difficulty and interval-witness review — November 2, 2026

Decision: retain all 16 existing configurations and the clarified prompts for a
fresh balanced **diagnostic calibration**, with no model calls authorized here.
The eight-call smoke gate established usable syntax in eight samples, not an
informative difficulty distribution. Do not begin the 192-call main collection
on that evidence alone. No fixture, contract, parser, prompt, saved response or
historical score is changed by this review.

## What the saved results say

| Family | Deep smoke successes | Reasoning required by the current interfaces | Difficulty concern and calibration decision |
| --- | ---: | --- | --- |
| Conditional preconditions | 2/2 | Normalize the sign and reflected offset; establish Start then Advance prerequisites before Finish. Shallow replaces the chain with Direct. | Likely easy anchor. The separate response uses visible `K.Abs(x)` to avoid one branch level; reference branch count is not minimum reasoning complexity. Retain and inspect for ceiling. |
| Sequence offset | 2/2 | Separate empty/nonempty sequences, recurse on `s[1..]` with offset `o+1`, meet the decreases clause, then compose the suffix-score relation. | Real induction choice remains, but supplied Base/Direct/Finish providers discharge unfolding and algebra. Deep adds Split/Lift, not a new inductive theorem. Retain; both smoke responses used the same successful strategy. |
| Interval witness | 1/2 | Construct a value in both intervals; deep obtains Left and Right facts for the **same** value, then Join and Finish. | One observed mathematical/precondition error, not a syntax error. Retain unchanged to measure fresh samples without injecting the discovered solution. |
| Map transfer | 2/2 | Distinguish aliasing from distinct keys; deep composes Debit/Credit/Finish after checking the source balance bound. | Short interface-guided proof. Providers already establish exact balances, conservation and frame properties. Retain; likely ceiling risk despite rich provider specifications. |

These are two observations per family (one per deep sharing condition), not a
reliable difficulty ranking. Shallow tasks were absent from this smoke test.
Earlier strict scores remain 18/32 and 1/32 in their own versions; many failures
were output rejections and cannot be interpreted as mathematical failures.
The smoke score remains 7/8. No samples will be pooled into the new 32 trials.

## The interval-witness failure

Saved evidence: [smoke-04 response](../monorepo-syntax-smoke-001/model-001/smoke-04/response.json),
[source](../monorepo-syntax-smoke-001/model-001/smoke-04/candidate/HelperA.dfy),
and [verifier diagnostic](../monorepo-syntax-smoke-001/model-001/smoke-04/verification.json).
The proof chooses `c` unconditionally in `S1.Left(a,b,c)`, followed by Right,
Join and Finish with the same value. Left requires `a <= c <= b`. The task assumes
`a <= b`, `c <= d`, `a <= d` and `c <= b`; it does **not** assume `a <= c`.
The archived verifier reports exit 4 at this first call's precondition.

For example, `[a,b]=[2,5]` and `[c,d]=[0,4]` overlap, but the selected value
`c=0` is outside `[2,5]`. This is a concrete counterexample to the submitted
proof's call precondition, not a counterexample to the task specification.

The already verified separate sample branches on `a <= c`: choose `c` in that
case and `a` otherwise. In the first case, `a <= c <= b` and `c <= d` establish
both interval memberships. In the second, `c < a <= d` and `a <= b` do so.
Thus `max(a,c)` is a common witness under the original assumptions. The reference
uses the equivalent reversed comparison. This explanation is reviewer-only and
is **not** added to the model's prompts or used to repair/rescore smoke-04.

The offline audit also enumerates integer endpoints in [-3,3] as a finite sanity
check of this explanation. This does not prove the universal theorem or execute
Dafny. The existing reference verification provides the formal evidence.

## Matching and workload audit

All four structural cells within each family retain identical Kernel, Stage1–3,
ClientA, ClientB and All files. Helper interfaces keep the same lemma contracts;
imports/export views and the shared forwarding wrapper implement the treatments.
Full source plus declared map is always visible. Hidden-Direct controls prevent
calling that shortcut from deep helpers. They do not prove minimum proof depth.

Shared configurations expose one editable helper body and a fixed forwarding
wrapper. Separate configurations expose two equivalent bodies; copying is allowed
but cross-helper delegation is not. **Every separate smoke response used identical
text in its two bodies.** These are not two independent reasoning attempts.
The change in body count/output size is part of the workload treatment; it is not
an equal-work test of a purely cognitive sharing benefit. Kernel and stage
definitions remain shared in both conditions.

The prompts contain full trusted provider implementations. They exclude reference
helper solutions and prior responses, but they are not an interface-only setting.
The task measures composing/instantiating visible APIs and writing the permitted
helper proof, not discovering or proving all provider mathematics from scratch.
Human-readable helper names may guide both conditions. All inspected families
remain development data, with no held-out/generalization claim.

The frozen `evidence-review.json` records exact prompt/source bytes, editable-body
counts, reference-body bytes, archived proof-depth annotations and evidence paths
for each variant. These are size/reference measurements, not token counts or
minimum possible proof lengths. It rechecks the 136 selected existing controls
(16 success, 108 proof failure, 4 termination failure, 8 explicit resolution
failure), reconstructs 16 reference workspaces exactly, and replays eight saved
responses with unchanged candidates and scores. No new verifier runs are needed
because task sources and parser bytes are unchanged.

## What the next calibration can resolve

Use two fresh samples for each of the 16 configurations, with the existing cyclic
Latin ordering and complete reversal for sample two. This balances cell and
position exposure; it is not a carryover-balanced design or a power calculation.
The midpoint has the same variant twice, always in separate fresh contexts.
No response or feedback flows between samples. New request IDs, ledgers and output
directories are mandatory; old trials are never resumed.

Report end-to-end strict verification and admission separately, retaining all
planned/reserved/dispatched counts. Inspect all failures and all accepted proof
strategies/duplicates. A family at 0/8 or 8/8 requires floor/ceiling review before
scale-up; near-ceilings or template duplication can also make collection
uninformative. Any recurring protocol issue blocks scaling. Do not tune the
parser or silently drop trials during collection. A changed family or protocol
gets a separately frozen version and validation evidence. The main corpus
requires a later explicit review and budget even if this pilot succeeds.
