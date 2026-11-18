"""Offline edit and accepted-parent binding policy; never verifies or promotes.

The host must supply pins from its reviewed native evidence gate. Self-consistent
JSON is not evidence authenticity. Nothing here creates an accepted revision.
"""
from dataclasses import asdict, dataclass
import hashlib
import json
from pathlib import Path, PurePosixPath
import re

from inherited.body_guard import tokens, syntax_context, sequence_update, assigned_roots
from inherited.extract_response import extract_json, unique, reject_constant

ROOT = Path(__file__).resolve().parent
VERSION = "sequential-real-repository-growth-policy-v1"
SPEC_SHA256 = "cd02279e50f39762a67dcbf9ae5fba4eeca90c7ffcc4fbe0e16813c89fedf3c5"
HEX = re.compile(r"[0-9a-f]{64}\Z")
NAME = re.compile(r"[A-Za-z_][A-Za-z_0-9]*\Z")
IDENTITY = re.compile(r"[A-Za-z0-9][A-Za-z0-9_.:-]{0,127}\Z")
TYPE_WORDS = {"Seq", "u8", "u16", "u32", "u64", "int", "nat", "bool"}
MORE_FORBIDDEN = {"reveal", "hide", "expect", "opaque", "trusted", "decreases_by",
                  "broadcast", "group", "autospec", "fuel", "recommends", "exec"}
RULES = {
    "vmc-move": dict(inputs={"xs", "k"}, roots={"Model", "T"},
                     calls={"Model.Swap", "MoveToFront", "multiset"}, methods=set()),
    "vmc-pair": dict(inputs={"xs", "i", "j"}, roots={"Shift", "T"},
                     calls={"Shift.MoveToFront", "multiset"}, methods=set()),
    "vest-frame": dict(inputs={"payload", "tail"}, roots={"U16Le", "Seq", "Varied"},
                       calls={"frame_format", "frame_value", "frame_len", "payload_fits",
                              "encode_frame", "decode_frame", "Some", "Varied", "Seq::empty"},
                       methods={"len", "consistent", "unambiguous", "serialize_dps_inv",
                                "byte_len", "theorem_serialize_dps_parse_roundtrip",
                                "lemma_serialize_dps_len", "lemma_serialize_dps_prepend",
                                "spec_serialize_dps", "spec_parse"}),
    "vest-batch": dict(inputs={"payloads", "tail"}, roots={"Seq"},
                       calls={"batch_roundtrip", "batch_fits", "batch_len", "encode_batch",
                              "decode_batch", "frame_roundtrip", "frame_len", "payload_fits",
                              "encode_frame", "decode_frame", "Some", "Seq::empty"},
                       methods={"len", "drop_first", "take", "skip", "subrange"}),
}


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode()


def read_json(raw):
    if not isinstance(raw, bytes) or len(raw) > 16 * 1024 * 1024:
        raise ValueError("Bounded JSON bytes required")
    try:
        return json.loads(raw, object_pairs_hook=unique, parse_constant=reject_constant)
    except (UnicodeDecodeError, RecursionError) as error:
        raise ValueError("Invalid bounded JSON") from error


def path_name(name):
    if (not isinstance(name, str) or not name or not name.isascii() or "\\" in name
            or any(ord(ch) < 32 for ch in name) or name.startswith("/")
            or any(part in ("", ".", "..") for part in name.split("/"))
            or str(PurePosixPath(name)) != name):
        raise ValueError("Canonical relative path required")
    return name


def digest_map(mapping):
    if not isinstance(mapping, dict) or not mapping:
        raise ValueError("Nonempty hash inventory required")
    for name, digest in mapping.items():
        path_name(name)
        if not isinstance(digest, str) or not HEX.fullmatch(digest):
            raise ValueError("Invalid source/evidence digest")
    return sha(canonical(mapping))


def source_hashes(sources):
    if not isinstance(sources, dict) or not sources:
        raise ValueError("Complete source byte map required")
    for name, raw in sources.items():
        path_name(name)
        if not isinstance(raw, bytes):
            raise ValueError("Exact source bytes required")
    return {name: sha(raw) for name, raw in sorted(sources.items())}


