# Map prerequisite-selection development candidates

Two fresh instances use a fixed `ClientA/ClientB → HelperB → HelperA` architecture.
Only `HelperA.Prove` and `HelperB.Prove` bodies are eligible for edits. Imports,
providers, contracts, exports and both clients are immutable. Both seed helper
bodies are nonempty; exactly one differs from its reference in each seed.
The enclosing study is prospective. No model requests or Dafny verification have
been run for these candidates by the constructor.

`inverse_exchange_pipeline` starts with two mutually inverse finite integer maps.
It exchanges values at distinct keys `p,q` in the forward map and at the **values**
`m[p],m[q]` in the inverse map. HelperA derives generic exchange domain/pointwise
facts from elementary opaque map-update laws. HelperB applies that prerequisite to
both maps and proves both inverse directions. The seed's second prerequisite call
incorrectly uses `p,q` as keys in the inverse map. The counterexample
`m={0:10,1:20}`, `n={10:0,20:1}` distinguishes key and value spaces.

`masked_override_composition_pipeline` proves
`Compose(Override(f1,f2),g) == Override(Compose(Restrict(f1,f1.Keys-f2.Keys),g),Compose(f2,g))`.
HelperA proves domain equality, including keys removed because the overriding
right value is absent from `g`. HelperB uses that contract and proves pointwise
values. The seed incorrectly retains an overwritten left-domain key when the old
value is in `g`: `f1={0:10}`, `f2={0:20}`, `g={10:1}` gives an empty correct result,
whereas unmasked left composition wrongly retains key `0`.

The two clients exercise each target under direct and reversed/transformed inputs.
An individual Dafny client unit can pass assuming a failed helper's contract.
Whole-repository verification and the dependency-closed acceptance gate must still
reject both client targets when their helper chain is invalid. Do not equate
conditional client-unit success with a verified repository.

There are 21 distinct planned verifier checks: four successes, fifteen ordinary
proof failures and two hidden-export name failures. Reference and alternative proofs, empty bodies, missing prerequisite
facts, wrong key/priority facts, and only-A/only-B repair controls are preserved.
The four only-A/only-B controls are exact source-hash/evidence aliases in
`control-aliases.json`; they reuse reference/faulty evidence without new verifier
calls and are not independent trials.
Expected diagnostic categories remain predictions until compute verification.
All successful controls must have strict exit zero and no warnings; proof failures
must not be confused with parser/type/resolution failures.

This is a fixed-architecture repair selection task, not a shared-versus-separate
comparison. It deliberately exposes two eligible files with different roles and
one actual seeded defect. The file to change can potentially be inferred from
verifier locations, provider signatures, or source inspection; a feedback benefit
would require the planned matched comparison. There is no uniqueness/minimum-proof
claim. Both instances adapt the existing finite-map development ancestry; neither
is a held-out family.

`build.py` deterministically emits 183 Dafny files, task/case metadata, per-file typed
grammar rules and a flat fixture manifest. `test_structure.py` checks exact scope,
single-fault construction, grammar admission and finite mathematical examples.
These offline checks do not establish Dafny validity. `file_rules.json` supplies
the separate guard agent with per-file parameters, call signatures and pure
function types; no old guard or frozen experiment is changed. The copied witness
verifier is imported unchanged by the thin `verify.py` adapter, which overrides
only its root and pin validation. The copied original CLI must not be invoked
directly. The flat runtime/fixture manifests bind this self-contained bundle;
`verify.sbatch` requests a single no-requeue `test` job after the parent confirms
live nonpreemptibility. Raw source, version output, stdout/stderr, base64/CSV and
exact diagnostic evidence are retained by the existing loop. Root owns submission,
diagnostic review and any separately frozen prompts.
