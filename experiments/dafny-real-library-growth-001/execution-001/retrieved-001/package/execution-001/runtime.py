"""Pure runtime validation and exclusive evidence I/O for one new bounded scope."""
from dataclasses import dataclass
import importlib.util
import json
import math
import os
from pathlib import Path
import re
import sys

HERE = Path(__file__).resolve().parent
PACKAGE = HERE.parent
COMMON = PACKAGE / "common"
sys.path.insert(0, str(COMMON))
import guard
import review_native as native
from bounded_requests import durable_json
from extract_response import extract_json

MAX_CALLS = 12
PILOT_SLOTS = 4
SCOPE_SCHEMA = "dafny-library-growth-scope-v1"
AUTH_SCHEMA = "dafny-library-execution-authorization-v1"


def require(ok, message):
    if not ok:
        raise native.EvidenceError(message)


def canonical(value):
    return native.canonical(value)


def sha(data):
    return native.sha(data)


def json_copy(value):
    return json.loads(canonical(value))


def save(path, value):
    path = Path(path)
    require(not path.exists() and not path.with_suffix(".tmp").exists(), "Evidence path already exists")
    path.parent.mkdir(parents=True, exist_ok=True)
    durable_json(path, value)


def save_bytes(path, value):
    require(isinstance(value, bytes), "Exact bytes required")
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("xb") as stream:
        stream.write(value)
        stream.flush()
        os.fsync(stream.fileno())


def read_json(path):
    def unique(items):
        result = {}
        for key, value in items:
            require(key not in result, "Duplicate JSON object key")
            result[key] = value
        return result
    return json.loads(Path(path).read_text(encoding="utf-8"), object_pairs_hook=unique,
                      parse_constant=lambda _: (_ for _ in ()).throw(ValueError("Nonfinite JSON")))


def checked_path(root, name):
    require(native.safe_path(name), "Unsafe package-relative path")
    root = Path(root).resolve()
    value = root / name
    require(value.resolve().is_relative_to(root), "Package path escaped")
    current = value
    while current != root:
        require(not current.is_symlink(), "Symlinks are not runtime inputs")
        current = current.parent
    require(value.is_file(), "Missing regular input")
    return value


def file_snapshot(folder):
    folder = Path(folder)
    result = {}
    for path in sorted(folder.rglob("*")):
        require(not path.is_symlink(), "Evidence symlink prohibited")
        if path.is_file():
            result[path.relative_to(folder).as_posix()] = sha(path.read_bytes())
    return result


def source_files(folder):
    folder = Path(folder)
    result = {}
    for path in sorted(folder.rglob("*.dfy")):
        require(path.is_file() and not path.is_symlink(), "Nonregular candidate source")
        result[path.relative_to(folder).as_posix()] = path.read_bytes()
    native.check_sources(result)
    return result


def save_sources(folder, sources):
    native.check_sources(sources)
    for name, data in sources.items():
        save_bytes(Path(folder) / name, data)


def validate_scope(scope):
    require(scope.get("schema") == SCOPE_SCHEMA and scope.get("max_calls") == MAX_CALLS,
            "Exactly the frozen twelve-slot ceiling is required")
    require(scope.get("pilot_slots") == PILOT_SLOTS, "Exactly four pilot slots required")
    require(isinstance(scope.get("batch_id"), str) and scope["batch_id"], "Missing batch identity")
    settings = scope.get("settings")
    require(isinstance(settings, dict) and set(settings) == {"model_id", "region", "inference_config"},
            "Frozen provider settings required")
    require(isinstance(settings["model_id"], str) and settings["model_id"]
            and isinstance(settings["region"], str) and settings["region"], "Missing model/region")
    require(isinstance(settings["inference_config"], dict), "Missing inference settings")
    projects = scope.get("projects")
    require(isinstance(projects, dict) and set(projects) == {"stdlib", "aws"}, "Two frozen projects required")
    slots = scope.get("slots")
    require(isinstance(slots, list) and len(slots) == MAX_CALLS, "Twelve explicit slots required")
    require([s.get("project") for s in slots[:4]] == ["stdlib", "aws", "stdlib", "aws"]
            and [s.get("stage") for s in slots[:4]] == [1, 1, 2, 2], "Pilot order differs")
    require([s.get("project") for s in slots[4:8]] == ["stdlib", "aws", "stdlib", "aws"]
            and [s.get("project") for s in slots[8:]] == ["aws", "stdlib", "aws", "stdlib"]
            and [s.get("stage") for s in slots[4:]] == [1, 1, 2, 2, 1, 1, 2, 2],
            "Expansion counterbalance differs")
    seen, chains = set(), {}
    for index, slot in enumerate(slots):
        require(set(slot) >= {"id", "project", "chain_id", "stage", "cohort"}, "Slot identity missing")
        require(native.safe_path(slot["id"]) and "/" not in slot["id"] and slot["id"] not in seen,
                "Unsafe/duplicate slot ID")
        seen.add(slot["id"])
        require(slot["project"] in projects and type(slot["stage"]) is int and slot["stage"] in (1, 2),
                "Slot stage/project differs")
        require(slot["cohort"] == ("pilot" if index < PILOT_SLOTS else "expansion"), "Cohort boundary differs")
        require(isinstance(slot["chain_id"], str) and slot["chain_id"], "Missing lineage")
        key = (slot["project"], slot["chain_id"])
        history = chains.setdefault(key, [])
        require(history == ([] if slot["stage"] == 1 else [1]), "Duplicate/misordered lineage stage")
        history.append(slot["stage"])
    require(len(chains) == 6 and all(x == [1, 2] for x in chains.values()), "Six complete declared lineages required")
    require(all(sum(p == project for p, _ in chains) == 3 for project in projects),
            "Three lineages per project required")
    pilot_chains = {(s["project"], s["chain_id"]) for s in slots[:4]}
    require(len(pilot_chains) == 2 and not any((s["project"], s["chain_id"]) in pilot_chains for s in slots[4:]),
            "Expansion must use fresh lineages")
    return json_copy(scope)


