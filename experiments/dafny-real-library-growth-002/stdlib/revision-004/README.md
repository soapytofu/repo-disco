# Replacement-fill frame revision

**Revised splice native status: UNKNOWN.** In job 63166870 the revision-003
filter reference passed all 59 named native units with zero errors or warnings.
The splice reference had one remaining ordinary proof error: the replacement
loop's Put call could not establish its modification frame. Both full
observations and all earlier failures are preserved and pinned in revision.json.

Only two proof lines are added to the splice reference body: a FillStart label
and a freshness invariant relative to that loop's entry. The fill loop starts
after growth and shifting may allocate; method-entry freshness alone permits
representation members allocated before the loop outside its fixed frame.
The new loop-relative invariant is the same reasoning already verified for
the earlier ShiftStart loop and is supported by Put's fresh-representation
postcondition.

The final trimming loop needs no such change: PopFast modifies exactly the
array object's size/items fields, which its existing frame permits, and its
contract cannot change Repr. No representation constancy is assumed for Put.

All filter case entries and sources are byte-identical to revision-003, so its
real reference pass is explicitly reused. It is not a new independent
observation or a model success. **Only splice-reference needs a new native
reference check.** The 17 fixture identities remain for the later control
gate. Derived splice mutations keep the same intended faults.

All protected templates, functional contracts, imports, helpers, types, prior
accepted seed, upstream bytes, verifier options and resource limits are
unchanged. Both alternative bodies are unchanged. header-diff.patch is empty;
body-diff.patch records the exact two-line addition.

Focused offline checks include byte-exact filter reuse, protected-body
reconstruction, prior failure evidence, and the same negative/omission
boundaries. They establish construction integrity, not the mathematical
validity of the revised splice. Full logs and tested hashes are in reviews/.
