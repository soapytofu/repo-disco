"""Offline, source-bound two-method measurement; no verifier or provider calls.

Candidate admission is replayed with a separately pinned method-body policy.
Historical fixture replay is a different, exact-hash path and cannot admit an
old internal contract as a candidate for the fixed-target repair task.
"""
import base64
import csv
import hashlib
import importlib.util
import json
import math
from pathlib import Path, PurePosixPath
import re
import sys

sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parent
INPUTS_SHA = "ff50855a3ee7ffeaefc17bf2ddcbd23750587512a8ad3f7f161f5e4ddbde94d5"
GUARD_MANIFEST_SHA = "e20897012f83d95de1bc88e9d6b3c3d3eb75114dc7c2136dbe973a9ccfbdb87f"
GUARD_PROVENANCE_SHA = "c6fdae216ad20a7291391c64dbdf60c17cdbc4f956d0b5afe7c6de138872fe6a"
POLICY_ID = "internal-contract-method-bodies-v1-development"
TARGETS = {"Helper.Transfer", "Client.Target"}
FILES = {"All.dfy", "Kernel.dfy", "Helper.dfy", "Client.dfy"}
SUFFIX = b"  }\n}\n"


class MeasurementError(ValueError):
    """Evidence or protected-scope mismatch; never a model proof failure."""


def require(value, message):
    if not value:
        raise MeasurementError(message)


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False).encode()


def pairs(items):
    result = {}
    for name, value in items:
        require(name not in result, "Duplicate JSON key")
        result[name] = value
    return result


def load(path):
    def reject(value):
        raise MeasurementError("Nonstandard JSON number")
    return json.loads(Path(path).read_bytes(), object_pairs_hook=pairs, parse_constant=reject)


def safe(root, name):
    require(isinstance(name, str) and name and "\\" not in name, "Relative POSIX path required")
    rel = PurePosixPath(name)
    require(not rel.is_absolute() and all(p not in ("", ".", "..") for p in name.split("/")), "Unsafe path")
    path = Path(root)
    require(path.is_dir() and not path.is_symlink(), "Regular root required")
    for part in rel.parts:
        path /= part
        require(not path.is_symlink(), "Symlink forbidden")
    return path


def inventory(root):
    root = Path(root)
    require(root.is_dir() and not root.is_symlink(), "Regular directory required")
    result = {}
    for path in sorted(root.rglob("*")):
        require(not path.is_symlink() and (path.is_file() or path.is_dir()), "Nonregular artifact")
        if path.is_file():
            result[path.relative_to(root).as_posix()] = sha(path.read_bytes())
    return result


def source_hashes(files):
    require(isinstance(files, dict) and set(files) == FILES and all(isinstance(v, bytes) for v in files.values()),
            "Exact four-file byte workspace required")
    return {n: sha(b) for n, b in sorted(files.items())}


def sources(folder):
    return {p.name: p.read_bytes() for p in sorted(Path(folder).glob("*.dfy"))}


def module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    result = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(result)
    return result


def checked_inputs(root=ROOT):
    root = Path(root)
    require(sha((root / "inputs-manifest.json").read_bytes()) == INPUTS_SHA, "Measurement inputs manifest changed")
    pins = load(root / "inputs-manifest.json")
    require(isinstance(pins, dict) and pins, "Missing measurement pins")
    for name, digest in pins.items():
        require(isinstance(digest, str) and re.fullmatch(r"[0-9a-f]{64}", digest), "Invalid input digest")
        require(sha(safe(root, name).read_bytes()) == digest, "Pinned measurement input changed: " + name)
    return pins


def inherited(root=ROOT):
    checked_inputs(root)
    versioned = module("internal_contract_measurement_named_v2", Path(root) / "inherited/review_v2.py")
    adapter = versioned.Adapter()
    classifier = module("internal_contract_measurement_classifier", Path(root) / "inherited/verify.py")
    require(adapter.old.TARGETS == TARGETS, "Inherited target scope differs")
    return adapter, classifier


