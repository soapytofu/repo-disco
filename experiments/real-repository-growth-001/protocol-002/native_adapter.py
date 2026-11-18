"""Lossless, source-bound native evidence replay. No verifier or promotion.

Trusted host pins select records; JSON cannot authenticate itself. Full-stage
analyst references remain reference observations, never stage-one acceptances.
"""
from collections import Counter
from dataclasses import asdict, dataclass
import csv
import io
import json
import math
from pathlib import Path
import re

import body_policy as b
from native_parsers import dafny as dg
from native_parsers.vest import protocol_v2 as vg
from native_parsers import warning_policy

VERSION = "growth-native-occurrence-adapter-v2"
OCCURRENCE_TAG = "verus-timed-occurrence-v1"
REFERENCE_ROOT_SHA256 = "0999050882566d8630dec4566ed5526e05fbabcd9f4f1092c9c9322322a82207"
SPECIAL = {"scope.json", "qualification-gate.json", "profile.json", "bound-record.json",
           "record.json", "tools-before.json", "tools-after.json"}


def require(condition, message):
    if not condition:
        raise ValueError(message)


def exact(record, values):
    require(isinstance(record, dict), "Expected typed object")
    require(all(type(record.get(key)) is type(value) and record.get(key) == value
                for key, value in values.items()), "Missing, stale or contradictory evidence field")


def compact(value):
    return json.dumps(value, ensure_ascii=True, separators=(",", ":"), allow_nan=False)


def _native_json(raw, stream):
    """Retain native JSON object positions, including duplicate timing records."""
    require(isinstance(raw, bytes), "Native stream bytes required")
    try:
        text = raw.decode("utf-8")
    except UnicodeDecodeError as error:
        raise ValueError("Invalid native stream encoding") from error
    decoder = json.JSONDecoder(object_pairs_hook=b.unique, parse_constant=b.reject_constant)
    cursor = 0
    reports = []
    object_index = 0
    while match := re.search(r"^\{", text[cursor:], re.M):
        start = cursor + match.start()
        try:
            obj, end = decoder.raw_decode(text, start)
        except (ValueError, RecursionError) as error:
            raise ValueError("Malformed, duplicate-key or truncated native JSON") from error
        cursor = end
        if isinstance(obj, dict) and "verification-results" in obj:
            start_byte, end_byte = len(text[:start].encode()), len(text[:end].encode())
            reports.append((obj, dict(stream=stream, json_object_index=object_index,
                                      start_byte=start_byte, end_byte=end_byte,
                                      json_sha256=b.sha(raw[start_byte:end_byte]))))
        object_index += 1
    return reports


def inverse_occurrences(rows):
    """Decode each explicit occurrence slot and reconstruct exact tuple counts."""
    counts, ordinals, seen = Counter(), {}, set()
    for row in rows:
        require(isinstance(row, dict) and isinstance(row.get("unit"), str), "Invalid occurrence row")
        try:
            decoded = json.loads(row["unit"])
        except (ValueError, TypeError) as error:
            raise ValueError("Malformed occurrence identifier") from error
        require(isinstance(decoded, list) and len(decoded) == 6 and decoded[0] == OCCURRENCE_TAG,
                "Unknown occurrence encoding")
        require(all(isinstance(x, str) and x for x in decoded[1:5]) and
                type(decoded[5]) is int and decoded[5] > 0, "Invalid tuple/ordinal")
        require(row["unit"] == compact(decoded) and row["unit"] not in seen,
                "Noncanonical or duplicate occurrence identifier")
        require(row.get("identity") == decoded[1:5] and row.get("ordinal") == decoded[5],
                "Occurrence identity differs")
        require(type(row.get("success")) is bool and row.get("status") ==
                ("Passed" if row["success"] else "Failed"), "Outcome is not an actual Boolean observation")
        key = compact(decoded[1:5])
        counts[key] += 1
        ordinals.setdefault(key, set()).add(decoded[5])
        seen.add(row["unit"])
    require(all(values == set(range(1, counts[key] + 1)) for key, values in ordinals.items()),
            "Occurrence ordinals have gaps or collisions")
    return dict(sorted(counts.items()))