def load_assets():
    raw = (ROOT / "policy-spec.json").read_bytes()
    if sha(raw) != SPEC_SHA256:
        raise ValueError("Policy specification drift")
    spec = read_json(raw)
    inventory_raw = (ROOT / "upstream-inventory.json").read_bytes()
    if sha(inventory_raw) != spec["upstream_inventory_sha256"]:
        raise ValueError("Upstream inventory drift")
    for name, expected in spec["inherited"].items():
        if sha((ROOT / "inherited" / name).read_bytes()) != expected:
            raise ValueError("Inherited parser drift")
    for stage in spec["stages"].values():
        raw = (ROOT / "templates" / stage["template"]).read_bytes()
        if sha(raw) != stage["template_sha256"]:
            raise ValueError("Fixed template drift")
    return spec, read_json(inventory_raw)


def policy_digest():
    """Runtime identity the host must pin, independent of notes and test logs."""
    spec, _ = load_assets()
    files = {"policy.py": sha(Path(__file__).read_bytes()),
             "policy-spec.json": SPEC_SHA256,
             "upstream-inventory.json": spec["upstream_inventory_sha256"]}
    files.update({"inherited/" + name: digest for name, digest in spec["inherited"].items()})
    files.update({"templates/" + item["template"]: item["template_sha256"]
                  for item in spec["stages"].values()})
    return sha(canonical(files))


def stage_spec(stage_id):
    spec, inventory = load_assets()
    if stage_id not in spec["stages"]:
        raise ValueError("Unknown growth stage")
    return spec["stages"][stage_id], spec, inventory


def fixed_parts(stage_id):
    stage, _, _ = stage_spec(stage_id)
    raw = (ROOT / "templates" / stage["template"]).read_bytes()
    begin, end = stage["begin"].encode(), stage["end"].encode()
    if raw.count(begin) != 1 or raw.count(end) != 1:
        raise ValueError("Ambiguous fixed body boundary")
    prefix, suffix = raw.split(begin)[0] + begin, end + raw.split(end)[1]
    if sha(prefix) != stage["prefix_sha256"] or sha(suffix) != stage["suffix_sha256"]:
        raise ValueError("Fixed prefix/suffix drift")
    return prefix, suffix


def source_body(stage_id, raw):
    prefix, suffix = fixed_parts(stage_id)
    if (not isinstance(raw, bytes) or not raw.startswith(prefix) or not raw.endswith(suffix)
            or len(raw) < len(prefix) + len(suffix)):
        raise ValueError("Changed protected file header, contract or footer")
    try:
        body = raw[len(prefix):len(raw) - len(suffix)].decode("ascii")
    except UnicodeDecodeError as error:
        raise ValueError("Body must be ASCII") from error
    validate_body(stage_id, body)
    return body


def _without_turbofish(ts):
    """Normalize only explicit closed type arguments for call-name inspection."""
    out = []
    i = 0
    while i < len(ts):
        if ts[i:i + 2] == ["::", "<"]:
            j, depth = i + 2, 1
            while j < len(ts) and depth:
                word = ts[j]
                if word == "<":
                    depth += 1
                elif word == ">":
                    depth -= 1
                elif word not in TYPE_WORDS | {","}:
                    raise ValueError("Unsupported explicit type arguments")
                j += 1
            if depth or j == i + 3:
                raise ValueError("Malformed explicit type arguments")
            i = j
        else:
            out.append(ts[i])
            i += 1
    return out


