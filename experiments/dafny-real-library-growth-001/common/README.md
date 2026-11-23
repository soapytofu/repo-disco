# Protected edits and native evidence replay

This directory supplies an offline edit boundary and a pure Dafny evidence
reviewer for declarative library-extension stages. It does not run a verifier,
send model requests, issue acceptance receipts, or promote repository revisions.
Native qualification for the new libraries must come from their actual saved
baseline and control observations. Synthetic tests are not that qualification.

## Interfaces

```python
candidate, edit_review = guard.reconstruct(
    edit_profile, body_text, exact_parent_sources, chain_id,
    parent=parent_evidence,       # None for stage one
    allow_synthetic=False,
)
native_review = review_native.review(
    native_profile, exact_candidate_sources, record, raw_artifacts,
    host_evidence_pins, allow_synthetic=False,
)
```

Sources and raw artifacts are dictionaries of relative paths to exact `bytes`.
The host stages an isolated candidate. Both functions return evidence reports;
`acceptance_issued` is always false. `render_body` renders a guarded draft or
analyst control without granting stage-two parent authority.

## Edit profile

The `dafny-library-edit-profile-v1` object contains:

- `project`, `stage` (1 or 2), and `stage_id`.
- `base_source_sha256`: every immutable parent `.dfy` file and exact SHA-256.
- `addition`: a fresh `path`, `template_utf8`, `begin_marker`, `end_marker`, and
  `kind` (`method`, `function`, `lemma`, or `predicate`). The marker-delimited
  template body is empty. The prefix and suffix retain all fixed interfaces,
  types, imports, behavioral contracts, and module declarations.
- `registrations`: host-owned files such as `All.dfy`, each with
  `before_sha256` (null for a new registration file) and exact `content_utf8`.
  The model supplies no registration bytes or paths.
- Alternatively, `registrations:{}` is allowed only with `verification_inputs`:
  an exact, unique ordered list of every final source path. No new `All.dfy` is
  invented. The corresponding native profile must carry the same list and its
  exact argv suffix; missing, extra or duplicate source inputs are rejected.
- `forbidden_identifiers`: exact bare identifier tokens from the trusted
  source audit. For example, a forbidden `Encode` token also rejects
  `UTF8.Encode` and `var encode := UTF8.Encode`; comments and strings do not
  invoke code. Use the callable's leaf name, not a dotted qualification. This
  conservatively also excludes any safe same-name identifier.
- `parent_requirement`: null at stage one; at stage two,
  `{stage_id, addition_path, guard_profile_sha256}` identifying stage one.
  The actual accepted addition is omitted from the stage-two base hash map;
  its identity instead comes from the exact accepted-parent evidence.

Bodies admit ordinary loops/invariants, local variables, object creation,
method calls, function expressions, quantifier statements and `calc` blocks.
Strings, characters, identifier primes and nested comments are scanned before
scope checks. Balanced braces, parentheses and brackets must stay within the
current body. New declarations/imports, trust keywords (`assume`, `admit`,
`expect`, etc.), attributes, `decreases *`, and body omission are rejected.
Current limits are ASCII syntax, 65,536 bytes, 32,768 tokens and depth 128.
This is deliberately a lexical boundary, not a complete Dafny parser. Dafny
still decides whether admitted code parses, types, terminates and verifies.

Either a stage-two client that uses the prior API or a direct implementation
may be admitted. Exact parent bytes remain fixed in both cases. Syntactic call
presence is not treated as a proof-dependence requirement.

## Native profile, record and pins

The `dafny-library-native-profile-v1` object contains:

- `project`, `stage` (0 for baseline, 1 or 2 for growth), `stage_id`.
- `inventory_status`: `pending` or `qualified`. Only a reviewed actual native
  profile may be marked qualified; a pending profile never qualifies success.
- `command`: exact native argv, including executable, flags and source inputs.
  When `verification_inputs` is present, it must enumerate all source files
  exactly and match the command's ordered source-argument suffix. New library
  profiles use this mode; the host must bind guard and native profile lists.
- `toolchain`: exact version/hash object selected by the host. Both the before
  and after tool observations must equal this object.
- `csv_columns`: exact ordered CSV header. Supported shapes are
  `TestResult.DisplayName, TestResult.Outcome, TestResult.Duration,
  TestResult.ResourceCount`, with optional final `RandomSeed`; `random_seed`
  is an explicit nonnegative integer. Unknown header aliases are not guessed.
  Actual saved Dafny 4.11 evidence uses the five-column shape.
