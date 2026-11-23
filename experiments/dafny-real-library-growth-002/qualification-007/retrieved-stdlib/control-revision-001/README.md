# Two replacement splice controls

These are new analyst-authored negative controls based on the natively verified
revision-004 splice-alternative snapshot/rebuild implementation. No model call
is involved, and the new native outcomes remain unknown until qualification.

- `splice-retains-old-content` removes only the clearing loop. Snapshot creation
  and final AppendAll remain unchanged. For original [1], position 0, deleteCount
  1 and replacement [], the requested result is [] while the executable actions
  retain [1]. The fixed Splice content/length contract should fail; AppendAll
  must still verify.
- `splice-unproved-seed-rebuild` keeps the verified caller bytes exactly and
  uses the previously constructed return-only AppendAll helper body. The helper
  must actually fail and the caller must actually pass under its declared
  contract. This is a native-only trust control: the ordinary model guard must
  reject that helper mutation, and the whole workspace must not be accepted.

Fixed headers, imports, types, termination clauses and all three upstream files
are unchanged. Both cases explicitly verify all five source files at the same
1,000,000 resource limit, 300-second verifier limit, 360-second outer limit and
one CPU. No resource escalation or verification bypass is introduced.

The earlier no-tail-pop and unproved-seed controls produced RESOURCE_FAILURE,
not the expected ordinary proof failures. Their original expectations, exact
sources and full raw evidence remain preserved in revision.json; they are
excluded, never retried or rescored. The final intended active gate is four
existing references plus 24 unchanged matching prior controls plus these two
new observations. The original catalog had 31 entries; adding two replacements
makes 33 historical entries and 30 active cases. No test result is claimed from
byte checks alone, and no model score changes.