def validate_body(stage_id, body):
    if stage_id not in RULES:
        raise ValueError("Unknown growth stage")
    rule = RULES[stage_id]
    is_vest = stage_id.startswith("vest")
    ts = tokens(body)
    if MORE_FORBIDDEN.intersection(ts):
        raise ValueError("Unapproved proof or declaration mechanism")
    if not is_vest and not ts:
        raise ValueError("Dafny function result expression required")
    if not is_vest and "=~=" in ts:
        raise ValueError("Verus equality is not Dafny syntax")
    if any(ts[i:i + 2] == ["=", ">"] for i in range(len(ts) - 1)):
        raise ValueError("No lambda or match-arm syntax in these bodies")
    bound = set(rule["inputs"])
    reserved = (bound | rule["roots"] | TYPE_WORDS | {"assert", "calc", "seq"}
                | {re.split(r"\.|::", call)[0] for call in rule["calls"]})
    locals_ = set()
    for i, word in enumerate(ts):
        if word in ("let", "var"):
            j = i + 1
            names = []
            while j < len(ts) and ts[j] not in (":", ":=", "=", ";"):
                if NAME.fullmatch(ts[j]):
                    names.append(ts[j])
                elif ts[j] not in ("(", ")", ","):
                    raise ValueError("Only simple or tuple local bindings")
                j += 1
            if not names or j == len(ts) or ts[j] == ";":
                raise ValueError("Malformed local binding")
            if reserved.intersection(names):
                raise ValueError("Protected input, type or API shadowing")
            locals_.update(names)
    # Verus choose/quantifier binders are expressions, not unapproved closures.
    # Every vertical bar must belong to one explicitly typed binder pair.
    bars = set()
    if is_vest:
        for i, word in enumerate(ts):
            if word in ("choose", "forall", "exists"):
                if i + 1 >= len(ts) or ts[i + 1] != "|":
                    raise ValueError("Typed quantifier binder required")
                j = i + 2
                expect_name = True
                while j < len(ts) and ts[j] != "|":
                    if expect_name:
                        if (not NAME.fullmatch(ts[j]) or ts[j] in reserved
                                or j + 1 >= len(ts) or ts[j + 1] != ":"):
                            raise ValueError("Protected or malformed quantified binder")
                        locals_.add(ts[j])
                        j += 2
                        expect_name = False
                    elif ts[j] == ",":
                        expect_name = True
                        j += 1
                    elif ts[j] in TYPE_WORDS | {"<", ">"}:
                        j += 1
                    else:
                        raise ValueError("Unsupported quantified type")
                if j == len(ts) or expect_name:
                    raise ValueError("Unclosed quantified binder")
                bars.update((i + 1, j))
        for i, word in enumerate(ts):
            if word == "|" and i not in bars:
                raise ValueError("No new closure or bitwise bar syntax")
            if word == "||" and (i == 0 or ts[i - 1] in ("=", "(", "{", ",", ";")):
                raise ValueError("No zero-argument closures")
    pairs, parents = syntax_context(ts)
    for i, word in enumerate(ts):
        if word in ("=", ":=") and i:
            if not is_vest and word == ":=" and sequence_update(ts, i, pairs, parents):
                continue
            if assigned_roots(ts, i - 1, pairs) & bound:
                raise ValueError("Protected input assignment")
        if word == "!" and i and NAME.fullmatch(ts[i - 1]):
            if is_vest and ts[i - 1] == "seq" and ts[i + 1:i + 2] == ["["]:
                continue
            negation_prefix = {"if", "else"} | ({"assert", "then"} if not is_vest else set())
            if ts[i - 1] not in negation_prefix:
                raise ValueError("Only the fixed Verus seq macro is allowed")
    call_tokens = _without_turbofish(ts) if is_vest else ts
    calls = []
    for i, word in enumerate(call_tokens):
        if word != "(" or not i:
            continue
        previous = call_tokens[i - 1]
        if NAME.fullmatch(previous):
            start = i - 1
            while (start >= 2 and call_tokens[start - 1] in (".", "::")
                   and re.fullmatch(r"[A-Za-z_0-9]+", call_tokens[start - 2])):
                start -= 2
            callee = "".join(call_tokens[start:i])
            if callee in ("assert", "if"):
                continue
            if callee in rule["calls"]:
                calls.append(callee)
                continue
            if is_vest and previous in rule["methods"] and start >= 1 and call_tokens[start - 1] == ".":
                # Receiver is a previously checked expression, e.g. Varied(n).
                if start >= 2 and call_tokens[start - 2] in (")", "]"):
                    calls.append("<expression>." + previous)
                    continue
            if is_vest and "." in callee:
                receiver, method = callee.rsplit(".", 1)
                if receiver in locals_ | bound | rule["roots"] and method in rule["methods"]:
                    calls.append(callee)
                    continue
            raise ValueError("Call outside closed vocabulary: " + callee)
        if previous in (")", "]", ">"):
            raise ValueError("Indirect function calls are forbidden")
    stage, _, _ = stage_spec(stage_id)
    parent_calls = [call for call in calls if call in stage["parent_calls"]]
    return dict(policy=VERSION, tokens=len(ts), locals=sorted(locals_), calls=calls,
                parent_api_calls=parent_calls, parent_call_required=False,
                semantics_checked=False)


