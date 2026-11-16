"""Versioned source/coverage gate for trusted Dafny 4.11.0 profiles.

No provider code. Unknown tools, scopes, diagnostic formats or missing evidence
fail closed. A trusted host must review the profile and edit policy; model output
must never supply its own source hashes or obligation inventory.
"""
import base64
import csv
import hashlib
import io
import json
import math
import os
from pathlib import Path, PurePosixPath
import posixpath
import re
import socket
import subprocess
import tempfile
import time

SCHEMA = "repodisco-dafny-source-gate-v1"
DAFNY_VERSION = "4.11.0+fcb2042d6d043a2634f0854338c08feeaaaf4ae2"
Z3_VERSION = "Z3 version 4.12.1 - 64 bit"
HEADER = ["TestResult.DisplayName", "TestResult.Outcome", "TestResult.Duration",
          "TestResult.ResourceCount", "RandomSeed"]
SUMMARY = re.compile(r"^Dafny program verifier finished with (\d+) verified, (\d+) errors?\s*$", re.M)
UNIT = re.compile(r".+ \((?:correctness|well-formedness)\)(?: \(assertion batch [1-9]\d*\))?")
DURATION = re.compile(r"(?:\d+\.)?\d{2}:[0-5]\d:[0-5]\d(?:\.\d+)?")

class GateError(ValueError):
    pass

def require(value, message):
    if not value:
        raise GateError(message)

def sha(raw):
    return hashlib.sha256(raw).hexdigest()

def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()

def hashes(files):
    return {name: sha(raw) for name, raw in sorted(files.items())}

def safe_name(name):
    return (isinstance(name, str) and bool(name) and not name.startswith("-")
            and not PurePosixPath(name).is_absolute() and "\\" not in name and "\x00" not in name
            and all(p not in ("", ".", "..") for p in name.split("/")))

def tokens(text):
    """Only discovers include tokens; not a Dafny parser or edit-policy checker."""
    i = 0
    while i < len(text):
        if text[i].isspace():
            i += 1
        elif text.startswith("//", i):
            end = text.find("\n", i); i = len(text) if end < 0 else end + 1
        elif text.startswith("/*", i):
            depth = 1; i += 2
            while depth and i < len(text):
                if text.startswith("/*", i): depth += 1; i += 2
                elif text.startswith("*/", i): depth -= 1; i += 2
                else: i += 1
            require(depth == 0, "Unclosed comment")
        elif text[i] == '"':
            start = i; i += 1
            while i < len(text):
                if text[i] == "\\": i += 2
                elif text[i] == '"': i += 1; break
                else: i += 1
            require(i <= len(text) and text[i-1] == '"', "Unclosed string")
            yield ("string", text[start:i])
        elif text[i].isalpha() or text[i] == "_":
            start = i; i += 1
            while i < len(text) and (text[i].isalnum() or text[i] in "_'"): i += 1
            yield ("identifier", text[start:i])
        else:
            yield ("punctuation", text[i]); i += 1

def include_edges(files):
    edges = {}
    for name, raw in files.items():
        try: stream = iter(tokens(raw.decode("utf-8")))
        except UnicodeError as error: raise GateError("Source must be UTF-8") from error
        deps = []
        for kind, value in stream:
            if kind == "identifier" and value == "include":
                next_token = next(stream, None)
                require(next_token is not None and next_token[0] == "string",
                        "Unsupported include syntax; review a new profile")
                try: relative = json.loads(next_token[1])
                except ValueError as error: raise GateError("Unsupported include escaping") from error
                require(isinstance(relative, str) and relative and "\\" not in relative
                        and "\x00" not in relative and not PurePosixPath(relative).is_absolute(),
                        "External/unsafe include")
                resolved = posixpath.normpath(posixpath.join(posixpath.dirname(name), relative))
                require(safe_name(resolved) and resolved in files, "Include escapes declared source closure")
                deps.append(resolved)
        edges[name] = sorted(set(deps))
    return dict(sorted(edges.items()))

