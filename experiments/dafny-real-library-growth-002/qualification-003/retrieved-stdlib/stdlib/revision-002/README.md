# Explicit frame and proof revision

**Revised native status: UNKNOWN.** This separate analyst construction has not
been parsed or verified by Dafny. The original two references actually failed
with ordinary proof diagnostics in job 63162242; their exact sources, raw
stdout/stderr, CSV files and records are preserved and pinned in revision.json.
All original fixtures, manifests and prior model results remain unchanged.

The original filter failed on loop read permissions, a final prefix equality,
and PopFast read/modify permissions. The original splice failed on a loop read
permission and four slice-bound obligations. These are construction failures,
not evidence about model performance.

The only protected-header change in this version is explicit in
header-diff.patch: both methods now have reads * and modifies a, a.Repr.
Exported PopFast has no explicit reads clause under the pinned method-reads
mode, so callers need its default unrestricted read permission. Its size and
items fields belong to the array object itself; the provided, opaque Valid?
predicate does not expose membership of that object in Repr. The old effect
frame could therefore not justify the reference's API use.

This is a deliberate broadening of effect permissions, not a body-only fix.
Every functional precondition and postcondition, type, helper definition,
import, export and upstream/accepted-seed byte is unchanged. No precondition
was added. No verification option, warning policy, resource limit or timeout
is relaxed. In particular, the methods still must preserve Valid?, exact items,
size/items coherence and allocation freshness, and promise nothing about
capacity because Put does not expose a capacity-preservation contract.

The revised bodies state loop frames and freshness explicitly, use natural
slice counters with both bounds, and expose the sequence equalities required
at loop exits and after updates. The two tasks retain their intended variety:
stable threshold compaction and generic overlapping range splicing. The
recursive filter and snapshot/rebuild splice alternatives remain valid
prospective solutions; the specification does not require one algorithm,
particular call counts or in-place shifting.

All 17 case identities and intended categories are retained in new workspaces:
four intended positives, eleven intended proof failures and two staged
omissions. Only filter-reference and splice-reference are initially eligible
for native qualification. The remaining controls must wait for review of
those two observations. The same frozen guard admits only the current method
body and protects the exact new headers, old upstream files and saved accepted
AppendAll. The bad-seed case remains a native-only measurement control,
ineligible as a model candidate.

build.py constructs this version once, validates the old fixture and failed
source lineage, and records all input pins. Focused offline tests check exact
reconstruction, the narrow header delta, immutable inputs, intended mutations,
and omission/bad-seed controls. Full stdout, stderr and tested-file receipts
are in reviews/. These tests establish construction integrity, not mathematics.
