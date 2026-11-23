"""Pure replay of host-pinned Dafny observations; never an acceptance issuer.

Coverage/count checks are adapted from real-repository-evolution-001/
harness-001/dafny_gate.py. No subprocess, network, model, or file writes occur.
"""
from collections import Counter
import csv
from dataclasses import dataclass
import hashlib
import io
import json
import math
from pathlib import PurePosixPath
import re

PROFILE_SCHEMA = "dafny-library-native-profile-v1"
RECORD_SCHEMA = "dafny-library-native-record-v1"
REVIEW_SCHEMA = "dafny-library-native-review-v1"
BASE_COLUMNS = ("TestResult.DisplayName", "TestResult.Outcome",
                "TestResult.Duration", "TestResult.ResourceCount")
CSV_SCHEMAS = (BASE_COLUMNS, BASE_COLUMNS + ("RandomSeed",))
SUMMARY = re.compile(r"^Dafny program verifier finished with (\d+) verified, (\d+) errors?\s*$", re.M)
UNIT = re.compile(r".+ \((?:correctness|well-formedness)\)(?: \(assertion batch [1-9]\d*\))?")
DURATION = re.compile(r"(?:\d+\.)?\d{2}:[0-5]\d:[0-5]\d(?:\.\d+)?")
HEX = re.compile(r"[0-9a-f]{64}")


class EvidenceError(ValueError):
    pass


def require(condition, message):
    if not condition:
        raise EvidenceError(message)


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"),
                      ensure_ascii=True, allow_nan=False).encode()


def sha(data):
    return hashlib.sha256(data).hexdigest()


def hashes(files):
    return {name: sha(data) for name, data in sorted(files.items())}


def safe_path(name):
    return (isinstance(name, str) and bool(name) and not name.startswith("-")
            and not PurePosixPath(name).is_absolute() and "\\" not in name
            and all(32 <= ord(c) < 127 for c in name)
            and all(part not in {"", ".", ".."} for part in name.split("/")))


def check_sources(sources):
    require(isinstance(sources, dict) and sources, "Nonempty source map required")
    require(all(safe_path(name) and name.endswith(".dfy") and isinstance(data, bytes)
                for name, data in sources.items()), "Exact relative Dafny byte sources required")
    require(all(not any(str(parent) in sources for parent in PurePosixPath(name).parents)
                for name in sources), "Source path collision")
    for data in sources.values():
        try:
            data.decode("utf-8", errors="strict")
        except UnicodeError as error:
            raise EvidenceError("Source is not UTF-8") from error
    return hashes(sources)


@dataclass(frozen=True)
class EvidencePins:
    """Selected by the trusted host, never taken from model/receipt JSON.

    Hashes prove identity relative to these pins, not the authenticity of pins.
    The host must own/review the native process and freeze its qualified profile.
    """
    profile_sha256: str
    record_sha256: str
    source_revision_sha256: str
    raw_sha256: tuple[tuple[str, str], ...]
    run_id: str
    origin: str