def validate_scope(files, profile):
    require(profile.get("schema") == SCHEMA and profile.get("language") == "dafny"
            and profile.get("dafny_version") == DAFNY_VERSION
            and profile.get("z3_version") == Z3_VERSION, "Unsupported verifier/profile")
    require(files and all(safe_name(n) and n.endswith(".dfy") and isinstance(b, bytes)
                          for n, b in files.items()), "Exact relative Dafny byte files required")
    for name in files:
        require(not any(str(p) in files for p in PurePosixPath(name).parents), "Path collision")
    require(hashes(files) == profile.get("source_sha256"), "Source pin mismatch")
    require(profile.get("entry") in files, "Missing entry")
    require(profile.get("verification_inputs") == sorted(files), "All declared files must be explicit inputs")
    require(profile.get("include_edges") == include_edges(files), "Include closure differs")
    units, unitless = profile.get("required_units"), profile.get("unitless_files")
    require(isinstance(units, dict) and units and isinstance(unitless, dict), "Explicit proof coverage required")
    require(all(isinstance(label, str) and UNIT.fullmatch(label) and file in files
                for label, file in units.items()), "Invalid unit/source coverage")
    require(set(units.values()).isdisjoint(unitless) and set(units.values()) | set(unitless) == set(files),
            "Missing or conflicting file coverage")
    require(all(isinstance(reason, str) and reason.strip() for reason in unitless.values()),
            "Unlogged files require reviewed explanations")
    require(profile.get("task_id") and profile.get("scope_review") and profile.get("edit_policy"),
            "Host scope/edit-policy provenance required")
    return profile

def command(profile):
    return ["dafny", "verify", "--verify-included-files", "--log-format", "csv",
            *profile["verification_inputs"]]

def record_from_raw(profile, run_id, exit_code, stdout, stderr, csv_files, elapsed_seconds,
                    peak_rss_kib=None, timed_out=False, execution_error=None):
    blobs = {"stdout.txt": stdout, "stderr.txt": stderr}
    blobs.update({"csv/" + name: raw for name, raw in csv_files.items()})
    return dict(schema=SCHEMA, run_id=run_id, profile_sha256=sha(canonical(profile)),
                source_sha256=profile["source_sha256"], command=command(profile),
                toolchain={"dafny": DAFNY_VERSION, "z3": Z3_VERSION}, exit_code=exit_code,
                elapsed_seconds=elapsed_seconds, peak_rss_kib=peak_rss_kib,
                timed_out=timed_out, execution_error=execution_error,
                attempts=1, model_calls=0, raw_sha256=hashes(blobs),
                raw_base64={name: base64.b64encode(raw).decode() for name, raw in blobs.items()})

def decode_record(files, profile, record, expected_run_id):
    validate_scope(files, profile)
    require(record.get("schema") == SCHEMA and record.get("run_id") == expected_run_id,
            "Run identity differs")
    require(record.get("profile_sha256") == sha(canonical(profile))
            and record.get("source_sha256") == hashes(files), "Stale profile/source evidence")
    require(record.get("command") == command(profile), "Verification input command differs")
    require(record.get("toolchain") == {"dafny": DAFNY_VERSION, "z3": Z3_VERSION},
            "Toolchain binding differs")
    require(type(record.get("attempts")) is int and record["attempts"] == 1
            and type(record.get("model_calls")) is int and record["model_calls"] == 0, "Unexpected invocation provenance")
    require(type(record.get("elapsed_seconds")) in (int, float)
            and math.isfinite(record["elapsed_seconds"]) and record["elapsed_seconds"] >= 0, "Invalid runtime")
    require(record.get("peak_rss_kib") is None or
            (type(record["peak_rss_kib"]) is int and record["peak_rss_kib"] >= 0), "Invalid memory metric")
    require(type(record.get("timed_out")) is bool and
            (record.get("execution_error") is None or isinstance(record["execution_error"], str)),
            "Missing process completion state")
    require(record.get("exit_code") is None or type(record["exit_code"]) is int, "Invalid exit")
    encoded = record.get("raw_base64")
    require(isinstance(encoded, dict) and {"stdout.txt", "stderr.txt"} <= set(encoded), "Missing raw streams")
    require(all(safe_name(n) and (n in {"stdout.txt","stderr.txt"} or
            n.startswith("csv/") and n.endswith(".csv")) for n in encoded), "Unexpected artifact path")
    try: raw = {n: base64.b64decode(b, validate=True) for n, b in encoded.items()}
    except (TypeError, ValueError) as error: raise GateError("Invalid artifact encoding") from error
    require(hashes(raw) == record.get("raw_sha256"), "Raw evidence hash mismatch")
    return raw

