"""Protected-body reconstruction for declarative Dafny extension stages.

This is a lexical edit boundary, not a Dafny parser or proof checker. Profiles,
EvidencePins and receipt pins are supplied by a reviewed host, never the model.
"""
from dataclasses import dataclass
import re

from review_native import (EvidenceError, EvidencePins, HEX, canonical, check_sources,
                           hashes, require, review, safe_path, sha)

SCHEMA = "dafny-library-edit-profile-v1"
RECEIPT_SCHEMA = "dafny-library-parent-receipt-v1"
MAX_BYTES = 65536
MAX_TOKENS = 32768
MAX_DEPTH = 128
FORBIDDEN = frozenset({
    "include", "import", "export", "module", "class", "trait", "datatype",
    "codatatype", "newtype", "type", "method", "function", "lemma", "predicate",
    "iterator", "constructor", "refines", "abstract", "assume", "axiom", "admit",
    "extern", "external", "external_body", "expect", "halt", "opaque",
})
IDENTIFIER = re.compile(r"[A-Za-z_][A-Za-z0-9_']*")


@dataclass(frozen=True)
class ParentEvidence:
    """Externally trusted host inputs, not an acceptance receipt issuer."""
    native_profile: dict
    record: dict
    raw: dict[str, bytes]
    pins: EvidencePins
    receipt: dict
    receipt_sha256: str


def body_tokens(body):
    """Skip balanced comments/literals and retain structural tokens exactly.

    Ordinary loops, invariants, calc blocks, local variables, constructors and
    function expressions are admitted. Unknown calls/types are left to Dafny.
    """
    require(isinstance(body, str), "Body must be text")
    require(len(body.encode("utf-8")) <= MAX_BYTES, "Body exceeds byte bound")
    require(all(c in "\n\r\t" or 32 <= ord(c) < 127 for c in body),
            "Body syntax currently requires ASCII")
    i, result = 0, []
    while i < len(body):
        if body[i].isspace():
            i += 1
            continue
        if body.startswith("//", i):
            end = body.find("\n", i)
            i = len(body) if end < 0 else end + 1
            continue
        if body.startswith("/*", i):
            i += 2
            depth = 1
            while i < len(body) and depth:
                if body.startswith("/*", i):
                    depth += 1
                    require(depth <= MAX_DEPTH, "Comment nesting exceeds bound")
                    i += 2
                elif body.startswith("*/", i):
                    depth -= 1
                    i += 2
                else:
                    i += 1
            require(depth == 0, "Unclosed block comment")
            continue
        if body.startswith('@"', i):
            start = i
            i += 2
            closed = False
            while i < len(body):
                if body.startswith('""', i):
                    i += 2
                elif body[i] == '"':
                    i += 1
                    closed = True
                    break
                else:
                    i += 1
            require(closed, "Unclosed verbatim string")
            result.append(("literal", body[start:i]))
        elif body[i] in {'"', "'"}:
            start, quote = i, body[i]
            i += 1
            closed = False
            while i < len(body):
                require(body[i] not in "\r\n", "Newline in ordinary literal")
                if body[i] == "\\":
                    require(i + 1 < len(body), "Unclosed literal escape")
                    i += 2
                elif body[i] == quote:
                    i += 1
                    closed = True
                    break
                else:
                    i += 1
            require(closed, "Unclosed literal")
            result.append(("literal", body[start:i]))
        else:
            match = IDENTIFIER.match(body, i)
            if match:
                result.append(("identifier", match.group()))
                i = match.end()
            else:
                result.append(("punctuation", body[i]))
                i += 1
        require(len(result) <= MAX_TOKENS, "Body exceeds token bound")
    return result


def check_body(body, kind, forbidden_identifiers=()):
    require(kind in {"method", "function", "lemma", "predicate"}, "Unknown host body kind")
    tokens = body_tokens(body)
    require(isinstance(forbidden_identifiers, (list, tuple))
            and all(isinstance(value, str) and IDENTIFIER.fullmatch(value)
                    for value in forbidden_identifiers), "Forbidden names must be exact identifier tokens")
    forbidden_names = set(forbidden_identifiers)
    require(kind not in {"function", "predicate"} or bool(tokens), "Expression body must be nonempty")
    stack = []
    matches = {"}": "{", ")": "(", "]": "["}
    for index, (token_kind, value) in enumerate(tokens):
        if token_kind == "literal":
            continue
        require(token_kind != "identifier" or value not in FORBIDDEN,
                "Declaration/trust keyword is outside editable scope: " + value)
        require(token_kind != "identifier" or value not in forbidden_names,
                "Host-forbidden identifier: " + value)
        following = tokens[index + 1][1] if index + 1 < len(tokens) else None
        require(not (value == "{" and following == ":"), "Attributes are not allowed in editable bodies")
        require(not (value == "decreases" and following == "*"), "Wildcard termination bypass prohibited")
        require(not (value == "." and tokens[index:index + 3] ==
                     [("punctuation", ".")] * 3), "Ellipsis/body omission prohibited")
        if value in "{([":
            stack.append(value)
            require(len(stack) <= MAX_DEPTH, "Body nesting exceeds bound")
        elif value in matches:
            require(bool(stack) and stack.pop() == matches[value], "Body escapes/mismatches host scope")
    require(not stack, "Unclosed body delimiter")
    return dict(token_count=len(tokens), body_sha256=sha(body.encode("utf-8")))


