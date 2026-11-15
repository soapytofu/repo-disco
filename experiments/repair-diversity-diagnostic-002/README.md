# Five failed-repair diagnostics

**Status: prepared and guard-validated; compute verification pending.** These are analyst-authored sufficiency hypotheses for five saved failures from `repair-diversity-pilot-002`. The original primary result remains **27/32**. There are no new model requests, retries, replacement trials or rescoring.

| Saved trial | Task / condition | Only proposed change |
| --- | --- | --- |
| 03 | Exact-gap pair, shared | Replace leading `var u := a;` with `var u := if a < c-gap then c-gap else a;`. |
| 15 | Exact-gap pair, separate | Apply the same declaration replacement in both editable helper bodies. |
| 05 | Saturating associativity, separate | Guard the two leading `O.Low` calls with `a+b <= c` and `b+d <= c`, respectively. |
| 09 | Saturating associativity, shared | Apply the same two guards to the existing calls. |
| 28 | Saturating associativity, separate | Apply the same two guards in both editable bodies. |

The witness candidates retain `v := u + gap`, every subsequent statement and all original lemma calls. The arithmetic candidates retain the later region proof verbatim; only the two initially unconditional calls acquire their exact sum-bound conditions. Every candidate preserves the original lemma-call sequence, including arguments. The two separate helper bodies remain duplicates where the model produced duplicate bodies.

These hypotheses address the observed diagnostics: the original witness choices lack the lower bound on `u+gap`, while the original unconditional `O.Low` calls lack their sum-bound preconditions. Passing the proposed edits would establish sufficiency for these saved outputs. It would not establish minimality, model repair success, a general feedback/sharing effect or an independent task-level success rate.

`prepare.py` replays each original response through its exact frozen envelope, body guard and repair adapter, then replays the analyst payload against the original candidate and immutable empty template. Only the listed leading statement text changes. All five edited candidates are admitted by those unchanged policies. Across them, **29 protected files and eight protected body boundaries** match exactly. Guard rejection would be preserved rather than bypassed.

`primary-archive-manifest.json` pins every path and hash in the **1,845-file** original model archive. The bundle preserves **91 exact original response, request, source and evidence files**, plus the original prompt/guard freeze. No original file is rewritten. `cases.json` records source/body hashes, exact edit spans, parent diagnostic hashes and the unchanged original outcomes.

The minimal runtime reuses the original `logging_verifier.py` and `target_metrics.py` byte-for-byte. `preflight.py` runs each of the five distinct candidates once, only on a Slurm compute node, checks Dafny/Z3 versions, saves raw CSV/stdout/stderr/source hashes, and permits no automatic retry or restart. Expected strict results are **9 obligations** for witness trials 03/15 and **7 obligations** for arithmetic trials 05/09/28, all with zero errors and warnings. Any failure remains evidence; the reviewer does not convert it to a success.

Offline reproduction:

```sh
python3 -B experiments/repair-diversity-diagnostic-002/test_design.py
```

The tests include source/guard replay, exact edit and protected-scope checks, coherent diagnostic classification, and a fake-verifier runner/reviewer round trip including a deliberately failed hypothesis. Fake evidence is isolated in temporary directories and cannot pass the default real-evidence reviewer. No model or Dafny invocations occur in these tests.

The remote packaging check runs the six self-contained source/guard/category tests. The primary-archive and two fake reviewer round-trip tests remain local because they inspect the complete original model archive; all nine passed locally. This does not replace the full local preservation review after retrieval.

After the parent reviews the frozen manifest, confirms the partition is currently nonpreemptible, and stages this bundle once, `verify.sbatch` runs the five checks with no requeue. The parent owns submission and retrieval. After completion, run:

```sh
python3 -B experiments/repair-diversity-diagnostic-002/review.py
```

The reviewer checks the original archive, exact parent copies, reconstructed edited sources, named declaration logs and diagnostics. Full raw evidence and a separate analyst-diagnostic summary should be published, retaining all original primary results.