def fixed_source_scope(files, source_pins, task_id, version, adapter, root=ROOT):
    """Reuse the exact source checker with fixed task metadata, not caller headers."""
    require(source_hashes(files) == source_pins, "Trusted candidate/source hash mismatch")
    old_tasks = {x["task_id"]: x for x in load(Path(root) / "metadata/propagation-tasks.json")}
    require(task_id in old_tasks and version in ("old", "new"), "Unknown fixed source scope")
    task = old_tasks[task_id]
    reference = sources(Path(root) / "controls" / (task_id + "-reference") / "sources")
    prefix = {"Client.dfy": task["public_contract_prefix"].encode(),
              "Helper.dfy": task["internal_api_versions"][version]["header"].encode() + b"  {\n"}
    boundaries = {}
    for name, start in prefix.items():
        require(files[name].startswith(start) and files[name].endswith(SUFFIX), "Fixed method header or suffix changed")
        require(len(files[name]) >= len(start) + len(SUFFIX), "Invalid fixed body span")
        boundaries[name] = dict(start=len(start), end=len(files[name]) - len(SUFFIX),
            protected_sha256=sha(start + b"<BODY>\n" + SUFFIX))
    case = dict(task_id=task_id, source_sha256=source_pins, internal_api_version=version,
        public_contract_sha256=task["public_contract_sha256"], body_boundaries=boundaries)
    try:
        declarations = adapter.source_scope(files, task, case, reference)
    except (ValueError, KeyError, TypeError) as error:
        raise MeasurementError("Protected source scope rejected: " + str(error)) from error
    return declarations


def validate_raw(record, raw_files, source_pins, classifier):
    """Same byte/base64/hash rules as the pinned reviewer, on an in-memory map."""
    require(isinstance(record, dict) and isinstance(raw_files, dict), "Record/raw maps required")
    required = {"command", "exit_code", "attempts", "model_calls", "source_sha256", "timed_out", "execution_error",
        "elapsed_seconds", "stdout", "stderr", "stdout_base64", "stderr_base64", "stdout_sha256", "stderr_sha256",
        "csv", "csv_base64", "csv_sha256"}
    require(required <= set(record), "Missing verifier evidence fields")
    require(record["command"] == classifier.COMMAND and type(record["attempts"]) is int and record["attempts"] == 1
            and type(record["model_calls"]) is int and record["model_calls"] == 0, "Verifier command or attempt provenance differs")
    require(record["source_sha256"] == source_pins, "Verifier source binding differs")
    require(record["exit_code"] is None or type(record["exit_code"]) is int, "Invalid verifier exit code")
    require(type(record.get("timed_out")) is bool, "Missing timeout evidence")
    require(record.get("execution_error") is None or isinstance(record["execution_error"], str), "Invalid execution error")
    require(type(record.get("elapsed_seconds")) in (int, float) and math.isfinite(record["elapsed_seconds"])
            and record["elapsed_seconds"] >= 0, "Invalid elapsed time")
    expected = {}
    try:
        for stream in ("stdout", "stderr"):
            require(isinstance(record[stream], str) and isinstance(record[stream + "_base64"], str), "Invalid raw stream encoding")
            raw = base64.b64decode(record[stream + "_base64"], validate=True)
            require(sha(raw) == record[stream + "_sha256"] and raw.decode("utf-8", errors="replace") == record[stream],
                    "Raw stream/base64/hash mismatch")
            expected[stream + ".txt"] = raw
        require(isinstance(record["csv"], dict) and set(record["csv"]) == set(record["csv_base64"]) == set(record["csv_sha256"]),
                "CSV inventory mismatch")
        for name in record["csv"]:
            require(isinstance(name, str) and name and "\\" not in name and not PurePosixPath(name).is_absolute()
                    and all(p not in ("", ".", "..") for p in name.split("/")) and name.endswith(".csv"), "Unsafe CSV path")
            require(isinstance(record["csv"][name], str) and isinstance(record["csv_base64"][name], str), "Invalid CSV encoding")
            raw = base64.b64decode(record["csv_base64"][name], validate=True)
            require(sha(raw) == record["csv_sha256"][name] and raw.decode("utf-8", errors="replace") == record["csv"][name],
                    "CSV/base64/hash mismatch")
            expected["csv/" + name] = raw
    except (ValueError, TypeError) as error:
        if isinstance(error, MeasurementError):
            raise
        raise MeasurementError("Malformed raw encoding") from error
    require(raw_files == expected and all(isinstance(v, bytes) for v in raw_files.values()), "Raw archive bytes or inventory differ")
    return {name: sha(raw) for name, raw in sorted(expected.items())}


def named_measurement(record, declarations, adapter):
    try:
        named = adapter.named_units(record["csv"], declarations)
    except (ValueError, csv.Error, KeyError, TypeError) as error:
        raise MeasurementError("Named verification evidence rejected: " + str(error)) from error
    expected = {symbol: ["correctness"] if symbol in TARGETS else ["well-formedness"]
                for symbol in declarations if symbol not in {x["symbol"] for x in named["unlogged_definitions"]}}
    require(named["observed_unit_kinds"] == expected, "Unknown or missing verification unit kind")
    named["logged_provider_units_verified"] = named.pop("providers_verified")
    named["provider_observation_complete"] = not named["unlogged_definitions"]
    return named