def _profile(profile):
    require(isinstance(profile, dict) and profile.get("schema") == SCHEMA, "Unsupported edit profile")
    require(isinstance(profile.get("project"), str) and profile["project"]
            and type(profile.get("stage")) is int and profile["stage"] in (1, 2)
            and isinstance(profile.get("stage_id"), str) and profile["stage_id"],
            "Missing edit identity")
    base = profile.get("base_source_sha256")
    require(isinstance(base, dict) and base and all(safe_path(name) and name.endswith(".dfy")
            and isinstance(digest, str) and HEX.fullmatch(digest) for name, digest in base.items()),
            "Full base source pins required")
    addition = profile.get("addition")
    require(isinstance(addition, dict) and safe_path(addition.get("path"))
            and addition["path"].endswith(".dfy") and addition["path"] not in base,
            "New file must have a host-owned fresh path")
    template = addition.get("template_utf8")
    begin, end = addition.get("begin_marker"), addition.get("end_marker")
    require(isinstance(template, str) and isinstance(begin, str) and begin
            and isinstance(end, str) and end and begin != end
            and template.count(begin) == 1 and template.count(end) == 1,
            "Exactly one host body boundary required")
    start, stop = template.index(begin) + len(begin), template.index(end)
    require(start <= stop and not template[start:stop].strip(), "Host template body must be empty")
    require(begin.endswith("\n") and (stop == 0 or template[stop - 1] == "\n"),
            "Body boundary must end at a line boundary")
    registrations = profile.get("registrations")
    require(isinstance(registrations, dict), "Exact host registration map required")
    for name, value in registrations.items():
        require(safe_path(name) and name.endswith(".dfy") and name != addition["path"]
                and isinstance(value, dict) and isinstance(value.get("content_utf8"), str)
                and value.get("before_sha256") == base.get(name), "Registration/base identity differs")
    parent = profile.get("parent_requirement")
    require((profile["stage"] == 1 and parent is None)
            or (profile["stage"] == 2 and isinstance(parent, dict)), "Stage/parent rule differs")
    if parent is not None:
        require(isinstance(parent.get("stage_id"), str) and parent["stage_id"]
                and safe_path(parent.get("addition_path"))
                and parent["addition_path"].endswith(".dfy")
                and parent["addition_path"] not in base and parent["addition_path"] != addition["path"]
                and parent["addition_path"] not in registrations
                and isinstance(parent.get("guard_profile_sha256"), str)
                and HEX.fullmatch(parent["guard_profile_sha256"]), "Invalid accepted-parent rule")
    inputs = profile.get("verification_inputs")
    require(registrations or inputs is not None, "Host registration or complete explicit inputs required")
    if inputs is not None:
        final_names = set(base) | {addition["path"]} | set(registrations)
        if parent is not None:
            final_names.add(parent["addition_path"])
        require(isinstance(inputs, list) and all(isinstance(name, str) for name in inputs)
                and len(inputs) == len(set(inputs)) and set(inputs) == final_names,
                "Explicit verification inputs must cover exactly the final source map")
    return template[:start], template[stop:]


def render_body(profile, body):
    """Render a guarded control/draft. This does not authorize a parent or run."""
    prefix, suffix = _profile(profile)
    addition = profile["addition"]
    require(addition["begin_marker"] not in body and addition["end_marker"] not in body,
            "Body may not introduce host markers")
    audit = check_body(body, addition["kind"], profile.get("forbidden_identifiers", []))
    separator = "" if not body or body.endswith("\n") else "\n"
    raw = (prefix + body + separator + suffix).encode("utf-8")
    return raw, audit


