"""Contain a completed Dafny solver-budget failure; never issue a proof pass.

Called only after the unchanged source/tool/command/inventory native audit. This
is a derived host classification, not a verifier output or evidence authority.
Unknown/missing diagnostics remain terminal. No process or transport is called.
"""
from collections import Counter
import hashlib
import json
import re

VERSION = "growth-completed-dafny-resource-outcome-v1"
SUMMARY = re.compile(r"Dafny program verifier finished with ([0-9]+) verified, 0 errors, ([0-9]+) out of resource")
DIAGNOSTIC = re.compile(r"(.+\.dfy)\(([1-9][0-9]*),([0-9]+)\): Verification out of resource \((.+)\)")
EXCERPT = re.compile(r"\s*(?:[0-9]+)?\s*\|.*")


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def require(value, reason):
    if not value:
        raise ValueError(reason)


def _completed(extraction, artifacts):
    require(extraction["project"] == "dafny-vmc", "unsupported_project")
    require(extraction["native_category"] == "VERIFIER_RESOURCE_FAILURE", "different_native_category")
    require(extraction["native_exit_code"] == 4 and
            extraction["qualified_pass"] is False and extraction["native_proof_pass"] is False,
            "not_an_unaccepted_exit_four")
    record = extraction["native_execution"]
    require(record.get("timeout") is False and record.get("outer_timeout") is False and
            record.get("resource_capture_missing") is False and record.get("attempts") == 1,
            "incomplete_process_or_resources")
    require(extraction["coverage_complete"] is True and
            extraction["known_analyst_native_reuse_rejected"] is True,
            "unqualified_source_or_inventory")
    raw_pins = extraction["raw_sha256"]
    require(all(sha(artifacts[name]) == digest for name, digest in raw_pins.items()), "raw_hash_drift")
    for name, field in (("record.json", "execution_record_sha256"),
                        ("scope.json", "scope_sha256")):
        require(sha(artifacts[name]) == extraction[field], "metadata_hash_drift")
    require(json.loads(artifacts["record.json"]) == record, "record_mismatch")
    scope = json.loads(artifacts["scope.json"])
    require(extraction["inventory"] == scope["required_inventory"] and
            all(type(n) is int and n == 1 for n in extraction["inventory"].values()),
            "incomplete_or_repeated_inventory")
    rows = extraction["rows"]
    require(Counter(row["name"] for row in rows) == Counter(extraction["inventory"]), "row_inventory_mismatch")
    require(all(row["status"] in ("Passed", "Failed") for row in rows), "unknown_unit_status")
    failed = sorted(row["name"] for row in rows if row["status"] == "Failed")
    require(failed, "no_failed_unit")
    require(artifacts["stderr.txt"] == b"", "nonempty_stderr")
    resources = artifacts["resources.txt"].decode("utf-8")
    require(re.findall(r"(?m)^\s*Exit status: (\d+)\s*$", resources) == ["4"] and
            re.findall(r"(?m)^\s*Signals delivered: (\d+)\s*$", resources) == ["0"],
            "resource_completion_record_missing")
    warning = extraction["warning_review"]
    require(warning["no_additional_warnings"] is True and
            warning["upstream_warning_profile_complete"] is True and
            not warning["missing_upstream_warnings"] and not warning["unclassified_warnings"] and
            not warning["operational_warnings"], "warning_profile_differs")
    permitted_warnings = Counter(scope["upstream_warnings"])
    observed_warnings, diagnoses, summaries, result_files = [], [], [], []
    in_diagnostic = False
    for line in artifacts["stdout.txt"].decode("utf-8").splitlines():
        if not line.strip():
            continue
        if line in permitted_warnings:
            observed_warnings.append(line); in_diagnostic = True
            continue
        match = DIAGNOSTIC.fullmatch(line)
        if match:
            path, line_no, column, name = match.groups()
            require(path in extraction["source_sha256"], "diagnostic_source_missing")
            diagnoses.append(dict(file=path, line=int(line_no), column=int(column), unit=name))
            in_diagnostic = True
            continue
        match = SUMMARY.fullmatch(line)
        if match:
            summaries.append(tuple(map(int, match.groups()))); in_diagnostic = False
            continue
        if line.startswith("Results File: "):
            result_files.append(line[len("Results File: "):]); in_diagnostic = False
            continue
        require(in_diagnostic and EXCERPT.fullmatch(line), "unrecognized_stdout_diagnostic")
    require(Counter(observed_warnings) == permitted_warnings, "warning_lines_differ")
    require(len(summaries) == 1 and summaries[0] == (len(rows)-len(failed), len(failed)),
            "resource_summary_count_mismatch")
    require(Counter(d["unit"] for d in diagnoses) == Counter(failed), "failed_unit_diagnostics_mismatch")
    csv_names = sorted(name for name in raw_pins if name.startswith("csv/") and name.endswith(".csv"))
    require(len(csv_names) == len(result_files) == 1 and
            result_files[0] == record["command"][record["command"].index("--pwd")+1] + "/" + csv_names[0][4:],
            "csv_results_path_mismatch")
    return dict(verified_units=len(rows)-len(failed), resource_failed_units=len(failed),
                required_units=len(rows), failed_units=failed, diagnostics=diagnoses,
                extended_summary_matches_csv=True,
                original_parser_count_agreement=extraction["native_flags"]["count_agreement"])


def audit(extraction, artifacts):
    """Return a negative-outcome receipt; a failed check remains terminal."""
    receipt = dict(policy=VERSION, eligible=False, qualified_pass=False,
                   permits_parent=False, changes_original_native_classification=False,
                   source_revision_sha256=extraction.get("source_revision_sha256"),
                   raw_sha256=extraction.get("raw_sha256"))
    try:
        receipt.update(_completed(extraction, artifacts), eligible=True,
                       action="record_unaccepted_block_child_continue_independent_lineages")
    except (ValueError, KeyError, TypeError, UnicodeError, IndexError) as error:
        receipt["reason"] = str(error) if isinstance(error, ValueError) else type(error).__name__
        receipt["action"] = "stop_dispatch"
    return receipt


def attach(extraction, artifacts):
    # Passing evidence must remain byte-exact for the unchanged parent issuer.
    if extraction.get("native_category") == "VERIFIER_RESOURCE_FAILURE":
        return dict(extraction, completed_resource_outcome=audit(extraction, artifacts))
    return extraction
