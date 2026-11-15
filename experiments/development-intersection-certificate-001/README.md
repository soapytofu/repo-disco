# D3-M1: intersection witness or separation certificate

**Candidate built and tested offline; Dafny verification is pending. No model calls.** This implements the original `D3-M1` proposal's exhaustive positive/negative certificate obligation for nonempty closed integer intervals. It is a development instance in the known relational-witness ancestry, not a held-out family.

The only helper precondition is `a <= b && c <= d`. It must prove that a valid tagged certificate exists:

- `kind = 0`: a point `w` is in both `[a,b]` and `[c,d]`;
- `kind = -1`: `b < c`, so the first interval lies strictly before the second;
- `kind = 1`: `d < a`, so the second interval lies strictly before the first.

Two immutable client **lemmas** return the tag and point through a protected ghost choice rule. Their contracts tie the tag exactly to the overlap or separation condition and require membership for a positive answer. The negative cases ignore the point value. This is a proof-certificate interface; it does not implement or benchmark executable witness search. A later executable interface would require a separate protocol decision.

The reference first tests the two strict separation conditions and otherwise chooses the larger lower endpoint. The alternative first tests overlap and chooses the smaller upper endpoint, then handles the two negative outcomes. The helper must establish the applicable opaque membership or strict-gap facts before packaging the corresponding certificate. `Witness` requires both membership facts; `Gap` requires a gap fact with the correct orientation tag. The public proof view hides the direct raw-membership shortcut and the client choice rule. No provider proves the full decision theorem from the helper's input precondition.

Touching is a positive case: `[0,2]` and `[2,5]` share `2`; `b <= c` cannot justify a separation certificate. Choosing a point from only one interval remains invalid, and reversing the negative tag is also unsound. `semantic-cases.json` records concrete counterexamples. Missing certificate facts are separate proof-dependency controls: their mathematical conclusion may be true, but the required opaque evidence is missing.

The two immutable clients use direct inputs and a common translation with the interval order swapped. Shared mode edits one helper body with a protected forwarding helper; separate mode edits two equivalent helper bodies and permits copying. The providers, clients and final meanings match exactly. Editable-body count, source length and output work differ, so this is not a pure causal sharing experiment. Reference call dependencies do not establish minimal proof depth.

## Development lineage and validation plan

The earlier `intersection-witness-001` requires overlap in its input assumptions. The exact-gap task also assumes its translated intervals are feasible. This instance removes that feasibility assumption and requires sound, exhaustive positive **and negative** branches. Its overlap branch still uses the known max-lower/min-upper construction and opaque membership packaging. That is a new logical obligation within an inspected family, not independent semantic ancestry. `lineage.json` preserves the exact original proposal record and hashes; the cited plan, antecedent generators, grammar and verifier wrapper are copied under `inputs/` for stable provenance. Reserved tree and transition families are untouched.

There are **20 planned verifier checks** across two sharing conditions: four reference/alternative successes, fourteen ordinary proof failures, and two hidden-export name-resolution failures. The ordinary controls are empty proof, touching-as-disjoint, witness in only one interval, reversed separation tag, omitted gap facts, omitted right-membership fact, and a negative branch without a certificate. No parse, type, termination or warning-only outcome counts as the expected ordinary proof failure.

Eight offline test methods pass. They check deterministic hashes, protected source spans, matched semantics and copying, public views, existing grammar compatibility, concrete counterexamples, and **6,272 finite-domain outcome checks**, including translated/swapped clients. The current bounded grammar admits all 27 non-hidden helper-body reconstructions under an explicitly proposed task environment and rejects three hidden-helper bodies. These are local syntax/arithmetic checks, not Dafny proofs, model responses or a production guard freeze.

`build.py` emits fixtures, empty templates, task records and the source manifest. `verification-plan.json` gives the pinned toolchain, command, expected cases and existing `verify(files)`/`matches(case, record)` wrapper functions for the parent-owned compute run. Its existing wrapper CLI is specific to its original family and must not be invoked unchanged against this directory. No new verifier framework or job submission script is introduced here. Parent review, compute-only verification and full diagnostic review remain required before any model prompt freeze or collection scope.

```sh
python3 -B experiments/development-intersection-certificate-001/build.py
python3 -B experiments/development-intersection-certificate-001/test_structure.py
```

No existing frozen sources, output policies, result archives or scores were changed. The task registry is a proposal for later guard integration; it does not silently extend the currently running pilot.
