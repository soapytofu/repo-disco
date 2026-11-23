# Harder independent DynamicArray extensions

**Mathematical/native status: UNKNOWN.** These are analyst-authored construction
fixtures. No Dafny, native runtime or model calls were made to build this bundle.
The qualifier must first review filter-reference and splice-reference, then
the distinct remaining controls. Exact CSV unit names and complete inventories
must come from those real observations; actual_native_unit_labels stays null.

| Task/project | Fixed behavior | Reference strategy |
| --- | --- | --- |
| stdlib-filter | Stable in-place retention of integers strictly below a threshold, with exact resulting sequence and removed count | Read/write compaction, then tail pops |
| stdlib-splice | Generic replacement of an arbitrary valid range by a sequence, preserving exact prefix and suffix | Grow through the prior accepted AppendAll, shift overlapping suffix backward or forward, fill replacement, then shrink |

Both tasks are independent stage-one body completions. The public signatures,
contracts, helper function, exports and imports are host-owned. Only the current
method body changes. There is no dynamic parent from this pilot. Splice's
growth/AppendAll.dfy is the exact already accepted model source from growth-001
slot 01, recorded with its request, receipt and native-evidence pins. It remains
ordinary immutable base source. The unused accepted AppendRotated is not staged.

All original BoundedInts, Wrappers and DynamicArray files are unchanged.
The selected exported DynamicArray API contains no stable filter or splice
method; this is a check of the pinned scope, not an exhaustive duplication audit
of every upstream module. The three original files' license is retained.

The methods require and preserve size == |items| explicitly. This makes the
sequence-view bound available without depending on unfolding the exported
Valid? predicate. Both preserve validity and allocation freshness. Neither
promises unchanged or nondecreasing capacity: the exported Put contract does
not provide that guarantee.

The filter specification recursively builds a retained prefix, preserving order
and handling repeated values and equality with the threshold. The splice
contract covers insertion, deletion, equal-sized replacement, empty arrays,
empty replacements and boundary positions. Its reference uses loop invariants
for unprocessed source regions and already copied destination regions.

The alternatives are deliberately different: recursive pop/filter/reappend for
filtering and snapshot/rebuild for splicing. They are also native-UNKNOWN. These
alternatives make clear that an efficient shift algorithm, a loop shape, or
particular API-call count is not a necessary solution requirement. Intended
extra semantic/proof complexity is not yet evidence that a model finds these
tasks harder.

There are **17 expected observations**: four positive reference/alternative
cases, eleven intended proof failures, and two staged-omission controls. Only
the two main references are eligible for the initial qualification dispatch.
Negatives cover an empty body, wrong threshold/write position/copy order,
missing tail shrink, missing growth call, and a missing loop proof invariant.
The omission controls retain the exact failing source bytes while leaving the
new file out of native roots; native exit zero must still fail full coverage.
The unproved-AppendAll control changes only that seed body while preserving its
contract. It is rejected by the model edit guard and is solely a native
measurement control; whether the caller passes under the unproved contract must
be observed, not presumed.

cases.json follows the prior qualifier's explicit-root schema. Declaration
names in required_targets are intended target identities, not invented CSV
rows or proof successes. The root qualifier owns pinned toolchain dispatch,
actual classifications, complete inventories and reviewed evidence.

build.py creates new output once from exact origins and body templates.
test_construction.py checks hashes, reconstruction, immutable sources,
omission/source identity, negative mutations and the native-only bad-seed
boundary. These checks establish fixture construction only, not Dafny syntax
or mathematics. Full local construction/test stdout, stderr and receipts are
saved in reviews/.