def _extract_verus(raw, exit_code):
    parsed = vg.verus_observation(exit_code, raw["stdout.txt"], raw["stderr.txt"])
    reports = _native_json(raw["stdout.txt"], "stdout.txt") + _native_json(raw["stderr.txt"], "stderr.txt")
    counts, rows, native_reports = Counter(), [], []
    crates_seen = set()
    for document, location in reports:
        modules = document.get("times-ms", {}).get("smt", {}).get("smt-run-module-times", [])
        require(isinstance(modules, list), "Native module breakdown absent")
        all_units = [unit for module in modules for unit in module.get("function-breakdown", [])]
        crates = {unit.get("function", "").split("::")[0] for unit in all_units} & {"vstd", "vest_lib", "vest_dev"}
        require(len(crates) == 1, "Missing or mixed native crate identity")
        crate = next(iter(crates))
        require(crate not in crates_seen, "Duplicate native crate report")
        crates_seen.add(crate)
        report_index = len(native_reports)
        native_reports.append(dict(crate=crate, location=location,
                                   summary=document["verification-results"], version=document.get("verus"),
                                   num_threads=document.get("times-ms", {}).get("num-threads")))
        for module_index, module in enumerate(modules):
            require(isinstance(module.get("module"), str), "Native module name missing")
            for record_index, record in enumerate(module.get("function-breakdown", [])):
                label, mode, success = record.get("function"), record.get("mode:"), record.get("success")
                require(isinstance(label, str) and "::" in label and mode in ("exec", "proof", "spec")
                        and type(success) is bool, "Malformed native occurrence")
                identity = [crate, module["module"], label, mode]
                key = compact(identity)
                counts[key] += 1
                ordinal = counts[key]
                rows.append(dict(unit=compact([OCCURRENCE_TAG, *identity, ordinal]), identity=identity,
                                 ordinal=ordinal, success=success, status="Passed" if success else "Failed",
                                 raw_location=dict(**location, report_index=report_index,
                                                   module_index=module_index, function_breakdown_index=record_index),
                                 native_record=record, native_record_sha256=b.sha(b.canonical(record))))
    rows.sort(key=lambda row: (*row["identity"], row["ordinal"]))
    inverse = inverse_occurrences(rows)
    require(inverse == dict(sorted(counts.items())) == parsed["inventory"],
            "Occurrence expansion does not exactly preserve native multiplicities")
    require(len(rows) == sum(parsed["inventory"].values()), "Native occurrence count differs")
    summaries = {record["crate"]: record["summary"]["verified"] for record in native_reports}
    return parsed, dict(encoding=OCCURRENCE_TAG, rows=rows, inventory=inverse, native_reports=native_reports,
                        timed_occurrences=len(rows), distinct_tuple_keys=len(inverse),
                        native_summary_verified_by_crate=summaries, native_summary_verified_total=sum(summaries.values()),
                        summary_count_is_timing_count=False, occurrence_slots_are_unique_logical_obligations=False)


def _extract_dafny(raw, exit_code):
    csv_files = {name: data for name, data in raw.items() if name.startswith("csv/") and name.endswith(".csv")}
    parsed = dg.dafny_observation(exit_code, raw["stdout.txt"], raw["stderr.txt"], csv_files)
    rows = []
    for name, data in sorted(csv_files.items()):
        reader = csv.DictReader(io.StringIO(data.decode("utf-8"), newline=""), strict=True)
        for index, row in enumerate(reader):
            label, status = row["TestResult.DisplayName"], row["TestResult.Outcome"]
            rows.append(dict(unit=compact(["dafny-named-unit-v1", label]), name=label, status=status,
                             raw_location=dict(stream=name, row_index=index, end_line=reader.line_num),
                             native_record=row, native_record_sha256=b.sha(b.canonical(row))))
    require({row["name"]: row["status"] for row in rows} == parsed["units"] and
            len(rows) == len(parsed["units"]), "Dafny named CSV identity drift")
    rows.sort(key=lambda row: row["name"])
    return parsed, dict(encoding="dafny-named-unit-v1", rows=rows,
                        inventory={name: 1 for name in sorted(parsed["units"])},
                        logged_named_units=len(rows), native_summary=parsed["summary"])


def extract_native(project, raw, exit_code):
    """Parse only; callers must bind and review scope before treating it as evidence."""
    require(project in ("dafny-vmc", "vest") and type(exit_code) is int, "Known project and native exit required")
    require(isinstance(raw, dict) and {"stdout.txt", "stderr.txt", "resources.txt"} <= set(raw),
            "Complete native stream/resource bytes required")
    b.source_hashes(raw)
    parsed, occurrence = (_extract_dafny if project == "dafny-vmc" else _extract_verus)(raw, exit_code)
    return parsed, occurrence


