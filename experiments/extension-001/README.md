# extension-001 — Add algebraic properties

**Outcome: FAIL — Dafny parse error.**

| Field | Record |
| --- | --- |
| Date | 2026-10-14 |
| Question | Can the editor extend a verified program with additional properties? |
| Parent | [pilot-001](../pilot-001/README.md) |
| Model / provider | `gpt-5.6-luna`, low reasoning effort / OpenAI |
| Attempts | 1 additional model request; cumulative agenda limit 2 |
| Run ID | `extension-pilot-20261014-022417` |
| Verifier setup | Dafny 4.11.0; Z3 4.12.1 |
| Token usage / measured cost | Not captured in this summary |

**Change attempted:** add `MaxCommutative` and `TestMaxAlgebra` to establish commutativity, idempotence, and associativity of `Max`.

**Failure:** the model inserted the new declarations between `method TestMax(a: int, b: int)` and its body, leaving an unexpected opening brace. The saved verifier output reports one parse error at line 37. The added proofs have not been verified.

**Evidence:** [input program](../pilot-001/verified-program.dfy) · [failed output](extended-program.dfy) · [model record](generation-record.json) · [run configuration](run-config.yaml) · [verifier output](verifier-output.txt) · [scheduler log](scheduler.log).

**Resume checkpoint:** `outputs/extension-pilot-20261014-022417/agenda.pkl` on the original Cannon checkout; ignored by Git and not restored by cloning.

**Interpretation:** this is a structural editing failure. It does not show that the intended mathematical properties are false.

**Follow-up:** [repair-001](../repair-001/README.md), using the failed program and verifier feedback. [All experiments](../README.md).
