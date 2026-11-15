# Exact positive-gap pair: development repair fixture

**Status: generated and tested offline; Dafny verification is pending.** No model
requests, SSH operations or verifier processes are part of this directory's
construction or tests.

Choose `u` in `[a,b]` and `v` in `[c,d]` with `v=u+gap` and `gap>0`. The exact
feasible-input contract is

```
gap > 0 && a <= b && c <= d && a+gap <= d && c <= b+gap
```

It is necessary: membership gives nonempty input intervals; `a<=u` and
`u+gap<=d` give `a+gap<=d`; `c<=u+gap` and `u<=b` give `c<=b+gap`.
It is sufficient because `[a,b]` intersects `[c-gap,d-gap]`:
`u=max(a,c-gap), v=u+gap` satisfies every bound. An alternative takes
`v=min(b+gap,d), u=v-gap`. Both constructions, including disjoint original
intervals and a single feasible pair, receive offline finite-domain checks.
These finite checks are not a Dafny proof or a general exhaustiveness claim.

The repair seed always chooses `u=a`. For `a=0,b=5,c=4,d=8,gap=2`, the precondition
holds but its `v=2` violates `c<=v`. Always taking the other endpoint also fails:
`a=0,b=5,c=1,d=4,gap=2` gives `v=7>d`. Counterexamples and the feasibility
derivation are machine-readable in `tasks.json`.

The helper must construct the values, establish separate opaque left-membership,
right-membership and exact-offset facts, then pass those facts to existential
packaging. `Finish` does not choose a witness. Public views hide predicate bodies
and the alternate membership provider. There is no provider lemma proving the
whole target from its input precondition.

Two immutable clients use the same theorem, one directly and one under a common
integer translation. The shared condition has one editable proof; the separate
condition has two equivalent editable proofs and allows copying. Provider files,
client files and final specifications are identical between conditions. This
changes output work and source length; it is not a pure causal test of reasoning
difficulty. Reference certificate dependencies are not a minimum-depth claim.

Each condition has reference and upper-endpoint alternative positives, seven
ordinary negative controls (empty, faulty lower endpoint, faulty upper endpoint,
short gap, and three missing certificates), and one hidden-export resolution
control: **20 checks total, expected 4 strict passes, 14 proof failures, and
2 name-resolution failures**. Parse/type/termination failures do not count as
ordinary proof failures. All expected statuses remain hypotheses until compute
verification. The editable body spans and protected-byte hashes are recorded for
every case; a production output-guard registry is still pending integration.

This is `D3-new-exact-gap`, in the existing integer-interval development ancestry.
It does not replace the current D3-M1 intersection/certificate proposal or the
older task that put both separated witnesses inside the interval intersection.
It is neither held out nor independent of that lineage.

Construction: `python3 build.py`. Offline tests:
`python3 -m unittest discover -s . -p test_design.py -v`.
`manifest.json` hashes all exact generated fixture/template sources and metadata.