@dataclass(frozen=True)
class NativeBinding:
    """External trusted host pins. Their authenticity is not established here."""
    project: str
    stage: int
    origin: str
    run_id: str
    source_revision_sha256: str
    policy_sha256: str
    # Tuple of pairs deliberately preserves/rejects duplicate artifact names.
    artifact_sha256: tuple


def _pinned(binding, artifacts, allow_synthetic):
    require(isinstance(binding, NativeBinding), "External native binding required")
    require(binding.project in ("dafny-vmc", "vest") and type(binding.stage) is int and binding.stage in (1, 2),
            "Native project/stage differs")
    require(binding.origin in ("analyst-reference", "analyst-control", "model-candidate", "synthetic-offline"),
            "Native evidence origin missing")
    require(binding.origin != "synthetic-offline" or allow_synthetic,
            "Synthetic fixtures are not native acceptance")
    require(isinstance(binding.run_id, str) and b.IDENTITY.fullmatch(binding.run_id), "Invalid native run identity")
    require(binding.policy_sha256 == b.policy_digest(), "Native adapter runtime changed")
    require(isinstance(binding.artifact_sha256, tuple) and
            all(isinstance(item, tuple) and len(item) == 2 for item in binding.artifact_sha256),
            "Immutable artifact pin pairs required")
    pins = dict(binding.artifact_sha256)
    require(len(pins) == len(binding.artifact_sha256), "Duplicate artifact pin")
    b.digest_map(pins)
    require(isinstance(artifacts, dict) and set(artifacts) == set(pins), "Missing or extra native artifact")
    require(SPECIAL <= set(pins), "Native metadata artifacts missing")
    for name, value in pins.items():
        require(isinstance(artifacts[name], bytes) and b.sha(artifacts[name]) == value,
                "Tampered or stale native artifact: " + name)
    return pins


