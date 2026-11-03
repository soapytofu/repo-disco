# Four-family output-policy compatibility

November 2, 2026 Eastern. **27 offline test methods passed; zero new model or
verifier calls.** A separately versioned policy integrates the previously
validated interval-witness task with the six reasoning instances and guarded
clamp monotonicity. No old parser, prompt, source, result or score changed.

The [catalog](task-catalog.json) identifies **32 existing workspace snapshots**:
eight development semantic instances, each with four structural variants.

| Family group | Instances | Snapshots |
| --- | --- | ---: |
| Conditional | Nested clamp, clamp stability, guarded monotonicity | 12 |
| Sequence | Reverse concatenation, nested filtering | 8 |
| Map | Commuting updates, delete after update | 8 |
| Relational | Interval witness | 4 |

This is a compatibility library, **not a new 32-call proposal, a frozen pilot or
the larger main corpus**. It contains inspected development tasks, including
ceiling anchors. Source paths/hashes, allowed calls, pure functions and editable
files are recorded; no trial order, model prompts or execution authorization is
created. Depth labels are task-relative and do not imply equal numerical proof
depth across families.

## Exact compatibility evidence

- Four interval-witness references and 20 admissible negative bodies reconstruct
  exactly. Two hidden-API controls are rejected; four weakened-contract controls
  are rejected at the protected boundary. All 30 link to their original compute
  records, expected exit categories and source hashes.
- All eight saved witness responses reconstruct exact original candidates,
  including the three precondition failures. The old balanced score stays
  **29/32**, and the later reasoning score stays **18/24**. No new combined score
  is computed.
- Regression tests retain 24 earlier reasoning references, 104 negative bodies,
  all 24 saved reasoning responses and the 28 admissible monotonicity controls.
  Reusing identical source evidence is not a new independent verification trial.
- All 813 files in the older balanced model archive retain their published hashes;
  its frozen plan, preflight gate and result review are pinned.

[Full replay audit](integration-review.json), [audit code](review_integration.py),
[tests](test_integration.py), [test log](offline-tests.log),
[execution metadata](offline-tests.json), [validation freeze](validation-freeze.json).

## What changed in the policy

`reasoning-body-json-v4-integration-development` preserves the v2 surface grammar
and protected insertion. It adds the exact witness parameter/API registry and
reserves the module aliases used by each task, including `S1`, `S2` and `End` in
deep witness mode. Those names cannot be shadowed by locals or binders. The
protection is task-specific; the old seven registries remain equal, and an old
task may still use an otherwise unused `S1` local. Tests compare the unchanged AST
outside the version, registry and declaration-binding check.

Witness shallow calls are `End.Direct` (five arguments). Deep calls are `S1.Left`
and `S1.Right` (three each), `S2.Join` and `End.Finish` (five each). Pure predicates
are the four public `K.LeftFact`, `K.RightFact`, `K.Joined`, `K.Overlap` symbols.
The hidden `K.Witness` predicate, cross-helper delegation and self-recursion are
not admitted for this task. Existing self-recursion rules for other families are
unchanged. No assumptions, reveals, attributes, declaration edits or warning-policy
exceptions were added.

See the [bounded syntax contract](../reasoning-output-policy-002/SYNTAX.md) and
[monotonicity registry](../conditional-monotonicity-001/protocol/README.md).
The parser still checks syntax and scope, not Dafny truth, types or finiteness.
All task metadata/seeds must be trusted and pinned. Strict nonzero exits remain
non-success; differing historical policies are not retroactively harmonized.

## Remaining decision

Technical four-family grammar compatibility is now demonstrated on the saved
evidence. The next model study still needs a deliberately selected task set,
family-specific depth annotations, precise instructions, matching review and a
complete request/settings/order freeze. In particular, ceiling examples should
not become the main corpus merely by adding renamed copies. The new conditional
task's model difficulty is unknown. New model calls require a separate budget.

Reproduce offline from the repository root:

```bash
python3 -B experiments/monorepo-policy-integration-001/test_integration.py
python3 -B experiments/monorepo-policy-integration-001/review_integration.py
```