def validate_parent(profile, parent_sources, chain_id, parent, *, allow_synthetic=False):
    require(isinstance(parent, ParentEvidence), "Stage two needs trusted-host ParentEvidence")
    require(isinstance(chain_id, str) and chain_id, "Actual chain identity required")
    receipt = parent.receipt
    require(isinstance(parent.receipt_sha256, str) and HEX.fullmatch(parent.receipt_sha256)
            and sha(canonical(receipt)) == parent.receipt_sha256, "Stale/unpinned parent receipt")
    requirement = profile["parent_requirement"]
    result = review(parent.native_profile, parent_sources, parent.record, parent.raw,
                    parent.pins, allow_synthetic=allow_synthetic)
    synthetic = result["synthetic"]
    origin = "synthetic_offline" if synthetic and allow_synthetic else "model_candidate"
    require(result["origin"] == origin and result["qualified_success"],
            "Parent must have a qualified model-origin native result")
    require(result["project"] == profile["project"] and result["stage"] == 1
            and result["stage_id"] == requirement["stage_id"], "Wrong parent project/stage")
    denied_runs = parent.native_profile.get("ineligible_parent_runs", [])
    denied_raw = parent.native_profile.get("ineligible_parent_raw_fingerprints", [])
    require(isinstance(denied_runs, list) and isinstance(denied_raw, list), "Invalid control provenance policy")
    require(result["run_id"] not in denied_runs
            and result["raw_fingerprint_sha256"] not in denied_raw, "Known analyst observation cannot be relabeled")
    required = dict(schema=RECEIPT_SCHEMA, project=profile["project"], stage=1,
                    stage_id=requirement["stage_id"], chain_id=chain_id, origin=origin,
                    guard_profile_sha256=requirement["guard_profile_sha256"],
                    source_revision_sha256=result["source_revision_sha256"],
                    native_profile_sha256=result["profile_sha256"],
                    native_record_sha256=result["record_sha256"],
                    native_run_id=result["run_id"],
                    native_raw_fingerprint_sha256=result["raw_fingerprint_sha256"],
                    accepted=True)
    require(all(receipt.get(key) == value for key, value in required.items()),
            "Parent receipt/source/native/chain binding differs")
    require(isinstance(receipt.get("request_id"), str) and receipt["request_id"]
            and isinstance(receipt.get("response_sha256"), str) and HEX.fullmatch(receipt["response_sha256"]),
            "Host model request/response provenance is required")
    return dict(native_review=result, receipt_sha256=parent.receipt_sha256,
                source_revision_sha256=result["source_revision_sha256"], synthetic=synthetic,
                acceptance_issued=False)


def reconstruct(profile, body, parent_sources, chain_id, *, parent=None, allow_synthetic=False):
    """Create an isolated candidate map, preserving all supplied parent bytes."""
    _profile(profile)
    observed = check_sources(parent_sources)
    required = profile["parent_requirement"]
    parent_audit = None
    if profile["stage"] == 1:
        require(parent is None and observed == profile["base_source_sha256"], "Stage-one source identity differs")
    else:
        path = required["addition_path"]
        require(path in observed and {name: value for name, value in observed.items() if name != path}
                == profile["base_source_sha256"], "Stage-two immutable parent bytes differ")
        parent_audit = validate_parent(profile, parent_sources, chain_id, parent,
                                       allow_synthetic=allow_synthetic)
    require(isinstance(chain_id, str) and chain_id, "Chain identity required")
    addition = profile["addition"]["path"]
    require(addition not in parent_sources, "Current stage file already exists")
    candidate = dict(parent_sources)
    raw, body_audit = render_body(profile, body)
    candidate[addition] = raw
    for path, registration in profile["registrations"].items():
        require(observed.get(path) == registration["before_sha256"], "Stale registration parent")
        candidate[path] = registration["content_utf8"].encode("utf-8")
    candidate_hashes = check_sources(candidate)
    if profile.get("verification_inputs") is not None:
        require(set(profile["verification_inputs"]) == set(candidate_hashes), "Candidate/explicit inputs differ")
    immutable = set(parent_sources) - set(profile["registrations"])
    require(all(candidate[path] == parent_sources[path] for path in immutable), "Candidate mutated immutable parent")
    return candidate, dict(schema="dafny-library-edit-review-v1", project=profile["project"],
                           stage=profile["stage"], stage_id=profile["stage_id"], chain_id=chain_id,
                           guard_profile_sha256=sha(canonical(profile)),
                           parent_source_revision_sha256=sha(canonical(observed)),
                           source_revision_sha256=sha(canonical(candidate_hashes)),
                           verification_inputs=profile.get("verification_inputs"),
                           source_sha256=candidate_hashes, body=body_audit, parent=parent_audit,
                           synthetic=bool(parent_audit and parent_audit["synthetic"]),
                           acceptance_issued=False)