def audit_native(binding, artifacts, sources, *, allow_synthetic=False):
    """Replay bound raw evidence; failed proofs remain valid failed observations."""
    pins = _pinned(binding, artifacts, allow_synthetic)
    scope, gate, profile, bound, record, before, after = (
        b.read_json(artifacts[name]) for name in ("scope.json", "qualification-gate.json", "profile.json",
                                               "bound-record.json", "record.json", "tools-before.json", "tools-after.json"))
    exact(scope, dict(schema="repodisco-native-growth-scope-v2", project=binding.project, stage=binding.stage,
                      qualification_gate_sha256=pins["qualification-gate.json"],
                      warning_policy_sha256=b.sha((b.ROOT / "native_parsers/warning_policy.py").read_bytes())))
    require(isinstance(gate, dict) and gate.get("project") == binding.project,
            "Qualification gate project differs")
    exact(profile, dict(project=binding.project))
    hashes = b.check_workspace(binding.project, binding.stage, sources)
    require(b.digest_map(hashes) == binding.source_revision_sha256, "Actual source revision differs")
    require(profile.get("source_sha256") == hashes, "Native profile source differs")
    raw_names = bound.get("raw_sha256")
    require(isinstance(raw_names, dict) and not SPECIAL.intersection(raw_names) and
            set(artifacts) == SPECIAL | set(raw_names),
            "Native raw file inventory differs")
    raw = {name: artifacts[name] for name in raw_names}
    dg.check_record(bound, profile, binding.run_id, raw)
    require(record.get("command") and isinstance(record["command"], list) and
            all(isinstance(x, str) for x in record["command"]), "Native command absent")
    require(b.sha(b.canonical(record["command"])) == scope.get("command_sha256") and
            profile.get("logical_command") == scope.get("logical_command") and
            profile.get("toolchain") == scope.get("toolchain"), "Native command/tool/scope identity differs")
    exact(record, dict(model_calls=0, attempts=1, exit_code=bound["exit_code"],
                       elapsed_seconds=bound["elapsed_seconds"]))
    require(type(record.get("timeout")) is bool and record["timeout"] == (record["exit_code"] == 124),
            "Native timeout metadata differs")
    require(record.get("artifacts") == {name: b.sha(raw[name]) for name in ("stdout.txt", "stderr.txt", "resources.txt")},
            "Native stdout/stderr/resource bindings differ")
    require(before == after and before.get("project") == binding.project and
            before.get("toolchain") == profile["toolchain"], "Toolchain changed during verification")
    require(b.sha(b.canonical(before)) == scope.get("tools_record_sha256"), "Pinned tool/image closure differs")
    parsed, extraction = extract_native(binding.project, raw, record["exit_code"])
    expected_inventory = scope.get("required_inventory")
    require(isinstance(expected_inventory, dict) and expected_inventory and
            all(isinstance(k, str) and type(v) is int and v > 0 for k, v in expected_inventory.items()),
            "Host-reviewed native occurrence inventory missing")
    if "actual_inventory" in gate:
        gate_inventory = ({name: 1 for name in gate["actual_inventory"]}
                          if binding.project == "dafny-vmc" else gate["actual_inventory"])
        require(expected_inventory == gate_inventory, "Scope silently changed the reviewed native inventory")
    else:
        require(gate.get("required_inventory_sha256") == b.sha(b.canonical(expected_inventory)),
                "Required native inventory is not bound to the reviewed gate")
    coverage = extraction["inventory"] == expected_inventory
    metadata_match = True
    if binding.project == "vest":
        metadata = scope.get("verus_metadata", {})
        metadata_match = (set(parsed["crates"]) == set(metadata.get("crates", [])) and
                          all(info["version"] == metadata.get("version") and info["num_threads"] == metadata.get("num_threads")
                              for info in parsed["crates"].values()) and parsed["entire_crate"])
    coverage = bool(coverage and metadata_match and parsed["coverage_complete"])
    observation = dict(parsed, coverage_complete=coverage, proof_pass=bool(parsed["proof_pass"] and coverage))
    allowed_warnings = scope.get("upstream_warnings")
    require(isinstance(allowed_warnings, list) and all(isinstance(w, str) for w in allowed_warnings),
            "Host warning profile missing")
    exact_warnings = Counter(parsed["warnings"]) == Counter(allowed_warnings)
    observation["qualified_scope_pass"] = observation["proof_pass"] and exact_warnings
    warning_review = warning_policy.report(binding.project, observation, record, dict(upstream_warnings=allowed_warnings))
    passed = bool(record["exit_code"] == 0 and not record["timeout"] and coverage and
                  observation["proof_pass"] and warning_review["eligible_under_policy_v2"])
    extraction.update(schema="repodisco-source-bound-native-occurrences-v2", derived_from_native_streams=True,
                      is_a_separate_verifier_output=False, adapter=VERSION, adapter_runtime_sha256=b.policy_digest(),
                      origin=binding.origin, project=binding.project, stage=binding.stage, run_id=binding.run_id,
                      source_revision_sha256=binding.source_revision_sha256, source_sha256=hashes,
                      raw_sha256={name: b.sha(data) for name, data in sorted(raw.items())},
                      bound_record_sha256=pins["bound-record.json"], execution_record_sha256=pins["record.json"],
                      native_profile_sha256=pins["profile.json"], scope_sha256=pins["scope.json"],
                      qualification_gate_sha256=pins["qualification-gate.json"],
                      native_command_sha256=scope["command_sha256"], toolchain_sha256=b.sha(b.canonical(profile["toolchain"])),
                      tools_before_sha256=pins["tools-before.json"], tools_after_sha256=pins["tools-after.json"],
                      qualified_pass=passed, native_exit_code=record["exit_code"], coverage_complete=coverage,
                      warning_review=warning_review, fixed_unlogged_definitions=scope.get("unlogged_definitions", []),
                      native_summary_and_timed_inventory_are_separate=True, accepted_revision_issued=False)
    require(isinstance(extraction["fixed_unlogged_definitions"], list) and
            all(isinstance(item, dict) for item in extraction["fixed_unlogged_definitions"]),
            "Malformed unlogged source inventory")
    for missing in extraction["fixed_unlogged_definitions"]:
        require(missing.get("counted_as_pass") is False and missing.get("source_sha256") == hashes.get(missing.get("file")),
                "Unlogged definition is not bound to an exact source file")
        require(compact(missing.get("unit")) not in extraction["inventory"], "Logged definition mislabeled unlogged")
    return extraction


def _read_pinned(repo, pins):
    data = {}
    root = Path(repo).resolve()
    for name, digest in pins.items():
        b.path_name(name)
        path = root / name
        cursor = path
        while cursor != root:
            require(not cursor.is_symlink(), "Symlink in evidence input")
            cursor = cursor.parent
        raw = path.read_bytes()
        require(b.sha(raw) == digest, "Reviewed evidence bytes changed: " + name)
        data[name] = raw
    return data


