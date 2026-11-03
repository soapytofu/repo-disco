# Monotonicity API registry on the unchanged v2 grammar

`reasoning-body-json-v3-monotonicity-development` adds the trusted
`clamp_monotone` task registry to a **separate copy** of the v2 parser. Only the
version label, module description and task/API registry differ. An AST comparison
checks that tokenization, grammar, binding, bounds, protected insertion and JSON
handling are unchanged. The original v1 and v2 policies remain pinned and intact.

**25 offline test methods passed:** 20 inherited grammar/compatibility tests and
five registry tests. Four new references and 24 semantic negative bodies
reconstruct byte-identically; all four hidden-view calls are rejected. Prior six
task registries compare equal, all 24 previous reference and 104 negative sources
still reconstruct, and all 24 saved model responses retain their exact candidate
bytes. These are regression checks, not new model or verifier trials.

The [replay audit](replay-review.json) links every new task/control to its existing
compute source hashes and diagnostics. No unchanged proof was re-verified.

| Registry field | Shallow | Deep |
| --- | --- | --- |
| Parameters | `x, y, l, h` | Same |
| Pure functions | `K.Lower` (2), `K.Upper` (2), `K.Clamp` (3) | Same |
| Provider lemma calls | `A.Below`, `A.Within`, `A.Above` (3 each) | `O1.Below`, `O1.Within`, `O1.Above` (3 each); `O2.Below` (2), `O2.Within` (3), `O2.Above` (2); `A.Assemble` (5) |
| Self-recursive call | `Prove` (4), subject to Dafny termination checks | Same |
| Editable bodies | HelperA shared; HelperA and HelperB separate | Same |

Numbers in parentheses are argument counts. Calls through alternate hidden views,
other helper modules or arbitrary function names are rejected. Parameter shadowing,
contract/file edits, assumptions, reveals, attributes and other bypasses remain
forbidden. See the unchanged [bounded syntax contract](../../reasoning-output-policy-002/SYNTAX.md)
for statement/expression forms and limits. This registry is not a semantic checker
or sandbox; trusted host-owned task metadata and exact seed hashes are required.

[Code](body_guard.py), [registry and inherited tests](test_registry.py),
[test log](offline-tests.log), [metadata](offline-tests.json),
[replay code](review_replay.py), [validation freeze](validation-freeze.json).

From the repository root, reproduce offline:

```bash
python3 -B experiments/conditional-monotonicity-001/protocol/test_registry.py
python3 -B experiments/conditional-monotonicity-001/protocol/review_replay.py
```

No complete model prompts, request order or inference settings are frozen here.
No model execution is authorized. A future coherent calibration must explicitly
select this policy or another reviewed version and freeze the exact requests;
the current relational-family registry gap is not resolved by this addition.