- `required_units`: `{exact CSV unit label: source path}` for the full scope.
  `unitless_files`: `{source path: reviewed explanation}` for files with no
  logged obligation. Every supplied `.dfy` file must be in exactly one of
  these coverage classes. Staging a source hash alone does not prove coverage.
- `unlogged_definitions`: objects containing `name`, `file`, exact whole-file
  `source_sha256`, and `counted_as_pass:false`. They never add logged passes.
- `inherited_warnings`: exact warning diagnostic lines, preserving
  multiplicity. A new warning or unexplained warning count cannot qualify.
- `ineligible_parent_runs` and `ineligible_parent_raw_fingerprints`: the
  recorded analyst/control provenance barred from future parent acceptance.
  Fingerprints cover the **complete** raw hash map, not shared empty stderr or
  source hashes. A newly verified model candidate may legitimately reproduce a
  reference body; the earlier analyst observation cannot be relabeled.

The `dafny-library-native-record-v1` object contains `run_id`, `origin`,
`source_before_sha256`, `source_after_sha256`, `argv`, `toolchain`,
`toolchain_after`, `raw_sha256`, `exit_code`, `elapsed_seconds`, `timeout`,
`attempts:1`, `model_calls:0`, and `host:{job_id,hostname,partition}`. Origins
are `analyst_qualification`, `model_candidate`, or `synthetic_offline`.

The exact raw dictionary contains `stdout.txt`, `stderr.txt`, `resources.txt`
and all `csv/...csv` files. Resource replay retains GNU time's user/system CPU
seconds, wall time, maximum RSS, and exit status separately from correctness.
Incomplete resource measurements can accompany a timeout/failure but cannot
qualify a successful observation. CSV rows retain original columns, paths,
row numbers, outcomes, resource counters and random seeds. Duplicate units,
stale evidence, changed tools/sources and malformed CSV raise `EvidenceError`.

`EvidencePins` is a trusted-host dataclass with `profile_sha256`,
`record_sha256`, `source_revision_sha256`, sorted `raw_sha256` tuple pairs,
`run_id`, and `origin`. JSON digests use `sha(canonical(object))`; source
revision means `sha(canonical({path:sha(bytes)}))`. The original pretty-printed
record and raw files remain retained separately. A complete raw fingerprint
is `sha(canonical({artifact_path:sha(bytes)}))`.

The reviewer separates ordinary proof failures, frontend parse/resolution,
resource exhaustion, timeout/process failures, missing coverage, summary
disagreement, warning-only exits, and verified outcomes. Exit 2 with only
warnings is never accepted. Exit-zero warnings qualify only when the complete
warning policy matches. A passed client cannot mask a failed parent unit.

## Actual-parent boundary

`ParentEvidence` contains the stage-one native profile, record, raw artifacts,
typed `EvidencePins`, a host-issued receipt, and its externally pinned canonical
SHA. Stage two reruns native review against the supplied parent source bytes.
It requires a qualified stage-one model-origin observation, the exact project,
stage, chain, source revision, policy, native run/record/profile/raw fingerprint,
and model request/response identity. The receipt fields are listed by
`validate_parent` in `guard.py`; no issuer exists here.

An arbitrary self-consistent JSON object is not an authority. A trusted host
must review and freeze profiles, own the one native process, bind its evidence
to the actual guarded model response/request, and choose the pins. These
Python types and hashes check identity relative to that authority; they do not
cryptographically authenticate caller-supplied claims. Default calls reject
synthetic evidence. Analyst observations remain parent-ineligible even if
native verification succeeds. Known recorded control runs/full raw evidence
are separately barred against label substitution. Tests use an explicit
synthetic opt-in and never create a live/model acceptance.

## Validation and origins

Run only the offline suite with `python3 -B -m unittest -v test_protocol` from
this directory. `reviews/` retains each transcript, exit and exact tested code
hashes; no test invokes Dafny, an API or a provider. The tests exercise coverage,
tool/source/raw integrity, native categories, broader syntax and actual-parent
binding with visibly synthetic fixtures.

The new files have no runtime dependency on old experiments. Coverage parsing
and count checks were adapted from
`real-repository-evolution-001/harness-001/dafny_gate.py`
(SHA-256 `48aba9059cf86d06d0577f9d2b92fed3f9e7ed9e7e5008d4cc8825757e12cd86`).
The provenance boundary follows the independently reviewed growth protocol's
`protocol-003/integration.py`
(`affe3059d247489a5f2e5d2f46c21d48e0d94e36dc1c4c07464f2178d924c079`)
and `body_policy.py`
(`e3f50a39e9bc6b2fe5df54a3e4177e4d9d2eef197b2af2873dfbf8660ab2273f`).
Those original files and their freezes remain unchanged.
