# Internal-contract propagation: two prospective API migrations

**Prospective verifier-only study; no results yet.** These two development tasks
change an internal helper's precondition and return meaning while keeping the
public `Client.Target` signature, preconditions and postconditions byte-identical.
They are outside the earlier body-only repair protocols. There is no model prompt,
output guard, runner, paid allocation or permission to edit prior experiments.

The question is whether a chosen locally valid helper change breaks an actual
caller proof, and whether a coordinated caller adaptation restores the same
public behavior. The verifier must report the real `Helper.Transfer` and
`Client.Target` obligations. A declared dependency closure is not a substitute
for a failed caller obligation here.

## Capped endpoint to relative advance

Initially, `Helper.Transfer(start,length,cap)` requires `length>=0` and returns
the absolute endpoint `min(cap,start+length)`. The public client returns that
endpoint for every such input, including `start>cap`.

The proposed internal API instead requires `start<=cap` and returns a relative
advance `delta`, with `0<=delta<=length` and
`start+delta=min(cap,start+length)`. The adapted caller handles `start>cap`
itself; otherwise it adds the origin back to the returned advance.

The helper-only migration violates the old caller's call precondition when
`start=4,length=1,cap=3`. Even in the new helper's domain, at `(1,1,5)` the old
caller returns `1` rather than the required `2`. The converse caller-only
migration receives the old absolute result `2`, adds the origin, and returns
`3` rather than `2`.

## Map remainder to extracted-entry patch

Initially, `Helper.Transfer(m,key)` returns the map excluding `key`, for present
or absent keys. The public client returns both that exact remainder and the
one-key removed-entry map (empty when the key is absent).

The proposed internal API requires `key in m` and returns the extracted one-key
entry instead. The adapted caller handles absent keys itself. For a present key
it returns the extracted entry as the removed map and excludes that patch's keys
from the input to form the remainder.

For `m={1:10,2:20}, key=1`, the helper-only migration presents `{1:10}` where the
old caller requires remainder `{2:20}`. The caller-only migration instead treats
old remainder `{2:20}` as the removal patch, producing remainder `{1:10}` and
reporting the wrong removed entry. An absent key additionally witnesses the new
helper precondition that the original caller cannot establish.

## Planned controls and interpretation

Each task has an initial/reference implementation, a helper-only API migration,
a caller-only adaptation, a coherent paired migration, and an alternative valid
paired implementation. Additional negatives change only the internal contract,
omit the new caller guard, lose the return-value transformation, or implement
the new helper result incorrectly. The initial, paired and alternative cases
must strictly pass; every negative must be an ordinary proof failure with the
predicted named target and diagnostic. Public-contract tampering is a separate
offline construction rejection, never a proof-failure score.

These controls show insufficiency of the particular one-sided changes. They do
not show that two files must change in every valid solution: keeping the original
API preserves the original behavior, and a caller may have other implementations.
The new internal return semantics are explicitly introduced migration goals;
they are not defects discovered in the original correct program.

All sources belong to known arithmetic and finite-map development lineages.
Tree and transition reservations remain untouched. Finite Python examples are
sanity checks only; fresh compute-node Dafny verification is required before any
semantic result is claimed. The parent owns compute submission and publication.

`build.py` deterministically emits 18 distinct workspace cases: six expected
strict successes followed by twelve ordinary proof failures. `test_structure.py`
checks construction/public-contract protection, 180 arithmetic configurations,
320 finite-map inputs, exact fake-process source/CSV bytes and isolated imports.
These checks do not replace Dafny verification. The verifier adapter is copied
byte-exact from the reviewed witness adapter and imports only the Python standard
library; no Formal Disco package dependencies or paid handlers are required.
Both runtime and fixture manifests include every dependency used by the isolated
bundle. `verify.sbatch` invokes the one fresh `verification-001` output path on a
compute allocation, pins Dafny and Z3 versions, runs each case once, and saves
the exact sources plus all stdout/stderr/CSV evidence, including unexpected errors.