def reference_material(project, repo):
    """Load only the two externally pinned analyst reference replays."""
    b.load_assets()
    inputs = b.read_json((b.ROOT / "reference-inputs.json").read_bytes())
    require(inputs["root_gate_sha256"] == REFERENCE_ROOT_SHA256, "Root reference review differs")
    require(project in inputs["references"], "Unknown reviewed reference project")
    item = inputs["references"][project]
    data = _read_pinned(repo, item["files"])
    overall = b.read_json(data[inputs["root_gate"]])
    require(b.sha(data[inputs["root_gate"]]) == REFERENCE_ROOT_SHA256 and
            overall["references"][project]["sha256"] == b.sha(data[item["gate"]]), "Root/project gate linkage differs")
    gate, reviewed, base = (b.read_json(data[item[key]]) for key in ("gate", "review", "baseline_profile"))
    exact(gate, dict(project=project, analyst_authored=True, accepted_model_parent=False,
                     model_generated_growth=False, native_exit_code=0, model_calls=0))
    require(reviewed["status"] == "REFERENCE_EVIDENCE_REPLAY_PASSED" and
            reviewed["result"]["case"] == item["case"], "Reference replay review differs")
    prefix = item["artifact_root"] + "/"
    for name, digest in reviewed["raw_files"].items():
        require(b.sha(data[prefix + name]) == digest, "Reviewed raw artifact identity differs")
    case_prefix = prefix + item["case"] + "/"
    profile_raw, bound_raw, record_raw = (data[case_prefix + name] for name in ("profile.json", "bound-record.json", "record.json"))
    profile, bound, record = (b.read_json(raw) for raw in (profile_raw, bound_raw, record_raw))
    before_raw, after_raw = data[prefix + "tools-before.json"], data[prefix + "tools-after.json"]
    before = b.read_json(before_raw)
    scope = dict(schema="repodisco-native-growth-scope-v2", project=project, stage=2,
                 qualification_gate_sha256=b.sha(data[item["gate"]]), readiness="REFERENCE_ONLY_NOT_STAGE_ONE_ACCEPTANCE",
                 command_sha256=b.sha(b.canonical(record["command"])), logical_command=profile["logical_command"],
                 toolchain=profile["toolchain"], tools_record_sha256=b.sha(b.canonical(before)),
                 warning_policy_sha256=b.sha((b.ROOT / "native_parsers/warning_policy.py").read_bytes()),
                 upstream_warnings=base["upstream_warnings"],
                 required_inventory=({name: 1 for name in gate["actual_inventory"]} if project == "dafny-vmc" else gate["actual_inventory"]),
                 unlogged_definitions=(gate.get("fixed_unlogged_growth_definitions", []) if project == "dafny-vmc"
                                       else gate["source_bound_unlogged_definitions"]))
    if project == "vest":
        scope["verus_metadata"] = dict(crates=base["required"]["crates"], version=base["required"]["version"], num_threads=1)
    artifacts = {name: data[case_prefix + name] for name in bound["raw_sha256"]}
    artifacts.update({"scope.json": b.canonical(scope), "qualification-gate.json": data[item["gate"]],
                      "profile.json": profile_raw, "bound-record.json": bound_raw, "record.json": record_raw,
                      "tools-before.json": before_raw, "tools-after.json": after_raw})
    # Source bytes come from the pinned qualified seed plus exact saved overlays.
    _, inventory = b.load_assets()
    upstream_pins = inventory["projects"][project]["files"]
    seed_prefix = "experiments/real-repository-qualification-001/upstream/" + project + "/"
    upstream = _read_pinned(repo, {seed_prefix + name: sha for name, sha in upstream_pins.items()})
    sources = {name: upstream[seed_prefix + name] for name in upstream_pins}
    for name, digest in gate["overlay_sha256"].items():
        source = data[case_prefix + "overlay/" + name]
        require(b.sha(source) == digest, "Reference overlay source drift")
        sources[name] = source
    require(b.source_hashes(sources) == gate["source_sha256"], "Reference actual sources differ from reviewed gate")
    binding = NativeBinding(project=project, stage=2, origin="analyst-reference", run_id=bound["run_id"],
                            source_revision_sha256=b.digest_map(gate["source_sha256"]), policy_sha256=b.policy_digest(),
                            artifact_sha256=tuple(sorted(b.source_hashes(artifacts).items())))
    return binding, artifacts, sources, dict(root_gate_sha256=REFERENCE_ROOT_SHA256,
                                            reviewed_input_sha256=item["files"], model_accepted_parent=False,
                                            source_stage=2, two_sequential_acceptances=False)