def render_source(stage_id, body):
    decision = validate_body(stage_id, body)
    rendered = body if not body or body.endswith("\n") else body + "\n"
    prefix, suffix = fixed_parts(stage_id)
    raw = prefix + rendered.encode("ascii") + suffix
    return raw, dict(**decision, submitted_body_sha256=sha(body.encode("ascii")),
                     rendered_body_sha256=sha(rendered.encode("ascii")),
                     prefix_sha256=sha(prefix), suffix_sha256=sha(suffix),
                     source_sha256=sha(raw))


def _check_source_state(project, sources, accepted_stage_id=None):
    """Check all original bytes, exact registration and at most one parent."""
    spec, inventory = load_assets()
    actual = source_hashes(sources)
    original = inventory["projects"][project]["files"]
    expected_paths = set(original)
    if accepted_stage_id:
        stage = spec["stages"][accepted_stage_id]
        if stage["project"] != project or stage["stage"] != 1:
            raise ValueError("Only stage-one revisions are eligible parents")
        expected_paths.add(stage["path"])
        source_body(accepted_stage_id, sources.get(stage["path"]))
    if set(actual) != expected_paths:
        raise ValueError("Incomplete, extra or preexisting descendant source paths")
    registration = spec["registration"]
    for name, expected in original.items():
        raw = sources[name]
        if accepted_stage_id and project == "vest" and name == registration["path"]:
            suffix = registration["stage1_append"].encode()
            if not raw.endswith(suffix):
                raise ValueError("Parent module registration is not host-exact")
            raw = raw[:-len(suffix)]
        if sha(raw) != expected:
            raise ValueError("Protected upstream bytes changed: " + name)
    return actual


@dataclass(frozen=True)
class AcceptedParentBinding:
    """Trusted host pins, never model input and never constructed by this policy.

    The caller is responsible for selecting the actual accepted revision from
    its native-reviewed history. No signature or external authority is inferred.
    """
    project: str
    stage_id: str
    chain_id: str
    run_id: str
    evidence_kind: str
    revision_sha256: str
    receipt_sha256: str
    review_sha256: str
    profile_sha256: str
    required_units_sha256: str
    policy_sha256: str


def _check_identity(value):
    if not isinstance(value, str) or not IDENTITY.fullmatch(value):
        raise ValueError("Bounded host run/chain identity required")


def _require(record, expected):
    if (not isinstance(record, dict)
            or any(type(record.get(k)) is not type(v) or record.get(k) != v for k, v in expected.items())):
        raise ValueError("Missing, stale or mismatched parent evidence")


