# patch-validation-001 — Reject malformed text edits

**Outcome: PASS.** Date: 2026-10-20. Engineering validation; no model requests.

**Problem:** in [repair-001](../repair-001/README.md), missing closing `@@` delimiters were silently ignored, and subsequent directives deleted the wrong brace.

**Change:** `apply_text_diff` now raises `ValueError` for malformed anchors and unmatched anchor sequences, keep directives, or delete directives. It checks trailing anchors too. The caller receives no partial result. The existing repair worker catches this as a diff error before updating the program. Valid diffs, explanatory prose, and the empty `@@@@` synchronization marker remain supported.

The Dafny, Verus, and Frama-C repair/extension prompts now explicitly require **both** opening and closing anchor markers. The recorded model response is rejected rather than automatically corrected. The assisted correction remains a distinct historical artifact.

## Validation

Tests ran directly through an authenticated SSH connection in Sophie's existing Cannon allocation, using `repodisco` / Python 3.11.17. An isolated copy under `outputs/patch-validation.bPvEdm/` was based on checkout revision `d93fe30b53eb54fde480123aced59045c6307d2e`, with the implementation and test changes included in this commit overlaid. The active research checkout was not edited during validation.

| Check | Result |
| --- | --- |
| Diff, prompt, Dafny verification, and patch module tests | **39 passed in 11.22s** |
| Recorded malformed Claude diff | Rejected explicitly |
| Same diff with the two closing delimiters supplied | Reproduces the saved assisted candidate |
| Dafny verification of the assisted candidate | **4 verified, 0 errors** |
| Model calls | **0** |

[Captured validation output](validation-output.txt).

Commands within the validation checkout:

```bash
python -m pytest tests/test_diff.py tests/test_prompt_formatters.py tests/test_dafny_backend.py::TestVerify patch.py -q
python experiments/repair-001/reproduce-patch.py
dafny verify experiments/repair-001/anchor-normalization-candidate.dfy
```

Local Python 3.12.8 validation also passed 31 tests (excluding the eight tests requiring the Cannon Dafny installation).

**Limits:** this does not establish a higher model repair success rate. A fresh model trial will have different prompt/parser behavior and must be recorded separately. Forward matching can still be ambiguous when a valid anchor has insufficient context; this change rejects invalid or missing matches rather than guaranteeing every valid edit expresses the intended location.

**Next research step:** one new bounded repair trial starting from the original failed extension, with exact prompts, responses, token usage, configuration, and verifier results captured.

[All experiments](../README.md).
