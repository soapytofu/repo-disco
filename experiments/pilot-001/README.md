# pilot-001 — Generate an integer maximum utility

**Outcome: PASS — 2 verified, 0 errors.**

| Field | Record |
| --- | --- |
| Date | 2026-10-14 |
| Question | Can the generation worker produce a verified program from a small natural-language seed? |
| Input | Synthetic integer-maximum description; no parent program |
| Model / provider | `gpt-5.6-luna`, low reasoning effort / OpenAI |
| Attempts | 1 generation attempt |
| Run ID | `20261014-020549` |
| Framework starting revision | `3d9a57fdc3f8d59a2547345dd16a3654fe3eb5a1` |
| Verifier setup | Dafny 4.11.0; Z3 4.12.1 |
| Token usage / measured cost | Not captured in this summary |

**Program:** `Max(a, b)` returns one of the inputs and is greater than or equal to both. `TestMax` asserts those properties.

**Evidence:** [seed](seed.jsonl) · [verified program](verified-program.dfy) · [model record](generation-record.json) · [run configuration](run-config.yaml). The verifier count was recorded in the original experiment README; a separate raw verifier-output file was not archived here.

**Interpretation:** the single-program generation and verification path worked for this seed. This does not test repair, extension, multi-module repositories, or reproduce the paper's baseline.

**Follow-up:** [extension-001](../extension-001/README.md). [All experiments](../README.md).