def validate_parent(child_stage_id, chain_id, sources, binding, artifacts, *, allow_synthetic=False):
    stage, _, inventory = stage_spec(child_stage_id)
    _check_identity(chain_id)
    if stage["stage"] != 2 or not isinstance(binding, AcceptedParentBinding):
        raise ValueError("Stage two requires an externally pinned accepted-parent binding")
    if binding.project != stage["project"] or binding.stage_id != stage["parent"] or binding.chain_id != chain_id:
        raise ValueError("Wrong parent project, stage or chain")
    _check_identity(binding.run_id)
    if binding.evidence_kind not in ("native-reviewed", "synthetic-offline"):
        raise ValueError("Unknown evidence kind")
    if binding.evidence_kind == "synthetic-offline" and not allow_synthetic:
        raise ValueError("Synthetic fixture is not native acceptance")
    for field in ("revision_sha256", "receipt_sha256", "review_sha256", "profile_sha256",
                  "required_units_sha256", "policy_sha256"):
        if not isinstance(getattr(binding, field), str) or not HEX.fullmatch(getattr(binding, field)):
            raise ValueError("Missing host evidence pin")
    if binding.policy_sha256 != policy_digest():
        raise ValueError("Parent was not accepted under this exact edit policy")
    sources_sha = _check_source_state(stage["project"], sources, stage["parent"])
    revision_sha = digest_map(sources_sha)
    if revision_sha != binding.revision_sha256:
        raise ValueError("Actual parent differs from accepted revision; no reference substitution")
    if not isinstance(artifacts, dict):
        raise ValueError("Pinned parent artifacts required")
    for name in ("accepted.json", "review.json", "profile.json"):
        expected = getattr(binding, {"accepted.json": "receipt_sha256", "review.json": "review_sha256",
                                     "profile.json": "profile_sha256"}[name])
        if name not in artifacts or not isinstance(artifacts[name], bytes) or sha(artifacts[name]) != expected:
            raise ValueError("Missing or changed pinned parent artifact: " + name)
    receipt, review, profile = (read_json(artifacts[name])
                                for name in ("accepted.json", "review.json", "profile.json"))
    common = dict(project=binding.project, stage_id=binding.stage_id, evidence_kind=binding.evidence_kind,
                  policy_sha256=binding.policy_sha256)
    required_units = profile.get("required_units") if isinstance(profile, dict) else None
    if (not isinstance(required_units, list) or not required_units
            or not all(isinstance(unit, str) and unit and len(unit) <= 4096 for unit in required_units)
            or len(set(required_units)) != len(required_units)
            or sha(canonical(required_units)) != binding.required_units_sha256):
        raise ValueError("Invalid or stale host-reviewed native inventory")
    new_units = profile.get("new_file_units")
    if (not isinstance(new_units, list) or not new_units
            or not all(isinstance(unit, str) for unit in new_units)
            or len(set(new_units)) != len(new_units) or not set(new_units) <= set(required_units)):
        raise ValueError("Parent addition is absent from the native inventory")
    for key in ("toolchain_sha256", "native_command_sha256", "warning_policy_sha256", "qualification_review_sha256"):
        if not isinstance(profile.get(key), str) or not HEX.fullmatch(profile[key]):
            raise ValueError("Missing qualification/toolchain/command/warning-policy identity")
    _require(profile, dict(**common, schema="repodisco-growth-native-parent-profile-v1",
                           scope="entire-qualified-project-plus-stage-one",
                           upstream_commit=inventory["projects"][binding.project]["commit"],
                           source_sha256=sources_sha,
                           inventory_origin=("reviewed-native-reference" if binding.evidence_kind == "native-reviewed"
                                             else "synthetic-fixture-not-native")))
    expected = dict(**common, chain_id=chain_id, run_id=binding.run_id,
                    revision_sha256=revision_sha, profile_sha256=binding.profile_sha256,
                    required_units_sha256=binding.required_units_sha256)
    _require(receipt, dict(**expected, schema="repodisco-growth-accepted-parent-v1", status="accepted",
                           source_sha256=sources_sha, review_sha256=binding.review_sha256,
                           predecessor_revision_sha256=digest_map(inventory["projects"][binding.project]["files"])))
    _require(review, dict(**expected, schema="repodisco-growth-parent-review-v1",
                          source_before_sha256=sources_sha, source_after_sha256=sources_sha,
                          native_exit_code=0, timed_out=False, frontend_errors=0, proof_failures=0,
                          coverage_complete=True, all_sources_registered=True, source_integrity_passed=True,
                          warning_policy_sha256=profile["warning_policy_sha256"],
                          warning_gate_passed=True, unreviewed_warnings=0))
    observations = review.get("named_outcomes")
    if (not isinstance(observations, list) or len(observations) != len(required_units)
            or any(not isinstance(item, dict) or set(item) != {"unit", "status"} for item in observations)
            or any(not isinstance(item["unit"], str) for item in observations)
            or {item["unit"] for item in observations} != set(required_units)
            or any(item["status"] != "Passed" for item in observations)):
        raise ValueError("Every required parent unit must have one actual passing observation")
    raw_pins, roles = review.get("raw_sha256"), review.get("raw_roles")
    digest_map(raw_pins)
    if (not isinstance(roles, dict) or set(roles) != {"stdout", "stderr", "native_units", "execution"}
            or not all(isinstance(name, str) for name in roles.values())
            or len(set(roles.values())) != 4 or not set(roles.values()) <= set(raw_pins)):
        raise ValueError("Missing native raw evidence roles")
    if set(raw_pins) & {"accepted.json", "review.json", "profile.json"}:
        raise ValueError("Raw evidence cannot substitute for reviewed records")
    if set(artifacts) != set(raw_pins) | {"accepted.json", "review.json", "profile.json"}:
        raise ValueError("Exact complete parent evidence artifact set required")
    for name, expected_sha in raw_pins.items():
        if not isinstance(artifacts[name], bytes) or sha(artifacts[name]) != expected_sha:
            raise ValueError("Missing or altered native raw evidence")
    return dict(binding_sha256=sha(canonical(asdict(binding))), parent_revision_sha256=revision_sha,
                parent_run_id=binding.run_id, evidence_kind=binding.evidence_kind,
                host_pins_validated=True, authenticity_established_by_policy=False,
                native_verification_performed=False, required_unit_count=len(required_units))


