# Restriction of overlapping right-biased override

**Status: generated and tested offline; Dafny verification is pending.** No model
requests, SSH operations or verifier processes are invoked by this directory.

For arbitrary finite maps `m,n` and a key set `keep`, prove

```
Restrict(Override(m,n),keep) == Override(Restrict(m,keep),Restrict(n,keep))
```

There is **no disjointness precondition**. `Override` uses the right map's value
whenever a key belongs to both maps. The proof composes domain unions and
intersections with guarded pointwise observations, selects the right map on
overlap, then establishes extensional equality. A hidden observation provider
cannot be called through the immutable public import. No provider supplies this
distribution theorem itself.

The repair seed branches on `q in m` first and claims `Override(m,n)[q]==m[q]`.
Its counterexample is `m=map[0:=1]`, `n=map[0:=2]`, `keep={0}`: the correct value
is 2, not 1. Missing left/right/outer value facts, unjustified disjointness and a
missing domain fact are separate controls. The alternative correct proof branches
on membership in the restricted right map and reverses the order of independent
pointwise observations. Offline tests check the algebra on 5,832 small map/set
combinations, including conflicting overlaps, disjoint domains and empty maps;
they do not establish Dafny verification.

Client A uses `m,n`; client B reverses their roles while retaining right bias.
Both clients and their final specifications are byte-identical across shared and
separate conditions. Shared has one editable helper and a protected forwarding
helper; separate has two equivalent editable helpers, for which copying is
allowed. Source length and output work differ. This fixture does not establish a
causal sharing or minimum-depth effect.

Each condition has reference and alternative positives, seven ordinary negative
controls and one hidden-export resolution control: **20 checks total, expected
4 strict passes, 14 proof failures, and 2 name-resolution failures**. Parse/type/
termination errors cannot satisfy a proof-failure expectation. The expectations
are pending compute validation. Editable byte spans and protected-source hashes
are recorded; the common output-guard registry needs a new task entry before
any prospective model pilot.

This `D4-new-overlap-override` development task extends finite-map restriction
ancestry. It does not rename or replace D4-M2's earlier disjoint-merge task and
does not consume a reserved held-out family. The existing corpus artifacts and
scores remain unchanged.

Construction: `python3 build.py`. Offline tests:
`python3 -m unittest discover -s . -p test_design.py -v`.
`manifest.json` hashes exact generated sources and metadata. No prompt, paid
execution scope or model-call authorization is implied by these fixtures.
