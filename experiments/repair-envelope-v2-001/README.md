# Repair response envelope v2

This is a separately versioned policy for **future, explicitly frozen pilots**. It extracts a JSON payload and then delegates to the original task body guard. It changes no previous prompt, parser, result or score. The diverse repair pilot remains **16/24** under its original policy. These are development compatibility checks, not new model trials or proof verification.

## Admission policy

`repair-envelope-v2-explicit-json-001` admits either:

1. A whole response consisting of one strict JSON object, with optional ASCII JSON whitespace; or
2. Exactly one explicitly `json`-tagged fenced block containing that object. The tag is case insensitive; only triple backtick fences are supported. Clearly non-JSON explanatory prose and fenced code may surround it.

The object must map string filenames directly to string proof bodies. Nested wrappers, array/scalar roots, duplicate keys, nonstandard numbers, non-string values, invalid JSON, unpaired Unicode surrogates and responses over 262,144 UTF-8 bytes are rejected. A response beginning with an object, array or quoted root must parse in full; the parser never searches inside it for an acceptable child. Unfenced JSON embedded in prose is intentionally unsupported.

The surrounding-text ambiguity rule rejects other JSON-tagged blocks, additional complete or JSON-looking malformed objects, standalone structured roots, JSON-looking arrays outside recognized code expressions, and malformed or unsupported fences. Relabeling an alternate JSON object as `dafny`, `text` or an untagged block does not make it admissible. Duplicate answers are rejected even if identical. Ordinary prose references such as `s[1..]`, `t[0]`, `[a,b]` and the inline expression `K.Weave([],[])` are not treated as alternate JSON containers. A separate Dafny `if` block may explain a proof when it contains no alternate structured answer.

The rule is deliberately bounded and lexical. It is not a semantic classifier for all prose, a general Markdown parser, a Dafny parser or a sandbox. Some valid explanations are rejected, including standalone JSON-looking sequence displays, unmatched inline backticks and code blocks with unsupported fence delimiters. An unquoted brace fragment in ordinary prose is not always identifiable as an intended malformed JSON answer; the implemented checks and adversarial examples define the boundary. Future prompts must request one of the two admitted formats rather than relying on prose recovery.

## Exactness and protected scope

`extract_json` returns the exact selected substring, its character and UTF-8 byte offsets, SHA-256 hashes and the admission mode. JSON decoding does not rewrite the selected payload, proof strings, whitespace or call order. `parse_response(raw, seeds, task, guard)` passes that substring to the separately supplied frozen body guard. The frozen repair adapter additionally checks the original parent and reconstructs candidates from immutable template boundaries. Neither an admitted envelope nor an admitted body establishes mathematical correctness; the verifier remains a separate gate.

Tests reject assumption/reveal/axiom bypasses, added declarations, full-file substitutions, cross-helper delegation, extra or missing file keys and altered protected sources. These tests exercise the existing guards without modifying them or claiming universal protection for arbitrary code.

## Offline evidence

- **20 test methods passed**, including exact offsets, Unicode and escape handling, multiple/hidden/malformed answers, wrappers, size limits and independent body/parent checks.
- **24/24 current saved responses** pass the prospective envelope plus the unchanged original repair/body guards. All reconstructed workspaces exactly match the 16 originally admitted candidates or the eight separately archived exact-extraction diagnostic candidates. This is not a revised primary score.
- **38/40 earlier saved responses** pass and reproduce their prior candidate hashes. The two intentional compatibility rejections are `conditional-monotonicity-pilot-001/model-001/monotone-04/response.json` and `monotone-06/response.json`: both put their JSON object in prose without an explicit JSON fence. The old policy admitted that format; this policy does not.
- All **1,204 original diverse-repair archive files** retain their exact paths and hashes. The replay also pins its old guard, adapter, policy, task, template and response inputs. There were **zero model calls and zero Dafny invocations**.

The nine earlier envelope test categories were reviewed: exact extraction, ambiguity, wrapper rejection, duplicates/malformed JSON, escape preservation, body bypasses, size limits, protected-source checks and unrelated structured containers are covered here. Old positive expectations for unfenced prose JSON are intentionally not carried forward. The exact old test and freeze files are pinned by the replay audit.

During policy design, requiring only one fenced block of any language would have admitted 19/24 current responses and rejected five already-admitted witness outputs with explanatory Dafny blocks (trials 03, 09, 16, 19 and 22). The final rule instead uses explicit-JSON precedence plus the documented ambiguity checks. This decision uses inspected development outputs; it is not blind parser evaluation.

## Reproduce and use prospectively

From the repository root:

```sh
python3 -B experiments/repair-envelope-v2-001/test_extract.py
python3 -B experiments/repair-envelope-v2-001/replay_saved.py
```

`offline-tests.log` and `saved-response-audit.json` preserve the observed outcomes; the latter records exact input hashes and per-response admission decisions. `policy-freeze.json` pins this directory's code, tests, documentation and recorded evidence. It does not authorize a model run. A future pilot must bind the chosen extractor and task body guards in its own freeze and approval before use. All previous policy versions and primary scores remain unchanged.