def _validate(profile, sources, record, raw, pins, allow_synthetic):
    require(isinstance(pins, EvidencePins), "Trusted host EvidencePins object required")
    require(all(isinstance(value, str) and HEX.fullmatch(value) for value in
                (pins.profile_sha256, pins.record_sha256, pins.source_revision_sha256)),
            "Invalid host digest")
    source_hashes = check_sources(sources)
    require(sha(canonical(profile)) == pins.profile_sha256, "Stale/unpinned profile")
    require(sha(canonical(record)) == pins.record_sha256, "Stale/unpinned native record")
    require(sha(canonical(source_hashes)) == pins.source_revision_sha256,
            "Source revision differs from host pins")
    require(profile.get("schema") == PROFILE_SCHEMA and record.get("schema") == RECORD_SCHEMA,
            "Unsupported evidence schema")
    require(isinstance(profile.get("project"), str) and profile["project"]
            and type(profile.get("stage")) is int and profile["stage"] in (0, 1, 2)
            and isinstance(profile.get("stage_id"), str) and profile["stage_id"],
            "Missing project/stage identity")
    require(profile.get("inventory_status") in {"pending", "qualified"}, "Inventory qualification unspecified")
    require(record.get("run_id") == pins.run_id and isinstance(pins.run_id, str) and pins.run_id,
            "Native run differs from host identity")
    require(record.get("origin") == pins.origin and pins.origin in
            {"analyst_qualification", "model_candidate", "synthetic_offline"}, "Origin differs from host identity")
    synthetic = pins.origin == "synthetic_offline" or profile.get("synthetic") is True
    require(not synthetic or allow_synthetic, "Synthetic evidence is rejected by default")
    require(record.get("source_before_sha256") == source_hashes
            and record.get("source_after_sha256") == source_hashes,
            "Native source changed or is stale")
    command = profile.get("command")
    require(isinstance(command, list) and command
            and all(isinstance(value, str) and value and "\x00" not in value for value in command)
            and record.get("argv") == command, "Exact native command differs")
    inputs = profile.get("verification_inputs")
    if inputs is not None:
        require(isinstance(inputs, list) and all(isinstance(name, str) for name in inputs)
                and len(inputs) == len(set(inputs)) and set(inputs) == set(sources)
                and command[-len(inputs):] == inputs,
                "Exact complete explicit verification inputs differ from sources/argv")
    tools = profile.get("toolchain")
    require(isinstance(tools, dict) and tools and record.get("toolchain") == tools
            and record.get("toolchain_after") == tools, "Exact before/after toolchain differs")
    require(type(record.get("attempts")) is int and record["attempts"] == 1
            and type(record.get("model_calls")) is int and record["model_calls"] == 0,
            "Unexpected native attempt/model count")
    require(type(record.get("timeout")) is bool, "Missing timeout state")
    require(record.get("exit_code") is None or type(record["exit_code"]) is int, "Invalid process exit")
    elapsed = record.get("elapsed_seconds")
    require(type(elapsed) in (int, float) and math.isfinite(elapsed) and elapsed >= 0,
            "Invalid elapsed time")
    host = record.get("host")
    require(isinstance(host, dict) and all(isinstance(host.get(key), str) and host[key]
            for key in ("job_id", "hostname", "partition")), "Missing compute provenance")
    require(synthetic or "login" not in host["hostname"].lower(), "Login-node evidence is ineligible")
    require(isinstance(raw, dict) and {"stdout.txt", "stderr.txt", "resources.txt"} <= set(raw),
            "Missing full native raw evidence")
    require(all(safe_path(name) and isinstance(data, bytes) and
                (name in {"stdout.txt", "stderr.txt", "resources.txt"}
                 or name.startswith("csv/") and name.endswith(".csv"))
                for name, data in raw.items()), "Unexpected native raw artifact")
    raw_hashes = hashes(raw)
    require(record.get("raw_sha256") == raw_hashes
            and tuple(sorted(raw_hashes.items())) == pins.raw_sha256,
            "Native raw bytes differ from host pins")
    columns = profile.get("csv_columns")
    require(isinstance(columns, list) and tuple(columns) in CSV_SCHEMAS, "Unqualified CSV schema")
    require(type(profile.get("random_seed")) is int and profile["random_seed"] >= 0,
            "Random seed must be explicit")
    units = profile.get("required_units")
    unitless = profile.get("unitless_files")
    require(isinstance(units, dict) and isinstance(unitless, dict), "Coverage map required")
    require(all(isinstance(name, str) and UNIT.fullmatch(name) and source in sources
                for name, source in units.items()), "Invalid named source coverage")
    require(all(name in sources and isinstance(reason, str) and reason.strip()
                for name, reason in unitless.items()), "Unlogged files need explicit reasons")
    require(set(units.values()).isdisjoint(unitless)
            and set(units.values()) | set(unitless) == set(sources), "Every source needs explicit coverage")
    require(profile["inventory_status"] != "qualified" or bool(units), "Qualified empty inventory prohibited")
    require(isinstance(profile.get("inherited_warnings"), list)
            and all(isinstance(value, str) and value for value in profile["inherited_warnings"]),
            "Warning policy must be explicit")
    unlogged = profile.get("unlogged_definitions")
    require(isinstance(unlogged, list), "Unlogged definition policy must be explicit")
    seen = set()
    for entry in unlogged:
        require(isinstance(entry, dict) and isinstance(entry.get("name"), str) and entry["name"]
                and entry["name"] not in seen and entry.get("file") in sources
                and entry.get("source_sha256") == source_hashes[entry["file"]]
                and entry.get("counted_as_pass") is False,
                "Invalid/stale unlogged definition identity")
        require(not any(label.startswith(entry["name"] + " (") for label in units),
                "Logged definition mislabeled as unlogged")
        seen.add(entry["name"])
    return source_hashes, raw_hashes, synthetic


