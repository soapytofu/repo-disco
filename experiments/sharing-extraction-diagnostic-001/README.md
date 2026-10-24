# Post-hoc extraction diagnostic of the eight saved responses

**Diagnostic only; no new model calls.** The original sharing-model-pilot-001 results are unchanged: shared 0/4 and separate 0/4 accepted under the frozen JSON-only rule. This experiment asks whether usable proof content exists inside those rejected responses; it does not retroactively change the primary outcome.

## Extraction rule and provenance

Scan the saved response text for a single decodable JSON object containing exactly ClientA.dfy and ClientB.dfy string values. Reject duplicate keys, multiple candidate objects, or non-whitespace content after the object. Remove the prose prefix and trailing whitespace only. Preserve the exact JSON substring and use standard JSON decoding; do not repair or modify proof statements. Apply the original protected-byte edit guard and evaluator unchanged.

All eight responses contain one such object. All recovered pairs pass the original guard; all 16 client files match their reference sources ignoring whitespace. `extraction.json` records source response hashes, character offsets, removal counts and reference comparisons. `extracted/` holds the exact JSON substrings and decoded source. Source records remain in sharing-model-pilot-001/model-001; that directory is not edited.

Verifier-only job **54975787** completed successfully on compute node holy7c04108 in 68 seconds, with requeue disabled. All **24/24 checks passed**: All.dfy and both clients for each recovered response. Shared: **4/4 recovered pairs verified**; separate: **4/4 recovered pairs verified**. Full stdout/stderr, commands, source hashes, input snapshots and environment details are in `verification-001/`; scheduler logs are stored alongside it. `review.json` records independent provenance and protected-source checks. No credentials, model SDK, API requests, or retry loop are used.

Two offline extractor tests cover exact substring preservation, duplicate keys, ambiguity, trailing prose and incomplete objects. `evaluator/harness.py` is an unchanged copy of the original frozen evaluator. `verify.py` snapshots inputs and logs full commands, output, errors, hashes and outcomes. Run verification only on compute nodes.

## Interpretation

The recovered proofs verify, showing that all eight saved responses contained valid solutions despite violating the requested output format. It will not demonstrate end-to-end success under the original protocol or a sharing advantage. This procedure was chosen after seeing the failures; any future tolerant parser must be frozen and validated before collecting a new model batch.
