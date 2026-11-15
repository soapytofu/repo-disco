# Four fresh development repair tasks

All **78 verifier controls** matched their expected outcomes: **16 strict reference/alternative passes, 52 proof failures, 2 termination failures and 8 hidden-export resolution failures**. No model calls were used. Each task has matched shared/separate workspaces with immutable providers, clients and contracts.

| Task | Semantic obligation | Controls | Evidence |
| --- | --- | ---: | --- |
| Saturating addition | Establish the correct intermediate saturation cases to prove associativity |18|[Arithmetic](arithmetic/RESULTS.md)|
| Adjacent compression | Propagate the clean-tail invariant through an inductive fixed-point proof; clients derive idempotence |20|[Sequence](sequence/RESULTS.md)|
| Exact positive-gap pair | Construct points in two intervals under exact feasibility inequalities, then compose opaque certificates |20|[Witness](witness/RESULTS.md)|
| Overlapping override/restriction | Select right-map values on collisions and compose domain/value facts |20|[Maps](maps/RESULTS.md)|

The [validation gate](validation-gate.json) pins every case, reviewed source, runtime and diagnostic. [review_verification.py](review_verification.py) checks whole-workspace named coverage, protected bytes, actual categories and complete evidence. All failed controls and pre-verification design records remain preserved. [compute_ops.py](compute_ops.py) records one submission per distinct bundle and never retries.

The separate [body policy](protocol/README.md) passes 20 offline tests: 70 non-hidden workspaces /105 helper bodies reconstructed exactly and8 hidden controls rejected. The prospective [envelope policy](../repair-envelope-v2-001/README.md) is pinned unchanged. Grammar admission and mathematical verification remain distinct gates.

These four familiar-family development instances are not held out. The faults are analyst-constructed, separate proofs may be copied, and separate mode requires twice as many editable bodies. Reference dependency paths do not prove necessary reasoning depth. A future matched repair batch must freeze exact prompts, order, feedback masking and runner before consuming the separately authorized research-window budget. No model outcome is reported here.