def interpret(record, declarations, adapter, classifier):
    """The pinned classifier defines categories; narrow consistency checks gate scoring."""
    coarse = classifier.classify(record)
    details = classifier.diagnostic_details(record)
    text = record["stdout"] + "\n" + record["stderr"]
    require("actual" not in record or record["actual"] == coarse, "Stored verifier category differs")
    require("diagnostics" not in record or record["diagnostics"] == json.loads(json.dumps(details)), "Stored diagnostic details differ")
    labels = {"success": "VERIFIED", "proof_failure": "PROOF_FAILURE", "termination_failure": "TERMINATION_FAILURE",
        "proof_failure_with_warnings": "PROOF_FAILURE_WITH_WARNINGS", "warning_only": "WARNING_ONLY",
        "timeout": "TIMEOUT", "execution_error": "VERIFIER_EXECUTION_ERROR", "resolution_failure": "RESOLUTION_OR_TYPE_FAILURE"}
    proof_level = coarse in ("success", "proof_failure", "termination_failure", "proof_failure_with_warnings", "warning_only")
    if coarse == "warning_or_other":
        warning_exit = record["exit_code"] == 2 and len(details["summaries"]) == 1 and details["summaries"][0][0] > 0 \
            and details["summaries"][0][1] == 0 and not details["error_lines"] and details["warnings"] > 0 \
            and "--allow-warnings is false" in text
        require(warning_exit, "Unclassified warning/exit evidence")
        outcome, proof_level = "WARNING_ONLY", True
    elif coarse == "frontend_failure":
        require(record["exit_code"] == 2 and details["error_lines"], "Incoherent frontend exit")
        parse = re.search(r"\bparse errors? detected\b", text, re.I) is not None
        typing = re.search(r"\bresolution/type errors? detected\b", text, re.I) is not None
        require(not (parse and typing), "Ambiguous frontend footer categories")
        outcome = "PARSE_FAILURE" if parse else "RESOLUTION_OR_TYPE_FAILURE" if typing else "FRONTEND_FAILURE"
    else:
        require(coarse in labels, "Unclassified verifier output")
        outcome = labels[coarse]
    named = named_measurement(record, declarations, adapter) if proof_level else None
    if named is not None:
        require(named["logged_provider_units_verified"], "Immutable provider failed verification")
        failures = [name for name, value in named["units"].items() if value == "Failed"]
        should_fail = outcome in ("PROOF_FAILURE", "TERMINATION_FAILURE", "PROOF_FAILURE_WITH_WARNINGS")
        require(bool(failures) == should_fail, "Workspace and named outcome disagree")
        require(len(details["summaries"]) == 1, "Missing single completed summary")
        verified_count, errors = details["summaries"][0]
        require(verified_count == sum(v == "Passed" for v in named["units"].values())
                and (errors > 0) == should_fail, "Summary and named verification counts disagree")
    return dict(outcome=outcome, inherited_classifier_category=coarse,
        strict_workspace_verified=outcome == "VERIFIED" and named is not None,
        named_evidence=named, diagnostic_categories=details["diagnostic_categories"],
        warning_count=details["warnings"], unscored_partial_csv=not proof_level and bool(record["csv"]),
        measurement_unit="Both named method correctness obligations plus all required logged provider obligations; no declared dependency closure")


def guard_module(root=ROOT):
    root = Path(root)
    require(isinstance(GUARD_MANIFEST_SHA, str), "Prospective guard bundle is not pinned yet")
    path = root / "guard-manifest.json"
    require(sha(path.read_bytes()) == GUARD_MANIFEST_SHA, "Guard manifest changed")
    pins = load(path)
    require(sha((root / "guard-provenance.json").read_bytes()) == GUARD_PROVENANCE_SHA
            and load(root / "guard-provenance.json")["runtime_files_sha256"] == pins, "Guard provenance differs")
    require(inventory(root / "guard") == pins, "Standalone guard inventory changed")
    guard = module("internal_contract_measurement_body_guard", root / "guard/body_guard.py")
    require(guard.POLICY_ID == POLICY_ID, "Wrong candidate policy identity")
    return guard


def candidate_bodies(files, task):
    prefixes = {"Helper.dfy": task["fixed_helper_prefix"].encode(), "Client.dfy": task["public_contract_prefix"].encode()}
    result = {}
    for name, prefix in prefixes.items():
        require(files[name].startswith(prefix) and files[name].endswith(SUFFIX), "Target contract/header/suffix changed")
        require(len(files[name]) >= len(prefix) + len(SUFFIX), "Invalid candidate body span")
        result[name] = files[name][len(prefix):-len(SUFFIX)].decode("utf-8")
    return result


