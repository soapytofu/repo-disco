# Body-only sequence and loop-frame revision

**Revised native status: UNKNOWN.** The two revision-002 references failed
ordinary native proof checks in job 63165218. Filter had one unread-suffix
invariant maintenance failure. Splice had one growth-loop Put permission
failure and one final concatenation assertion failure. The exact failed
sources and full evidence remain unchanged and are pinned in revision.json,
alongside the earlier revision-001 failures.

All revision-002 protected templates are byte-identical here. This revision
changes only the two reference method bodies and their derived negative
controls. The empty header-diff.patch records that fact; body-diff.patch
contains the complete proof edits. The two alternative bodies are unchanged.
Every functional contract, effect frame, fixed helper, upstream file and saved
accepted AppendAll remains fixed. Native commands and resource limits are
unchanged.

The filter now explicitly derives equality of the unread tails after dropping
their first element, preserves that equality through either branch, and
asserts it before incrementing the read cursor. This exposes the slice
identity needed by the already existing suffix invariant.

The splice growth loop starts after AppendAll may allocate. Its previous
freshness invariant referred only to method entry. After loop heap havoc, that
condition permits representation members allocated before the loop but outside
its fixed loop-entry modification frame. The new ShiftStart label and
loop-relative freshness invariant retain the exact allocation condition
supported by Put's postcondition. No representation field is assumed constant.
The final proof separately splits the known items prefix into original prefix,
replacement, and original suffix, then concatenates those equal segments.

All 17 control identities and intended categories remain: four positives,
eleven proof failures and two staged omissions. Negative bodies are derived
from the revised reference with the same single intended mutations; their
actual classification still requires native checking. Only the two principal
references are initially eligible for qualification. The bad-seed mutation
remains native-only and is rejected by the body-edit guard.

The offline checks establish exact protected-body reconstruction, immutable
source and failed-evidence lineage, identical headers/commands, and the
retained mutation and omission semantics. They establish no Dafny syntax or
mathematical success. Full construction/test logs and hashes are in reviews/.
