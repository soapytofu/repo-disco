# Interpretation of the 26 pending controls

This is a read-only source review, not a native verification run or runtime
test. Counterexamples below are mathematical traces of the executable
operations with ghost proof statements erased; a bad assertion may expose
the fault earlier. Sources, draft selection and retired native evidence are
bound by the accompanying review.json. No fixtures or expectations changed.

The planned 26 controls comprise one alternative positive, 17 semantically
incorrect current bodies, three deliberately unproved immutable helpers,
one proof-support deletion and four coverage omissions. Their actual native
categories remain pending. The selected snapshot/rebuild splice alternative
also still needs its positive native gate.

All five functional splice negatives are independently incorrect under the
unchanged exact range-edit specification. Their interpretation does not require
the shifting reference to have passed:

| Control | Concrete input and mismatch |
| --- | --- |
| splice-empty | [1], position 0, delete 1, replacement [] remains [1]; required [] |
| splice-growth-wrong-order | [1,2], position 0, delete 0, replacement [8,9] produces [8,9,2,1]; required [8,9,1,2] |
| splice-wrong-replacement-offset | [10,20], position 1, delete 1, replacement [99] produces [99,20]; required [10,99] |
| splice-no-tail-pop | [1,2], position 0, delete 2, replacement [] retains [1,2]; required [] |
| splice-missing-growth-call | Empty array, position 0, delete 0, replacement [1] never grows; the size assertion is false and the later Put index is out of range |

The last four bodies retain the complex shifting proof structure. Their direct
semantic counterexamples do not predict Dafny's outcome under the fixed limit.
The unchanged shifting reference exhausted 1,000,000 resources
(reported ResourceCount 1,037,148), with the other 59 units passing.
If a negative also exhausts resources, record RESOURCE_FAILURE and leave its
intended proof-failure gate unmet. A resource result is not a mathematical
failure, a successful mutation check or evidence of a minimal causal ablation.

Three controls mutate only an immutable helper: splice-unproved-seed,
counted-unproved-frame and tagged-unproved-pair. Each helper independently
violates its fixed contract on an explicit valid input. Whole-workspace
acceptance must reject these candidates. A passing-client/unproved-helper
claim additionally requires the actual named caller to pass. In particular,
splice-unproved-seed retains the resource-heavy shifting caller, so that
stronger claim is unresolved even if AppendAll fails as expected.

filter-missing-prefix-invariant changes no executable operation. It is a
proof-support sensitivity check, not a semantically incorrect implementation.
An unexpected native pass must be retained; it would not invalidate the task
or establish that the omitted invariant was necessary.

The four omission controls stage exactly their corresponding failing empty or
always-failure sources but omit the addition from the command roots. They test
coverage rejection independently of the chosen positive implementation.
An exit-zero native run must not count as complete workspace verification.

The AWS body counterexamples and the remaining filter examples are enumerated
in review.json. They cover acceptance/rejection equivalence, frame count,
payload order, trailing suffix, tag removal, tag matching and byte budget.
The helper controls remain ineligible model edits. No broad causal,
minimal-repair, necessary-call, model-difficulty or held-out claim follows.
