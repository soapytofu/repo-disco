# Native scope profiles and saved-evidence replay

The current standard-library profiles are in `stdlib-002`. Their named
inventories, source ownership, exact command order, versions/package hashes,
warning policy and unlogged-definition records come from actual saved native
observations. The profile builder/reviewer makes no verifier or model calls and
issues no model acceptance or execution release. Root's independent review and
the other project's qualification remain separate gates.

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

AWS profiles are intentionally absent until its actual pinned-toolchain native
evidence is available. Analyst reference success establishes a qualification
control, never a model-generated or model-accepted parent revision.
