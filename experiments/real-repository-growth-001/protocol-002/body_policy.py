"""Revised source/body policy; native_adapter supplies actual-parent evidence.

The host must supply pins from its reviewed native evidence gate. Self-consistent
JSON is not evidence authenticity. Nothing here creates an accepted revision.
"""
import hashlib
import json
from pathlib import Path, PurePosixPath
import re

from lexical.body_guard import tokens, syntax_context, sequence_update, assigned_roots
from lexical.extract_response import extract_json, unique, reject_constant

ROOT = Path(__file__).resolve().parent
VERSION = "sequential-real-repository-growth-policy-v2"
SPEC_SHA256 = "4b34cfc048db5626df8637af74d768741a677adfba8bd9938918355a77cce2c4"
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
        if sha((ROOT / "lexical" / name).read_bytes()) != expected:
            raise ValueError("Inherited parser drift")
    for name, expected in spec["native_parser_files"].items():
        if sha((ROOT / name).read_bytes()) != expected:
            raise ValueError("Pinned native parser drift")
    if sha((ROOT / "reference-inputs.json").read_bytes()) != spec["reference_inputs_sha256"]:
        raise ValueError("Reviewed reference input pins drift")
    for stage in spec["stages"].values():
        raw = (ROOT / "templates" / stage["template"]).read_bytes()
        if sha(raw) != stage["template_sha256"]:
            raise ValueError("Fixed template drift")
    return spec, read_json(inventory_raw)


def policy_digest():
    """Runtime identity the host must pin, independent of notes and test logs."""
    spec, _ = load_assets()
    files = {"body_policy.py": sha(Path(__file__).read_bytes()),
             "native_adapter.py": sha((ROOT / "native_adapter.py").read_bytes()),
             "policy-spec.json": SPEC_SHA256,
             "upstream-inventory.json": spec["upstream_inventory_sha256"],
             "reference-inputs.json": spec["reference_inputs_sha256"]}
    files.update(spec["native_parser_files"])
    files.update({"lexical/" + name: digest for name, digest in spec["inherited"].items()})
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


def check_workspace(project, stage, sources):
    """Source scope only. A passing byte audit is never native acceptance."""
    if project not in ("dafny-vmc", "vest") or type(stage) is not int or stage not in (0, 1, 2):
        raise ValueError("Known project and stage 0, 1 or 2 required")
    first, second = ("vmc-move", "vmc-pair") if project == "dafny-vmc" else ("vest-frame", "vest-batch")
    if stage < 2:
        return _check_source_state(project, sources, first if stage else None)
    second_spec, spec, _ = stage_spec(second)
    if second_spec["path"] not in sources:
        raise ValueError("Stage-two source is missing")
    source_body(second, sources[second_spec["path"]])
    parent = dict(sources)
    del parent[second_spec["path"]]
    if project == "vest":
        registration = spec["registration"]
        suffix = registration["stage2_append"].encode()
        if not parent.get(registration["path"], b"").endswith(suffix):
            raise ValueError("Stage-two module registration differs")
        parent[registration["path"]] = parent[registration["path"]][:-len(suffix)]
    _check_source_state(project, parent, first)
    return source_hashes(sources)


def reconstruct(stage_id, body, parent_sources, *, chain_id, parent_binding=None,
                parent_artifacts=None, allow_synthetic=False):
    """Reconstruct an unverified candidate; no acceptance or promotion."""
    stage, spec, _ = stage_spec(stage_id)
    if not isinstance(chain_id, str) or not IDENTITY.fullmatch(chain_id):
        raise ValueError("Bounded host chain identity required")
    if stage["stage"] == 1:
        if parent_binding is not None or parent_artifacts is not None:
            raise ValueError("Stage one starts at the qualified pinned upstream")
        before = check_workspace(stage["project"], 0, parent_sources)
        parent_audit = None
    else:
        from native_adapter import validate_accepted_parent
        parent_audit = validate_accepted_parent(stage_id, chain_id, parent_sources, parent_binding,
                                                parent_artifacts, allow_synthetic=allow_synthetic)
        before = check_workspace(stage["project"], 1, parent_sources)
    new_source, body_audit = render_source(stage_id, body)
    candidate = dict(parent_sources)
    if stage["path"] in candidate:
        raise ValueError("Current-stage source already exists")
    candidate[stage["path"]] = new_source
    registration_audit = None
    if stage["project"] == "vest":
        registration = spec["registration"]
        name = registration["path"]
        candidate[name] += registration[f"stage{stage['stage']}_append"].encode()
        registration_audit = dict(path=name, before_sha256=before[name], after_sha256=sha(candidate[name]),
                                  host_owned=True)
    after = check_workspace(stage["project"], stage["stage"], candidate)
    return candidate, dict(policy=VERSION, policy_sha256=policy_digest(), stage_id=stage_id,
                           chain_id=chain_id, new_path=stage["path"], body=body_audit,
                           before_revision_sha256=digest_map(before),
                           candidate_revision_sha256=digest_map(after),
                           candidate_source_sha256=after, host_registration=registration_audit,
                           accepted_parent=parent_audit, candidate_unverified=True,
                           native_acceptance_performed=False)


def audit_candidate(stage_id, candidate_sources, parent_sources, **kwargs):
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