def reconstruct(stage_id, body, parent_sources, *, chain_id, parent_binding=None,
                parent_artifacts=None, allow_synthetic=False):
    """Return an unverified candidate byte map and audit; never changes inputs."""
    stage, spec, _ = stage_spec(stage_id)
    _check_identity(chain_id)
    if stage["stage"] == 1:
        if parent_binding is not None or parent_artifacts is not None:
            raise ValueError("Stage one begins from the pinned qualified upstream")
        before = _check_source_state(stage["project"], parent_sources)
        parent_audit = None
    else:
        parent_audit = validate_parent(stage_id, chain_id, parent_sources, parent_binding,
                                       parent_artifacts, allow_synthetic=allow_synthetic)
        before = source_hashes(parent_sources)
    new_source, body_audit = render_source(stage_id, body)
    candidate = dict(parent_sources)
    if stage["path"] in candidate:
        raise ValueError("Current-stage file already exists")
    candidate[stage["path"]] = new_source
    registration_audit = None
    if stage["project"] == "vest":
        registration = spec["registration"]
        name = registration["path"]
        candidate[name] += registration[f"stage{stage['stage']}_append"].encode()
        registration_audit = dict(path=name, before_sha256=before[name], after_sha256=sha(candidate[name]),
                                  host_owned=True)
    after = source_hashes(candidate)
    return candidate, dict(policy=VERSION, policy_sha256=policy_digest(), stage_id=stage_id,
                           chain_id=chain_id, new_path=stage["path"], body=body_audit,
                           before_revision_sha256=digest_map(before),
                           candidate_revision_sha256=digest_map(after),
                           candidate_source_sha256=after, host_registration=registration_audit,
                           accepted_parent=parent_audit, candidate_unverified=True,
                           native_acceptance_performed=False)


def audit_candidate(stage_id, candidate_sources, parent_sources, **kwargs):
    """Recheck all candidate bytes immediately before the host verifier gate."""
    stage, _, _ = stage_spec(stage_id)
    source_hashes(candidate_sources)
    if stage["path"] not in candidate_sources:
        raise ValueError("Current-stage source missing")
    body = source_body(stage_id, candidate_sources[stage["path"]])
    expected, audit = reconstruct(stage_id, body, parent_sources, **kwargs)
    if candidate_sources != expected:
        raise ValueError("Candidate changed protected sources, parent or registration")
    return audit


def parse_response(raw, stage_id, parent_sources, **kwargs):
    payload, envelope = extract_json(raw)
    obj = read_json(payload.encode())
    if not isinstance(obj, dict) or set(obj) != {"replacement"} or not isinstance(obj["replacement"], str):
        raise ValueError("Exactly one replacement body string required")
    candidate, audit = reconstruct(stage_id, obj["replacement"], parent_sources, **kwargs)
    return candidate, dict(**audit, envelope=envelope)
