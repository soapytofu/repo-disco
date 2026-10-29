# Saved-response output diagnostic — separate from frozen scoring

The original 32-call pilot is complete and published, strict score 18/32. This
non-paid analysis examines eleven rejected responses without new model requests,
feedback or proof rewriting. Three JSON-wrapper rejections remain excluded.

For five responses, append exactly one final LF when missing; all other source
bytes are identical. For six, retain source verbatim and extend a separate copy of
the bounded grammar to admit pure inline if-then-else expressions. The frozen
original guard and scores are unchanged. Includes/contracts/imports/attributes and
all source outside the existing proof bodies remain protected. Four offline tests
pass, including attempted assumptions, side-effect calls and contract edits.

A single verifier-only compute job checks all eleven candidates, recording exact
source hashes and raw logs. This is a post-hoc diagnostic with different acceptance
rules, not a replacement calibration score or extra independent model trials.
Job **56022487** completed on non-preemptible test in 33s: **11/11 candidates
verified**, with full source/hash/guard and original-response review. Zero new
model calls. The original score remains **18/32**; three wrapper failures were
not evaluated. This shows the eleven selected failures were output-policy effects,
not failed Dafny obligations under this diagnostic. It does not retrospectively
change the frozen acceptance policy or establish a new unbiased model score.
