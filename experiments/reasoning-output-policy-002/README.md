# Reasoning output policy v2 — offline development validation

November 2, 2026 Eastern. **No new model calls. The original pilot remains
18/24.** This separate parser admits the primed identifiers and collection
expressions that caused five rejections in the frozen v1 pilot. Neither the old
parser nor any old prompt, result, accepted revision, or archive was changed.

## What was checked

- **25 offline test methods passed:** the nine unchanged v1 tests against current
  revision-003 fixtures, 11 extension/adversarial tests, and five evidence tests.
- All **24 saved responses** reconstruct exactly the previously verified source
  bytes: 19 workspaces from the original run and five from the separate diagnostic.
- All **24 reference proofs and 104 semantic negative controls** reconstruct
  exactly. Invalid proofs remain invalid proofs; admission does not repair them.
- Both published evidence archives and all 306 frozen proposal files retain their
  pinned hashes. Original imports, contracts, clients, providers, and file sets
  remain protected.

This is a post-hoc compatibility study informed by the observed outputs, **not a
new prospective success rate**. The [audit](compatibility-audit.json) links every
candidate to a raw record and source hashes. It reuses existing compute evidence;
it makes zero new verifier invocations. It deliberately excludes the analyst's
one-fact repair of trial 03, preserving that trial's failing original body.

The exact original bodies of trials 02, 18 and 21 have strict successes in the
separate diagnostic. Trial 08 still fails assertions. Trial 24 still has
warning-only exit 2. Those observations do not change the five original guard
rejections or the original pilot score.

## Policy changes and limits

The [syntax contract](SYNTAX.md) describes the bounded language. Compared with v1,
v2 adds ASCII identifiers containing trailing/interior apostrophes, set displays,
functional collection updates, and one-binder map comprehensions. No submitted
body is rewritten, normalized, alpha-renamed, or silently repaired.

Bindings cannot shadow parameters, reserved module names, or active locals.
Map-comprehension and `forall` binders cannot escape their scopes. Arbitrary
declarations/calls, assumptions, reveals, attributes, loops, mutable assignments,
comments, and strings remain forbidden. Exact seed hashes and host-owned editable
file sets are still required. The same size, token, nesting and statement bounds
apply. The parser's tree inventories syntax; it is not a typed Dafny AST.

This policy is neither a sandbox nor a Dafny semantic checker. It deliberately
admits some ill-typed expressions, potentially nonfinite maps and false proofs.
The verifier must reject them. It can also reject legal Dafny outside this small
language. All trusted task metadata and seed sources must be pinned by the host.

## Warnings remain non-success

The original strict exit-zero acceptance policy is retained. The audit distinguishes
an assertion failure from the observed warning-only nonzero exit using exact
verifier summaries and diagnostics. It does not mistake `10 errors` for `0 errors`
or count missing-trigger warnings as parse/proof failures. This classifier is
limited to the observed saved-response categories; unfamiliar or inconsistent
evidence fails review instead of being guessed. It is not installed in the old
runner or backend.

A subsequent [one-case compute preflight](warning-preflight/README.md) replaces
the warning-producing concrete map expressions with existing `lhs`/`rhs` aliases.
It passes strictly: 16 verified, zero errors, zero warnings, exit 0. This
analyst-authored syntax substitution adds no lemma calls and leaves all contracts
unchanged. It demonstrates one permitted warning-free formulation; the original
output and its diagnostic remain unchanged. This is the only new verifier call
in the follow-up and used no model request.

## Reproduce offline

From the repository root:

```bash
python3 -B -m unittest discover -s experiments/reasoning-output-policy-002 -p 'test_*.py' -v
python3 -B experiments/reasoning-output-policy-002/evidence_audit.py
```

[Test log](offline-tests.log), [execution metadata](offline-tests.json),
[parser](body_guard.py), [audit code](evidence_audit.py),
[validation freeze](validation-freeze.json).

No revised model pilot is frozen or authorized by this work. Before any future
pilot, choose the task set and warning policy, embed matching syntax instructions,
pin this policy or a separately reviewed successor, and freeze the complete
requests/settings/order. Conditional and nested-filtering ceiling results still
need a difficulty decision; parser compatibility does not solve that problem.
