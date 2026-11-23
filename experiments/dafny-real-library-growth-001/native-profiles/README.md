# Native scope profiles and saved-evidence replay

The current standard-library profiles are in `stdlib-002`. Their named
inventories, source ownership, exact command order, versions/package hashes,
warning policy and unlogged-definition records come from actual saved native
observations. The profile builder/reviewer makes no verifier or model calls and
issues no model acceptance or execution release. Root's independent review and
the final runtime/execution review remain separate gates.

| Saved observation | Native units | Outcome |
| --- | ---: | --- |
| Baseline, job 63086889 | 56 | All pass, exit zero, no warnings |
| Revised `AppendAll` reference, job 63088122 | 58 | All pass, exit zero, no warnings |
| Revised `AppendRotated` reference, job 63088122 | 60 | All pass, exit zero, no warnings |
| Two alternatives, job 63088528 | 58 / 60 | All pass |
| Five negative bodies, job 63088528 | 58 or 60 | Expected named correctness failure |
| Two omitted failing additions, job 63088528 | 56 / 58 observed | Native exit zero; rejected for incomplete source/command coverage |

The audit matches **12/12 expected observations**: three previously collected
positive observations plus nine controls. Replaying them does not create twelve
new native trials. All original 56 baseline units pass in every control.
Each added method contributes its actual correctness and well-formedness unit.

`rotate-unproved-append` records `AppendAll (correctness)` as Failed while both
`AppendRotated` units are Passed. Whole-workspace success is rejected. Each
omission candidate is byte-identical to the corresponding tested failing
workspace; only the native source argument was omitted. Common review rejects
the unchanged record with `Exact native command differs`. The audit then retains
the actual exit-zero summary and missing named units; it never changes that
command or shrinks the expected inventory to manufacture a pass.

The scopes contain **44 explicitly unlogged definitions**: 21 simple integer
constants, two type aliases, 17 wrapper functions and four wrapper predicates.
Every entry has its exact source line and whole-file hash. None contributes a
logged pass. `mapping-stage*.json` maps named observations to declarations and
files; `has_logged_units` means exactly that, not a separate definition score.
The historical `stdlib-001` mappings used the less precise field name
`counted_as_pass` for this presence flag. `stdlib-002` clarifies the label without
changing native results or pass counts.

The initial two failed references from qualification-002 remain in the retained
evidence and explicit exclusion list. They do not establish a positive profile.
All fourteen known analyst observation IDs and complete raw fingerprints (the
twelve gate observations and those two earlier failures) are ineligible as
model-origin accepted parents, including after relabeling. A future genuinely
fresh model run may produce an identical body; source identity alone is not an
origin blacklist.

`build_stdlib.py` generated the initial positive profiles and replays;
`audit_stdlib_controls.py` created `stdlib-002` with all controls and provenance
exclusions. Full command stdout/stderr, exits and code hashes are under
`reviews/stdlib-mapping-001` and `reviews/stdlib-controls-001`. Every input source,
record and raw artifact is referenced by exact path/hash; large evidence archives
are not copied here.

The actual command order is `BoundedInts`, `Wrappers`, `DynamicArray`, then the
new files. The earlier prompt draft sorted those file names. Its source set is
the same, but the final prompt/edit profile must adopt this actual ordered list
before release. No native rerun is needed just to change draft metadata.

## AWS UInt-only reference gate

`aws-001` now binds the three actual qualification-005 observations from job
63100879: **71, 75 and 77 named units**, respectively, all Passed with exit zero
and no warnings. The common reviewer replays exact source, raw CSV/stdout/stderr,
resources, command order and before/after toolchain pins. The native observations
took 5.70, 5.94 and 6.10 seconds; this replay made no new native/model calls.
This reference-only checkpoint remains preserved; `aws-002` adds the completed
control review below.

The baseline contains only the original `UInt`, `BoundedInts` and `Wrappers`
files. Stage one adds `ReadU16Frame`; stage two preserves those exact reference
bytes and adds `ReadFramePair`. All references match the exact host body markers.
The earlier 102-file AWS scope remains unqualified historical evidence; this
smaller scope does not test UTF8 validation, encryption-context parsing or all
of AWS MPL.

These function methods emit actual **well-formedness** units that check their
bodies/contracts; no separate correctness label is fabricated. Stage one adds
four units (`HasFrame`, `FramePayload`, `FrameRest`, `ReadU16Frame`); stage two adds
two (`HasFramePair`, `ReadFramePair`). Every actual CSV occurrence is retained;
the inventories have no duplicate names. There are 54/55/56 explicitly unlogged
source definitions, including datatype declarations; none is counted as a pass.

`build_aws.py` reuses the immutable saved-observation loader and source scanner,
with a narrowly reviewed declaration-to-file mapping that handles legacy
function syntax and Wrappers datatype members. `reviews/aws-mapping-001` retains
the full replay transcript and code pins. All three observations are explicitly
analyst-origin and ineligible as model parents. Analyst reference success
establishes a qualification control, never a model-generated or accepted parent.

`aws-002/control-gate.json` combines those three saved positives with nine
distinct observations from job **63103670**. All twelve expectations match:
eight postcondition failures and one omitted-child coverage rejection, in
addition to the three positives. Every control preserves all 71 upstream passes.
The actual unproved-parent case has a failed `ReadU16Frame` and passing
`ReadFramePair`; the workspace remains rejected. The omission case verifies
75 units while staging the same bad child that fails when included. Only the
whole-file hashes for already declared unlogged definitions are materialized
after checking protected source boundaries; source declarations, named units,
native commands, warnings and toolchain pins remain fixed. Root independently
reviewed all 133 gate inputs and the full 242-file transfer. This gate qualifies
the task and measurement; it is not model evidence or live execution authority.
