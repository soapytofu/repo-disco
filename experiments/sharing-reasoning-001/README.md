# Reasoning-focused sharing fixture

**Evidence reviewed: all 46 intended outcomes confirmed.** Job 54818785 finished on sapphire in 2 minutes 4 seconds. Its raw status is **FAILED (1:0)** because four hidden-helper diagnostics said `unresolved identifier`, while the original harness expected `does not exist`. The other 42 checks matched automatically. The original failed summary, runner, and all raw logs are preserved in [verification-001](verification-001/). A corrected matcher was tested offline against all 46 recorded results; no verifier rerun was performed. **Zero model calls.**

[Full check table](VERIFICATION.md) · [Separate evidence review](review.json) · [Original batch log](verify-54818785.log).

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

## Measured outcome and limits

Both conditions' reference proofs verify. Removing either concatenation step or the final step fails; wrong concatenation arguments and calling Finish before deriving its precondition fail proof obligations. The four attempts to call an alternate helper hidden by the export view fail name resolution, separately classified from reasoning failures. Weakening ConcatA breaks both clients in the shared condition but only ClientA in the separate condition; weakening ConcatB affects only ClientB in the separate condition. Weakened providers themselves verify.

Review checked exact compute/local fixture bytes, every recorded source hash and exit code, and all diagnostics. Three design tests and three diagnostic tests pass. These controls establish sensitivity to intermediate facts, argument choices, and precondition availability in the archived proofs; they do not establish an LLM's reasoning ability or a sharing advantage. Both conditions still share Finish, and the alternate export view is part of the experimental intervention.
