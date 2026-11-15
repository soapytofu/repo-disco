# Two-module witness repair selection

**Constructed development fixtures; not yet verified by Dafny.** No model calls
or corpus freeze are performed here. Two different proof modules are eligible in
each task: `HelperA.Prove` supplies an intermediate certificate;
`HelperB.Prove` composes it into the result used by both immutable clients.
The fixed architecture has no shared/separate factor. It provides a choice of
which eligible body to change, rather than unrestricted file discovery.

`intersection_or_separation-pipeline` is a new pipeline layout of the original
D3-M1 obligation. HelperA certifies the canonical maximum-lower-endpoint witness
under overlap assumptions. HelperB must handle overlap and both strictly ordered
separation cases. Its seed incorrectly uses `b <= c` to enter the left-separation
branch. Touching intervals `[0,2]`, `[2,5]` require the positive certificate at 2.
The original D3-M1 layout's verification cannot establish this layout's validity.

`conserved_sum_gap-pipeline` combines interval bounds, a fixed sum and a positive
gap. It requires `a<=b`, `c<=d`, `a<=s-c`, `s-d<=b`, `g>0`, `a+a+g<=s`, and
`(s-d)+(s-d)+g<=s`. Put `L=max(a,s-d)`: the inequalities ensure
`L<=min(b,s-c)` and `L+L+g<=s`. Thus `u=L,v=s-L` satisfies both intervals,
`u+v=s`, and `u+g<=v`. Conversely any satisfying pair implies every listed
inequality. HelperA establishes the bounded, sum-preserving canonical pair;
HelperB establishes the gap and packages existence. The seed instead uses `u=a`:
for `[0,4]`, `[0,3]`, `s=5,g=1`, it chooses `(0,5)` instead of the valid `(2,3)`.

The first seed fails in HelperB; the second in HelperA. Both source bodies are
nonempty and contain no fault labels, comments or empty-stub markers. The empty
templates are host-side reconstruction inputs and must not appear in model
prompts. Future arms must have identical full failing source, eligible files and
syntax; only the declared verifier-feedback condition may differ. The model
returns both complete body strings, preserving a sound body unchanged if desired.
All roles visible in the source are legitimate context; no blind localization
claim is made.

The 24 prospective checks comprise 6 successes, 16 ordinary proof failures and 2
hidden-export resolution failures. Every workspace is byte-distinct. The
only-A/only-B repair controls use alternative valid bodies so they do not duplicate
reference/base verification. Changing the already-sound module alone must leave
the seeded failure. Contracts, exports, provider proofs, clients and attributes
are identical across each task's controls. Hidden shortcuts are intentionally
excluded by named export views; no assumption or verification bypass is used.

Clients return ghost witnesses through protected existential-choice lemmas;
this is proof repair, not an executable search benchmark. ClientB exercises a
translated/swapped interval decision or a translated pair with its sum increased
by twice the shift. Local client verification must not count as repository
success while an upstream helper is unproved. `tasks.json` supplies the exact
A→B→clients graph, per-file parameter/call/pure-symbol types and source spans for
the prospective guard. No minimum proof depth is claimed.

The offline tests check deterministic source hashes, all immutable bytes, distinct
control workspaces, one-module repair differences, and compatibility with the
existing bounded AST grammar (46 admitted bodies; 2 hidden calls rejected).
Finite checks cover 225 interval configurations and 12,375 sum/gap configurations,
including negative integers and transformed clients. They are arithmetic sanity
checks, not proofs over arbitrary integers or Dafny validation.

`build.py` generates exact fixtures/templates and flat manifests.
`test_structure.py` is the offline compute-staging entry point and also checks a
single fake process's exact source/CSV byte preservation. `verify.py` is copied
unchanged from the reviewed prior witness adapter: it requires a compute
allocation, checks runtime/fixture pins and toolchain versions, runs each case
once, and saves raw stdout/stderr/CSV plus every unexpected diagnostic. Root owns
staging, partition confirmation, submission, evidence review and publication.

All tasks are adaptively designed within previously inspected development
lineages. Source ancestors and their hashes are preserved under `inputs/` and
`lineage.json`. Tree and transition reservations are untouched. Old task sources,
guards, primary scores and archives remain unchanged.