def replay_reference(project, repo):
    binding, artifacts, sources, provenance = reference_material(project, repo)
    extraction = audit_native(binding, artifacts, sources)
    require(extraction["qualified_pass"], "Reviewed full reference does not replay as qualified success")
    gate = b.read_json(artifacts["qualification-gate.json"])
    if project == "vest":
        require(extraction["timed_occurrences"] == gate["actual_timed_occurrences"] == 5416 and
                extraction["distinct_tuple_keys"] == gate["actual_inventory_keys"] == 5306 and
                extraction["native_summary_verified_total"] == sum(gate["native_summary_verified_by_crate"].values()) == 5727,
                "Native occurrence/summary totals differ")
    else:
        require(extraction["logged_named_units"] == gate["total_logged_units"] == 269,
                "Dafny reference inventory differs")
    return dict(status="PINNED_ANALYST_REFERENCE_REPLAY_PASSED", project=project, stage=2,
                eligible_as_accepted_stage_one=False, model_generated_growth=False,
                provenance=provenance, extraction=extraction)


@dataclass(frozen=True)
class AcceptedParentBinding:
    """Prospective host integration; no constructor here creates acceptance."""
    native: NativeBinding
    chain_id: str
    receipt_sha256: str
    extraction_sha256: str


def validate_accepted_parent(child_stage_id, chain_id, sources, binding, artifacts, *, allow_synthetic=False):
    stage, _, _ = b.stage_spec(child_stage_id)
    require(stage["stage"] == 2 and isinstance(binding, AcceptedParentBinding),
            "Stage two needs a separate host-pinned accepted-parent record")
    require(binding.chain_id == chain_id and isinstance(chain_id, str) and b.IDENTITY.fullmatch(chain_id),
            "Accepted parent chain differs")
    native = binding.native
    require(isinstance(native, NativeBinding) and native.project == stage["project"] and native.stage == 1,
            "A full-stage-two reference cannot become a stage-one parent")
    require(native.origin == "model-candidate" or (allow_synthetic and native.origin == "synthetic-offline"),
            "Analyst reference/control is not an accepted model parent")
    require(isinstance(artifacts, dict) and {"accepted.json", "native-units.json"} <= set(artifacts),
            "Accepted record and derived native occurrence artifact required")
    require(b.sha(artifacts["accepted.json"]) == binding.receipt_sha256 and
            b.sha(artifacts["native-units.json"]) == binding.extraction_sha256,
            "Changed accepted parent or extraction artifact")
    metadata = {name: raw for name, raw in artifacts.items() if name not in ("accepted.json", "native-units.json")}
    extraction = audit_native(native, metadata, sources, allow_synthetic=allow_synthetic)
    require(b.canonical(extraction) == artifacts["native-units.json"], "Native extraction does not replay exactly")
    require(extraction["qualified_pass"], "Unproved, incomplete or failed parent cannot advance")
    scope = b.read_json(metadata["scope.json"])
    gate = b.read_json(metadata["qualification-gate.json"])
    exact(scope, dict(readiness="STAGE_ONE_REFERENCE_AND_NEGATIVES_REVIEWED"))
    exact(gate, dict(schema="repodisco-growth-stage-one-scope-qualification-v1", project=native.project, stage=1,
                     status="SOURCE_AND_NATIVE_INVENTORY_REVIEW_PASSED", reference_reviewed=True,
                     negative_controls_reviewed=True, model_acceptance=False,
                     required_inventory_sha256=b.sha(b.canonical(scope["required_inventory"]))))
    receipt = b.read_json(artifacts["accepted.json"])
    exact(receipt, dict(schema="repodisco-growth-host-accepted-stage-one-v2", status="accepted", stage=1,
                        project=native.project, chain_id=chain_id, run_id=native.run_id,
                        origin=native.origin, source_revision_sha256=native.source_revision_sha256,
                        source_sha256=b.source_hashes(sources), policy_sha256=b.policy_digest(),
                        native_binding_sha256=b.sha(b.canonical(asdict(native))),
                        native_extraction_sha256=binding.extraction_sha256,
                        qualification_gate_sha256=b.sha(metadata["qualification-gate.json"])))
    return dict(parent_run_id=native.run_id, parent_revision_sha256=native.source_revision_sha256,
                native_binding_sha256=b.sha(b.canonical(asdict(native))),
                extraction_sha256=binding.extraction_sha256, origin=native.origin,
                evidence_replayed=True, acceptance_created_here=False,
                host_authenticity_established_here=False, native_calls_made=0)