def _csv(profile, raw):
    rows = []
    seen = set()
    columns = profile["csv_columns"]
    for path, data in sorted(raw.items()):
        if not path.startswith("csv/"):
            continue
        try:
            reader = csv.DictReader(io.StringIO(data.decode("utf-8", errors="strict"), newline=""), strict=True)
            require(reader.fieldnames == columns, "Native CSV columns differ")
            for index, row in enumerate(reader, 2):
                require(set(row) == set(columns) and all(isinstance(value, str) for value in row.values()),
                        "Malformed native CSV row")
                name, outcome, duration, resource = (row[key] for key in BASE_COLUMNS)
                require(UNIT.fullmatch(name) and name not in seen, "Invalid/duplicate native proof unit")
                require(outcome in {"Passed", "Failed", "Inconclusive", "Timeout", "OutOfResource"}
                        and DURATION.fullmatch(duration) and resource.isdigit(), "Invalid native outcome/metric")
                if "RandomSeed" in columns:
                    require(row["RandomSeed"] == str(profile["random_seed"]), "Native random seed differs")
                seen.add(name)
                rows.append(dict(name=name, outcome=outcome, csv=path, row=index,
                                 fields=row))
        except (UnicodeError, csv.Error) as error:
            raise EvidenceError("Malformed native CSV") from error
    return rows


def _resources(data):
    """Retain GNU time metrics separately from proof correctness."""
    try:
        text = data.decode("utf-8", errors="strict")
    except UnicodeError as error:
        raise EvidenceError("Undecodable resource record") from error
    patterns = {
        "max_rss_kib": (r"^\s*Maximum resident set size \(kbytes\): (\d+)\s*$", int),
        "user_cpu_seconds": (r"^\s*User time \(seconds\): (\d+(?:\.\d+)?)\s*$", float),
        "system_cpu_seconds": (r"^\s*System time \(seconds\): (\d+(?:\.\d+)?)\s*$", float),
        "wall_time": (r"^\s*Elapsed \(wall clock\) time \(h:mm:ss or m:ss\): ([0-9:.]+)\s*$", str),
        "exit_status": (r"^\s*Exit status: (-?\d+)\s*$", int),
    }
    observed = {}
    for name, (pattern, convert) in patterns.items():
        values = re.findall(pattern, text, re.M)
        require(len(values) <= 1, "Duplicate resource metric")
        observed[name] = convert(values[0]) if values else None
    observed["complete"] = all(value is not None for value in observed.values())
    return observed