def score(files, profile, record, expected_run_id):
    raw = decode_record(files, profile, record, expected_run_id)
    text = raw["stdout.txt"].decode("utf-8", errors="replace") + "\n" + raw["stderr.txt"].decode("utf-8", errors="replace")
    code = record["exit_code"]
    warnings = max([len(re.findall(r"^.*\bWarning\s*:", text, re.I | re.M))]
                   + [int(n) for n in re.findall(r"\b(\d+) warnings?\b", text, re.I)])
    errors = re.findall(r"^.*\bError:\s*(.*)$", text, re.M)
    summaries = [(int(a), int(b)) for a,b in SUMMARY.findall(text)]
    completed = False
    if record["execution_error"]: category = "EXECUTION_ERROR"
    elif record["timed_out"] or code == 124: category = "TIMEOUT"
    elif code == 137: category = "KILLED"
    elif re.search(r"(?:Error:.*(?:timed out|time limit)|\b[1-9]\d* time outs?\b)", text, re.I): category = "VERIFIER_TIMEOUT"
    elif re.search(r"Error:.*(?:out of resource|resource limit|out of memory)", text, re.I): category = "RESOURCE_EXHAUSTED"
    elif code == 2 and re.search(r"\bparse errors? detected\b", text, re.I): category = "PARSE_FAILURE"
    elif code == 2 and re.search(r"\bresolution/type errors? detected\b", text, re.I): category = "RESOLUTION_OR_TYPE_FAILURE"
    elif code in (0,2) and len(summaries) == 1 and summaries[0][0] > 0 and summaries[0][1] == 0 and not errors:
        require(code == 0 or warnings > 0, "Unexplained nonzero completed verification")
        category = "WARNING_ONLY" if warnings else "VERIFIED"; completed = True
    elif code == 4 and len(summaries) == 1 and summaries[0][1] > 0 and errors:
        category = "PROOF_FAILURE_WITH_WARNINGS" if warnings else "PROOF_FAILURE"; completed = True
    else: category = "UNCLASSIFIED_ERROR"
    units = {}
    if completed:
        for name, data in raw.items():
            if not name.startswith("csv/"): continue
            try:
                reader = csv.DictReader(io.StringIO(data.decode("utf-8"), newline=""), strict=True)
                require(reader.fieldnames == HEADER, "CSV schema differs")
                for row in reader:
                    require(set(row) == set(HEADER) and all(isinstance(v, str) for v in row.values()), "Malformed CSV row")
                    label, outcome = row[HEADER[0]], row[HEADER[1]]
                    require(label in profile["required_units"] and label not in units, "Unknown/duplicate proof unit")
                    require(outcome in {"Passed","Failed"} and DURATION.fullmatch(row[HEADER[2]])
                            and row[HEADER[3]].isdigit() and row["RandomSeed"] == "0", "Invalid/incomplete proof unit")
                    units[label] = outcome
            except (UnicodeError,csv.Error) as error: raise GateError("Malformed CSV bytes") from error
        require(set(units) == set(profile["required_units"]), "Missing proof-unit coverage")
        failed = any(value == "Failed" for value in units.values())
        require(failed == category.startswith("PROOF_FAILURE"), "Summary/named outcomes disagree")
        require(summaries[0][0] == sum(v == "Passed" for v in units.values()), "Verified count/CSV mismatch")
    return dict(category=category, strict_success=category=="VERIFIED", units=units,
                proof_coverage_complete=completed, warnings=warnings,
                unlogged_files=profile["unitless_files"],
                elapsed_seconds=record["elapsed_seconds"], peak_rss_kib=record["peak_rss_kib"])

def verify(files, profile, run_id, process_runner=None):
    validate_scope(files, profile)
    native = process_runner is None
    if native:
        require(os.environ.get("SLURM_JOB_ID") and "login" not in socket.gethostname().lower(),
                "Live verification requires compute allocation")
        for invocation, expected in [(["dafny", "--version"], DAFNY_VERSION), (["z3", "--version"], Z3_VERSION)]:
            observed = subprocess.run(invocation, capture_output=True, text=True, timeout=15)
            require(observed.returncode == 0 and observed.stdout.strip() == expected,
                    "Native toolchain differs from profile")
    runner = subprocess.run if native else process_runner
    start = time.monotonic()
    with tempfile.TemporaryDirectory(prefix="repodisco-covered-") as temporary:
        root = Path(temporary)
        for name, data in files.items():
            path=root/name;path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(data)
        require({p.relative_to(root).as_posix():p.read_bytes() for p in root.rglob("*.dfy")} == files,
                "Staged bytes differ")
        invocation = ["/usr/bin/time","-f","%M","-o","maxrss.txt","timeout","-k","5s","60s",*command(profile)]
        timeout, error = False, None
        try:
            result = runner(invocation,cwd=root,capture_output=True,timeout=75)
            code, out, err = result.returncode, result.stdout, result.stderr
        except subprocess.TimeoutExpired as exc:
            code, out, err = None, exc.stdout or b"", exc.stderr or b""; timeout=True
        except OSError as exc:
            code, out, err = None, b"", str(exc).encode(); error=type(exc).__name__
        csv_files={p.relative_to(root).as_posix():p.read_bytes() for p in root.rglob("*.csv")}
        memory=(root/"maxrss.txt").read_text().strip() if (root/"maxrss.txt").exists() else ""
        peak=int(memory.splitlines()[-1]) if memory and memory.splitlines()[-1].isdigit() else None
        return record_from_raw(profile,run_id,code,out,err,csv_files,time.monotonic()-start,peak,timeout,error)
