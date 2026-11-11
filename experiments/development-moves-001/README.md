# Fresh-key move composition — D4-M1 development task

Prepared November 11, 2026. **Constructed and tested offline; Dafny verification
pending authenticated Cannon access. No job submitted and zero model calls.**

This implements the map M1 instance in the existing
[family split plan](../../docs/corpus-family-split-plan.md). It stays in the map
development ancestry group with the swap/update tasks. Reserved tree and
transition families are untouched. There are four structural workspaces, not
four independent semantic problems, and no model prompts or paid scope are frozen.

## Obligation and clients

For a map `m`, a present key `a`, fresh keys `b,c`, and pairwise distinct keys,
prove:

```text
Move(Move(m,a,b),b,c) == Move(m,a,c)
```

`Move` transfers the stored value and removes its source key when the source is
present and destination fresh; otherwise it returns the input map unchanged.
The reference must justify intermediate-domain changes and the original value
at `a`. Singleton maps and arbitrary integer values are included by the contract.
ClientA consumes whole-map equality; ClientB consumes membership and pointwise
equality to the direct move at any key in that direct result. ClientB is not an
independent frame theorem about the original map.

The four cells use the same kernel, providers, helper contract and clients.
Shallow mode exports a bundled `ObserveMove` contract. Deep mode exposes
`Certify`, `MoveKeys` and `MoveAt`; its intermediate certificate must be
justified from earlier domain facts. Named exports hide the alternate interface.
`Equal` is available in both modes. Shared mode edits HelperA and uses an immutable
HelperB forwarding wrapper. Separate mode edits both helper bodies, with copying
permitted. More editable bytes and duplicated work are explicit confounds.

These are proposed **reference application paths**, not necessary proof depths.
The deep reference also needs an inner-move value observation at `b` for the final
key `c`, or an unchanged original-key observation in the other branch. It is not
merely the two-update involution from calibration. Solver alternatives may exist.
The source metadata deliberately leaves `minimum_proof_depth` null.

## Planned verifier controls

| Phase | Checks | Expected |
| --- | ---: | --- |
| Core | 4 reference, 4 empty-body | 4 strict passes, 4 proof failures |
| Negatives | 24 common semantic negatives, 2 deep certificate omissions | 26 proof failures |
| Negatives | 4 hidden-interface calls | 4 name-resolution failures |
| Total | 38 | 4 passes, 30 proof failures, 4 resolution failures |

Semantic negatives omit the inner value fact, query the stale original map for
an intermediate source, retain the removed intermediate key, claim every moved
value is zero, skip singleton inputs, or call a move fact with an occupied
destination. In shallow mode removing the first bundled observation removes
domain **and** value facts; it is not a value-only ablation. The two deep
certificate omissions separately remove the intermediate `Ready` justification.
`checks.json` identifies the exact bytes and expected category of every case.
All changes are within designated helper bodies; contracts/providers/clients stay
fixed. Hidden calls test export visibility and are expected resolution errors,
never counted as proof failures.

References require strict exit zero, a positive verified count, zero errors and
no warnings. The 30 targeted negatives will be submitted only after the reviewed
eight-check core gate passes. Failures are archived before any deliberate versioned
revision. Each check gets one verifier invocation with a 60-second bound. No
automatic retries, requeue or duplicate submissions. Live partition state and
`PreemptMode=OFF` must be confirmed before submission. Dafny runs only on compute
nodes, with all included files verified. No provider client is present.

## Offline evidence and protected edits

Eight local test methods passed ([final frozen-input run](offline-tests-002.log),
[initial run](offline-tests-001.log)):

- A finite executable oracle checked 288 admissible map/key combinations,
  including 72 singleton cases and 96 cases with negative moved values. This
  sanity check is not a mathematical proof or a substitute for Dafny.
- All 38 fixture workspaces regenerate exactly; only editable bodies differ
  across controls. Source/contracts/client and interface comparisons are explicit.
- All 34 semantic bodies reconstruct byte-for-byte through the scoped grammar;
  all four hidden-helper bodies are rejected. False assertions remain admissible
  syntax so Dafny, rather than the parser, decides their truth.
- Contract/source edits, extra files, bypasses, shadowing, ambiguous JSON and
  out-of-scope binders are rejected. The isolated verifier is tested with a fake
  process that inspects actual staged files. Embedded remote scripts compile.

The separate task registry uses the diagnostic's quantified-expression grammar
with only task bindings and version changed. `provenance.json` pins that normalized
syntax and the unchanged envelope/verifier files; old policies are not edited.
The verifier requires trusted/guarded includes and is not a sandbox.

## Reproduction

```sh
python3 -B test_design.py
```

`manifest.json` pins fixture, runtime and test bytes for this verifier-only run.
The one-shot operations are `ops.py stage`, `preflight`, `submit core`, `status
core`, `fetch core`, then offline `review.py verification-001`. Only after reviewing
that evidence may `ops.py gate` and `submit negatives` be used, followed by the
corresponding fetch/review. The commands do not authorize model execution.

Current missing evidence: actual provider/reference verification, negative
diagnostics, and runtime/compute accounting. No measured model performance or
minimum-depth, causal-sharing, or held-out claim follows from this construction.