def score_candidate(task_id, files, trusted_source_sha256, guard_receipt, record, raw_files, root=ROOT):
    """Score one already-verified candidate, replaying exact guarded body admission.

    The host must obtain trusted_source_sha256 from the reconstructed candidate,
    not model text, and bind the verifier environment to the pinned compute run.
    This function independently replays the pinned guard and all raw/source pins;
    a caller-provided acceptance Boolean is never sufficient.
    """
    root = Path(root)
    adapter, classifier = inherited(root)
    tasks = {t["task_id"]: t for t in load(root / "metadata/tasks.json")}
    require(task_id in tasks, "Unknown candidate task")
    task = tasks[task_id]
    source_pins = source_hashes(files)
    require(source_pins == trusted_source_sha256, "Trusted source hash mismatch")
    seeds = sources(root / "seeds" / task_id)
    require(source_hashes(seeds) == task["source_sha256"] == task["template_sha256"], "Pinned seed source mismatch")
    guard = guard_module(root)
    payload = canonical(candidate_bodies(files, task)).decode()
    try:
        rebuilt_text, replay_receipt = guard.parse_response(payload, {n:b.decode("utf-8") for n,b in seeds.items()}, task)
        rebuilt = {n:text.encode("utf-8") for n,text in rebuilt_text.items()}
    except (ValueError, KeyError, TypeError) as error:
        raise MeasurementError("Candidate guard replay rejected: " + str(error)) from error
    require(rebuilt == files and replay_receipt == guard_receipt, "Candidate or guard receipt replay mismatch")
    declarations = fixed_source_scope(files, source_pins, task["semantic_instance"], "new", adapter, root)
    raw_pins = validate_raw(record, raw_files, source_pins, classifier)
    result = interpret(record, declarations, adapter, classifier)
    return dict(schema="internal-contract-candidate-measurement-v1", task_id=task_id,
        semantic_instance=task["semantic_instance"], source_sha256=source_pins, raw_sha256=raw_pins,
        policy_id=POLICY_ID, guard_receipt_sha256=sha(canonical(guard_receipt)),
        guard_receipt_replayed=True, body_annotations=guard_receipt,
        call_annotation_limit="Syntactic call occurrences only; not necessary reuse, dynamic execution, or a reasoning path.",
        new_verifier_runs=0, new_model_calls=0, **result)


def rejected_output(stage, error_type):
    """Non-success record only; the caller supplies the actual parser/guard error."""
    require(stage in ("envelope", "body_guard") and isinstance(error_type, str) and error_type, "Unknown output rejection stage")
    return dict(outcome="ENVELOPE_REJECTED" if stage == "envelope" else "BODY_GUARD_REJECTED",
        strict_workspace_verified=False, named_evidence=None, stage=stage, error_type=error_type,
        new_verifier_runs=0, new_model_calls=0)


def replay_controls(root=ROOT):
    """Replay exactly the 18 saved observations; not new verifier trials or scores."""
    root = Path(root)
    checked_inputs(root)
    rows = []
    for case in load(root / "metadata/propagation-cases.json"):
        adapter, classifier = inherited(root)
        folder = root / "controls" / case["case_id"]
        files = sources(folder / "sources")
        declarations = fixed_source_scope(files, case["source_sha256"], case["task_id"], case["internal_api_version"], adapter, root)
        record = load(folder / "record.json")
        raw = {n: safe(folder / "raw", n).read_bytes() for n in inventory(folder / "raw")}
        validate_raw(record, raw, case["source_sha256"], classifier)
        result = interpret(record, declarations, adapter, classifier)
        require(result["inherited_classifier_category"] == case["expected"]
                and result["named_evidence"]["local_targets"] == case["expected_local_targets"], "Historical expected outcome differs")
        rows.append(dict(case_id=case["case_id"], variant=case["variant"], record_sha256=sha((folder / "record.json").read_bytes()), **result))
    require(len(rows) == 18, "Expected all 18 historical controls")
    return dict(schema="internal-contract-measurement-historical-replay-v1", historical_observations=18,
        strict_successes=sum(r["strict_workspace_verified"] for r in rows),
        proof_failures=sum(r["outcome"] == "PROOF_FAILURE" for r in rows),
        unlogged_Endpoint_observations=sum(len(r["named_evidence"]["unlogged_definitions"]) for r in rows),
        new_verifier_runs=0, new_model_calls=0, previous_results_unchanged=True,
        candidate_admission=False, interpretation="Exact historical fixture replay, including old API variants; not a prospective candidate guard bypass.", rows=rows)
