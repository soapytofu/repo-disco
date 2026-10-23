# Reasoning-focused sharing fixture

October 23, 2026. Built; verifier-only job **54818785** is queued on `shared`/`sapphire`, with requeue disabled. **No model calls. No verifier findings claimed yet.**

## Reasoning target

Each client must derive a strict bound for the size of a three-part sequence, then supply that fact to `Finish`, whose precondition is the bound and whose postcondition is the opaque predicate `Large`. ClientA starts from a prefix bound and uses `(s + t) + u`; ClientB starts from a middle-sequence bound and uses `s + (t + u)`. Each reference uses two concatenation instances with different arguments, then `Finish`. Merely naming a helper is insufficient: incorrect arguments or missing intermediate size equalities should leave an obligation unproved.

Both conditions have identical provider source. Named exports expose only `ConcatA` or only `ConcatB` to each client. In the shared condition both clients import ViewA; in the separate condition ClientB imports ViewB and uses ConcatB. Source byte counts, target contracts, and reference call counts match. The chosen helper identity and export view differ; tokenizer counts have not been matched. `Finish` remains shared in both conditions, so the treatment concerns sharing of the concatenation lemma, not a repository with no shared definitions.

The named exports follow [Dafny's module/export semantics](https://dafny.org/dafny/DafnyRef/DafnyRef). The provider and imports must be protected in a future repair experiment. Hiding the alternate helper is a real API intervention and must be reported as such. A helper's full source can still be included in model context; verifier visibility is a separate constraint.

## Predeclared checks

46 verifier-only checks cover both conditions:

- Reference proofs: each client and the full repository must pass.
- Each client with the first step, second step, or final step omitted must fail proof obligations.
- Each client calling Finish first or repeating the wrong concatenation arguments must fail proof obligations.
- Attempts to call the hidden alternate helper must fail name resolution. These are boundary checks, **not reasoning failures**.
- Weakening ConcatA or ConcatB must affect the clients using that contract according to the sharing condition; weakened providers themselves must still pass.

Three offline tests check matching, protected contracts/provider bytes, and the check matrix. Run `python3 experiments/sharing-reasoning-001/test_design.py`. The verifier runner snapshots sources and diagnostics, uses a 60-second per-check timeout, and runs only on a Slurm compute node. No SDK or key is required.

## Interpretation limits

This is a designed reasoning-sensitive fixture, not evidence that sharing is intrinsically harder or easier. The two conditions deliberately keep each client's local mathematical proof comparable while changing which provider guarantee is reused. Future evaluation can measure correct intermediate arguments, satisfaction of preconditions, completion of both clients, and repair propagation after a provider change. A model study still requires a frozen edit policy, matched context design, and a new explicit call budget.