def review(profile, sources, record, raw, pins, *, allow_synthetic=False):
    """Replay exact evidence and return a report, never a promotion/acceptance.

    Integrity failures raise EvidenceError. Returned categories describe native
    observations, including completed negative controls and incomplete coverage.
    """
    source_hashes, raw_hashes, synthetic = _validate(profile, sources, record, raw, pins, allow_synthetic)
    try:
        text = raw["stdout.txt"].decode("utf-8", errors="strict") + "\n" + raw["stderr.txt"].decode("utf-8", errors="strict")
    except UnicodeError as error:
        raise EvidenceError("Undecodable native diagnostic bytes") from error
    rows = _csv(profile, raw)
    resources = _resources(raw["resources.txt"])
    units = {row["name"]: row["outcome"] for row in rows}
    expected = set(profile["required_units"])
    missing, extra = sorted(expected - set(units)), sorted(set(units) - expected)
    coverage_complete = bool(expected) and not missing and not extra
    warning_lines = re.findall(r"^.*\bWarning\s*:[^\n]*$", text, re.I | re.M)
    warning_summary = [int(n) for n in re.findall(r"\b(\d+) warnings?\b", text, re.I)]
    warnings = max([len(warning_lines)] + warning_summary)
    warning_policy_matches = (warnings == len(warning_lines)
                              and Counter(warning_lines) == Counter(profile["inherited_warnings"]))
    errors = re.findall(r"^.*\bError\s*:[^\n]*$", text, re.I | re.M)
    summaries = [(int(a), int(b)) for a, b in SUMMARY.findall(text)]
    passed = sum(value == "Passed" for value in units.values())
    failed = sum(value == "Failed" for value in units.values())
    nonfinal = sorted(name for name, value in units.items() if value not in {"Passed", "Failed"})
    code = record["exit_code"]
    category = "UNKNOWN_NATIVE_FAILURE"
    terminal = True
    if record["timeout"] or code == 124:
        category = "TIMEOUT"
    elif code is None or code < 0 or code in {137, 143}:
        category = "PROCESS_FAILURE"
    elif re.search(r"(?:Error:.*(?:timed out|time limit)|\b[1-9]\d* time outs?\b)", text, re.I):
        category = "VERIFIER_TIMEOUT"
    elif re.search(r"(?:Error:.*(?:out of resource|resource limit|out of memory)|OutOfResource)", text, re.I) or nonfinal:
        category = "RESOURCE_FAILURE"
    elif re.search(r"\bparse errors? detected\b", text, re.I):
        category = "FRONTEND_PARSE_FAILURE"
    elif re.search(r"\bresolution/type errors? detected\b", text, re.I):
        category = "FRONTEND_RESOLUTION_FAILURE"
    elif not resources["complete"] or resources["exit_status"] != code:
        category = "RESOURCE_OBSERVATION_MISMATCH"
    elif not coverage_complete:
        category = "COVERAGE_FAILURE"
    elif len(summaries) != 1 or summaries[0][0] != passed:
        category = "SUMMARY_INVENTORY_MISMATCH"
    elif code == 4 and summaries[0][1] > 0 and failed > 0 and errors:
        category, terminal = "PROOF_FAILURE", False
    elif summaries[0][1] == 0 and failed == 0 and not errors and code in {0, 2}:
        if code == 2 and warnings:
            category, terminal = "WARNING_ONLY", False
        elif code == 0:
            category, terminal = ("VERIFIED_WITH_WARNINGS" if warnings else "VERIFIED"), False
    qualified = (category in {"VERIFIED", "VERIFIED_WITH_WARNINGS"}
                 and profile["inventory_status"] == "qualified" and warning_policy_matches)
    return dict(schema=REVIEW_SCHEMA, project=profile["project"], stage=profile["stage"],
                stage_id=profile["stage_id"], run_id=record["run_id"], origin=record["origin"],
                synthetic=synthetic, category=category, terminal=terminal,
                qualified_success=qualified, strict_zero_warning_success=qualified and warnings == 0,
                proof_coverage_complete=coverage_complete, missing_units=missing, extra_units=extra,
                units=rows, passed_units=passed, failed_units=failed, summaries=summaries,
                warnings=warnings, warning_lines=warning_lines, warning_policy_matches=warning_policy_matches,
                unlogged_definitions=profile["unlogged_definitions"], unitless_files=profile["unitless_files"],
                elapsed_seconds=record["elapsed_seconds"], resources=resources,
                resources_sha256=raw_hashes["resources.txt"],
                profile_sha256=pins.profile_sha256, record_sha256=pins.record_sha256,
                source_revision_sha256=sha(canonical(source_hashes)),
                raw_fingerprint_sha256=sha(canonical(raw_hashes)),
                acceptance_issued=False)