def validate_authorization(auth, scope_hash, runtime_hash, now):
    require(auth.get("schema") == AUTH_SCHEMA and auth.get("operator") == "Sophie Zeng",
            "Fresh human authorization required")
    require(auth.get("scope_sha256") == scope_hash
            and auth.get("runtime_manifest_sha256") == runtime_hash, "Authorization freeze binding differs")
    require(auth.get("max_new_calls") == MAX_CALLS and auth.get("total_session_ceiling") == 100,
            "Authorization budget differs")
    require(auth.get("no_retry") is True and auth.get("no_reassignment") is True
            and auth.get("no_resume") is True, "Terminal/no-reassignment policy required")
    require(all(isinstance(auth.get(k), str) and auth[k] for k in
                ("allocation_id", "budget_session_id", "human_approval_basis")), "Missing allocation/human basis")
    created, expires = auth.get("created_at_epoch"), auth.get("expires_at_epoch")
    require(type(created) in (int, float) and type(expires) in (int, float)
            and math.isfinite(created) and math.isfinite(expires)
            and created <= now < expires <= created + 86400, "Authorization expired or not fresh")
    return expires


def validate_payload(payload, settings):
    require(isinstance(payload, dict)
            and set(payload) == {"modelId", "system", "messages", "inferenceConfig"},
            "Frozen Converse payload shape differs")
    require(payload["modelId"] == settings["model_id"]
            and payload["inferenceConfig"] == settings["inference_config"], "Payload settings differ")
    require(isinstance(payload["system"], list) and isinstance(payload["messages"], list)
            and len(payload["messages"]) == 1 and payload["messages"][0].get("role") == "user",
            "Fresh single-user context required")
    canonical(payload)


def parse_body_receipt(text):
    require(isinstance(text, str), "Provider text missing")
    def unique(items):
        obj = {}
        for key, value in items:
            require(key not in obj, "Duplicate response JSON key")
            obj[key] = value
        return obj
    try:
        stripped, envelope = extract_json(text)
        obj = json.loads(stripped, object_pairs_hook=unique,
                         parse_constant=lambda _: (_ for _ in ()).throw(ValueError("Nonfinite JSON")))
    except (ValueError, TypeError) as error:
        raise native.EvidenceError("Response is not one complete JSON object") from error
    require(type(obj) is dict and set(obj) == {"body"} and isinstance(obj["body"], str),
            "Response must be exactly {body:string}")
    return obj["body"], envelope


def parse_body(text):
    return parse_body_receipt(text)[0]


@dataclass
class Stage:
    edit_profile: dict
    native_profile: dict
    base_sources: dict
    adapter: dict


def materialize_profile(template, sources):
    result = json_copy(template)
    for item in result["unlogged_definitions"]:
        require(item["file"] in sources, "Unlogged definition source absent")
        item["source_sha256"] = sha(sources[item["file"]])
    return result


def validate_stage(stage, project, number):
    guard._profile(stage.edit_profile)
    require(stage.edit_profile["project"] == project and stage.edit_profile["stage"] == number,
            "Edit stage identity differs")
    require(stage.native_profile["project"] == project and stage.native_profile["stage"] == number
            and stage.native_profile["stage_id"] == stage.edit_profile["stage_id"]
            and stage.native_profile["inventory_status"] == "qualified", "Native profile is not qualified for stage")
    require(native.check_sources(stage.base_sources) == stage.edit_profile["base_source_sha256"],
            "Pinned stage base differs")
    require(stage.native_profile.get("synthetic") is not True, "Live profile cannot be synthetic")
    for key in ("ineligible_parent_runs", "ineligible_parent_raw_fingerprints"):
        require(isinstance(stage.native_profile.get(key), list), "Explicit analyst-exclusion inventory required")
    return stage


def validate_runtime(package, freeze, expected_sha):
    require(sha(Path(freeze).read_bytes()) == expected_sha, "Runtime manifest digest differs")
    value = read_json(freeze)
    require(value.get("schema") == "dafny-library-execution-runtime-v1", "Unknown runtime manifest")
    for name, digest in value["files"].items():
        require(sha(checked_path(package, name).read_bytes()) == digest, "Frozen runtime/input drift: " + name)
    return value


def load_stages(package, scope):
    result = {}
    for project, definition in scope["projects"].items():
        stages = definition["stages"]
        require(set(stages) == {"1", "2"}, "Both stage definitions required")
        for number, spec in stages.items():
            source_map = {}
            for name, pin in spec["base_sources"].items():
                require(native.safe_path(name) and name.endswith(".dfy"), "Bad source name")
                data = checked_path(package, pin["path"]).read_bytes()
                require(sha(data) == pin["sha256"], "Base source drift")
                source_map[name] = data
            stage = Stage(read_json(checked_path(package, spec["edit_profile"])),
                          read_json(checked_path(package, spec["native_profile"])),
                          source_map, json_copy(spec["native_adapter"]))
            result[(project, int(number))] = validate_stage(stage, project, int(number))
    return result


def load_renderer(package, relative_path):
    path = checked_path(package, relative_path)
    module_spec = importlib.util.spec_from_file_location("frozen_library_prompt_renderer", path)
    module = importlib.util.module_from_spec(module_spec)
    module_spec.loader.exec_module(module)
    return module

