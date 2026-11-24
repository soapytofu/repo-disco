"""Independent read-only saved-evidence audit; no test or native/provider calls."""
import csv
import hashlib
import io
import json
from pathlib import Path
import re
import sys

HERE = Path(__file__).resolve().parent
EXECUTION = HERE.parents[1]
PACKAGE = EXECUTION.parent
sys.path.insert(0, str(EXECUTION))
import runtime as rt

pins = {}


def read(path):
    path = Path(path)
    data = path.read_bytes()
    pins[str(path.relative_to(PACKAGE))] = rt.sha(data)
    return data


def obj(path):
    return json.loads(read(path))


def archive_check(execution):
    transfer = obj(execution / "transfer-001.json")
    root = execution / "retrieved-001"
    actual = {p.relative_to(root).as_posix(): dict(bytes=p.stat().st_size,
        sha256=hashlib.sha256(p.read_bytes()).hexdigest())
        for p in root.rglob("*") if p.is_file()}
    assert actual == transfer["files"]
    return dict(files=len(actual), all_file_bytes_and_hashes_match=True,
        manifest=str((execution / "transfer-001.json").relative_to(PACKAGE)),
        manifest_sha256=pins[str((execution / "transfer-001.json").relative_to(PACKAGE))])


archives = {"current": archive_check(EXECUTION), "prior": archive_check(PACKAGE / "execution-001")}
scope = obj(EXECUTION / "scope.json")
previous = obj(PACKAGE / "pilot/frozen-001/scope.json")
for field in ("projects", "slots", "settings", "renderer", "max_calls", "independent_trials", "adaptive_expansion"):
    assert scope[field] == previous[field]
freeze_checks = {}
for name in ("execution-001", "execution-002"):
    freeze = obj(PACKAGE / name / "runtime-freeze.json")
    assert all(hashlib.sha256((PACKAGE / path).read_bytes()).hexdigest() == digest
               for path, digest in freeze["files"].items())
    freeze_checks[name] = dict(files=len(freeze["files"]), all_pins_match=True,
        manifest_sha256=pins[name + "/runtime-freeze.json"])

model = EXECUTION / "retrieved-001/model-001"
summary = obj(model / "summary.json")
ledger = obj(model / "requests/ledger.json")
review = obj(EXECUTION / "collection-review-001.json")
assert summary["status"] == "COMPLETE" and summary["fatal"] is None
assert ledger["closed"] and ledger["closed_reason"] == "complete"
assert len(ledger["reservations"]) == summary["reserved"] == summary["completed"] == 8
assert all(row["status"] == "COMPLETED" for row in ledger["reservations"])
assert review["status"] == "PASS_COMPLETE" and review["score"] == {"accepted": 3, "returned_trials": 8}
assert review["full_archive_reviewed"] and review["archive_files"] == archives["current"]["files"]

budget = obj(EXECUTION / "budget-snapshot.json")
prior_budget = obj(EXECUTION / "prior-budget-snapshot.json")
assert budget["allocations"][:-1] == prior_budget["allocations"]
assert budget["previous_snapshot_sha256"] == rt.sha(read(EXECUTION / "prior-budget-snapshot.json"))
assert budget["total_allocated_request_ceiling"] == 44
assert sum(row["maximum_new_requests"] for row in budget["allocations"]) == 44
assert budget["unallocated_request_ceiling"] == 56
assert budget["closed_unused_slots_total"] == prior_budget["closed_unused_slots_total"] == 14
claim = obj(EXECUTION / "retrieved-001/canonical-allocation-claim.json")
authorization = obj(EXECUTION / "retrieved-001/authorization.json")
assert claim["state"] == "CONSUMED_NO_RESUME"
assert claim["authorization_sha256"] == rt.sha(read(EXECUTION / "retrieved-001/authorization.json"))
assert authorization["max_new_calls"] == 8 and all(authorization[x] for x in ("no_retry", "no_resume", "no_reassignment"))
assert authorization["runtime_manifest_sha256"] == freeze_checks["execution-002"]["manifest_sha256"]
assert authorization["scope_sha256"] == rt.sha(read(EXECUTION / "scope.json"))
assert read(EXECUTION / "budget-snapshot.json") == read(EXECUTION / "retrieved-001/canonical-budget-snapshot.json")
assert claim["execution_binding"]["allocation_id"] == "dafny-varied-growth-8-002"
assert prior_budget["allocations"][-1]["execution_id"] == "dafny-varied-growth-8-001"
old_review = PACKAGE / "execution-001/collection-review-001.json"
assert rt.sha(read(old_review)) == prior_budget["allocations"][-1]["collection_review_sha256"]
assert obj(old_review)["score"] is None

rows, ids = [], []
tokens = dict(inputTokens=0, outputTokens=0, totalTokens=0)
payload_pins = {}
for number, slot in enumerate(scope["slots"], 1):
    folder = model / "slots" / slot["id"]
    outcome = obj(folder / "outcome.json")
    assert outcome == summary["rows"][number - 1]
    spec = scope["projects"][slot["project"]]["stages"]["1"]
    profile = obj(folder / "native-profile.json")
    edit = obj(PACKAGE / spec["edit_profile"])
    body = read(folder / "body.txt").decode()
    base = {name: read(PACKAGE / item["path"]) for name, item in spec["base_sources"].items()}
    candidate, edit_replay = rt.guard.reconstruct(edit, body, base, slot["chain_id"])
    assert rt.canonical(edit_replay) == rt.canonical(obj(folder / "edit-review.json"))
    assert profile == rt.materialize_profile(obj(PACKAGE / spec["native_profile"]), candidate)
    for name, data in candidate.items():
        assert data == read(folder / "candidate" / name) == read(folder / "native/workspace" / name)
    payload_path = PACKAGE / spec["exact_payload_path"]
    payload = obj(payload_path)
    payload_pins[slot["project"]] = rt.sha(read(payload_path))
    prompt = obj(folder / "prompt.json")
    assert prompt["payload"] == payload == ledger["reservations"][number - 1]["prompt"]
    assert prompt["payload_sha256"] == rt.sha(rt.canonical(payload))
    assert read(payload_path) == read(EXECUTION / "retrieved-001/package" / spec["exact_payload_path"])
    response = obj(model / "requests" / ("response-%03d.json" % number))
    assert response["text"] == "".join(item.get("text", "") for item in response["content"])
    assert response["content"] == response["raw_response"]["output"]["message"]["content"]
    metadata = response["raw_response"]["ResponseMetadata"]
    assert metadata["RequestId"] == response["request_id"] == outcome["request_id"]
    assert metadata["RetryAttempts"] == response["retry_attempts"] == 0
    assert metadata["HTTPStatusCode"] == 200
    assert rt.parse_body_receipt(response["text"])[0] == body
    ids.append(response["request_id"])
    for field in tokens:
        assert response["usage"][field] == response["raw_response"]["usage"][field]
        tokens[field] += response["usage"][field]
    record = obj(folder / "native/record.json")
    event = obj(folder / "native-dispatch.json")
    assert event == obj(folder / "native/event.json")
    assert event["request_id"] == response["request_id"] and event["request_sequence"] == number
    assert event["response_sha256"] == rt.sha(rt.canonical(response))
    assert event["candidate_sha256"] == rt.sha(rt.canonical(rt.native.hashes(candidate)))
    assert record["source_before_sha256"] == record["source_after_sha256"] == rt.native.hashes(candidate)
    assert record["toolchain"] == record["toolchain_after"] == profile["toolchain"]
    assert record["argv"] == profile["command"]
    assert record["argv"][-len(candidate):] == profile["verification_inputs"]
    assert set(candidate) == set(profile["verification_inputs"])
    assert record["attempts"] == 1 and not record["timeout"] and record["model_calls"] == 0
    assert record["host"]["job_id"] == "63440248" and record["host"]["cpus_per_task"] == 1
    assert record["origin"] == "model_candidate" and record["run_id"] == event["run_id"]
    raw = {path.relative_to(folder / "native/raw").as_posix(): read(path)
           for path in sorted((folder / "native/raw").rglob("*")) if path.is_file()}
    assert record["raw_sha256"] == rt.native.hashes(raw)
    assert raw["stderr.txt"] == b""
    report = obj(folder / "native-review.json")
    actual_units = []
    for name, data in raw.items():
        if name.startswith("csv/"):
            assert read(folder / "native/workspace" / name[4:]) == data
            csv_reader = csv.DictReader(io.StringIO(data.decode()))
            assert csv_reader.fieldnames == profile["csv_columns"]
            actual_units.extend(list(csv_reader))
    units = {row["TestResult.DisplayName"]: row for row in actual_units}
    assert len(units) == len(actual_units)
    assert {name: row["TestResult.Outcome"] for name, row in units.items()} == {
        row["name"]: row["outcome"] for row in report["units"]}
    assert all(entry["counted_as_pass"] is False for entry in profile["unlogged_definitions"])
    assert set(profile["required_units"].values()) | set(profile["unitless_files"]) == set(candidate)
    text = raw["stdout.txt"].decode()
    errors = re.findall(r"^.*\bError\s*:[^\n]*$", text, re.M)
    assert not re.search(r"\bWarning:", text) and report["warnings"] == 0
    resources = rt.native._resources(raw["resources.txt"])
    assert resources == report["resources"] and resources["complete"]
    assert resources["exit_status"] == record["exit_code"]
    assert outcome["accepted"] == report["qualified_success"]
    if outcome["accepted"]:
        assert record["exit_code"] == 0 and not errors
        assert set(units) == set(profile["required_units"])
        assert all(row["TestResult.Outcome"] == "Passed" for row in actual_units)
        assert report["category"] == "VERIFIED" and report["proof_coverage_complete"]
        assert all(units[name]["TestResult.Outcome"] == "Passed" for name in profile["actual_target_units"])
    elif number == 7:
        assert record["exit_code"] == 4 and report["category"] == "RESOURCE_FAILURE"
        assert set(units) == set(profile["required_units"]) and report["proof_coverage_complete"]
        bad = [row for row in actual_units if row["TestResult.Outcome"] != "Passed"]
        assert len(bad) == 1 and bad[0]["TestResult.DisplayName"] == "RepoDiscoFrameBatch.ReadCountedFrames (well-formedness)"
        assert bad[0]["TestResult.Outcome"] == "Failed" and int(bad[0]["TestResult.ResourceCount"]) == 500057327
        assert "80 verified, 0 errors, 1 out of resource" in text
        assert rt.nonterminal_native_failure(report, record, raw, edit["addition"]["path"])
    else:
        assert number in (1, 3, 6, 8) and record["exit_code"] == 2
        assert report["category"] == "FRONTEND_RESOLUTION_FAILURE" and not actual_units
        assert len(errors) == {1: 11, 3: 2, 6: 1, 8: 6}[number]
        expected_error = "member 'data' has not been imported" if number in (1, 8) else "allowed only in specification contexts"
        assert all(expected_error in line for line in errors)
        assert rt.candidate_frontend_failure(report, record, raw, edit["addition"]["path"])
    assert outcome["outcome"] == ("ACCEPTED" if outcome["accepted"] else "NATIVE_REJECTED")
    rows.append(dict(slot_id=slot["id"], project=slot["project"], accepted=outcome["accepted"],
        category=report["category"], exit_code=record["exit_code"], warnings=report["warnings"],
        error_diagnostics=errors, logged_units=len(actual_units), passed_units=report["passed_units"],
        csv_failed_units=report["failed_units"], proof_coverage_complete=report["proof_coverage_complete"],
        explicit_unlogged_definitions=len(profile["unlogged_definitions"]),
        protected_base_files=len(base), guarded_source_reconstruction_exact=True,
        full_source_command_tool_raw_pins_match=True, prompt_equals_original_frozen_payload=True,
        request_id=response["request_id"], body_sha256=rt.sha(body.encode()),
        elapsed_seconds=record["elapsed_seconds"], max_rss_kib=resources["max_rss_kib"]))

assert len(set(ids)) == 8 and sum(row["accepted"] for row in rows) == 3
assert tokens == review["tokens_from_saved_responses"] == dict(inputTokens=69626, outputTokens=4264, totalTokens=73890)
accounting = read(EXECUTION / "retrieved-001/accounting.txt").decode()
assert "63440248|COMPLETED|00:04:25|265|0:0|1|" in accounting
assert "308056K" in accounting
for name in ("runtime.py", "run_pilot.py", "review_collection.py"):
    read(EXECUTION / name)
for name in ("guard.py", "review_native.py"):
    read(PACKAGE / "common" / name)
read(Path(__file__))
assert all(rt.sha((PACKAGE / name).read_bytes()) == digest for name, digest in pins.items())

result = dict(schema="repodisco-independent-collection-audit-v1", status="PASS", blocking_findings=[],
    job_id="63440248", new_native_or_provider_calls=0, tests_run=0, acceptance_issued=False,
    score=dict(accepted=3, returned_trials=8), unique_request_ids=8, sdk_retries=0,
    native_resolution_rejections=4, closed_native_resource_rejections=1,
    ordinary_mathematical_proof_failure_observations=0, tokens=tokens, rows=rows,
    per_task=summary["per_task"], full_archive_identity=archives, frozen_runtime_identity=freeze_checks,
    same_task_specifications_settings_order_and_payloads=True, original_payload_sha256=payload_pins,
    previous_cohort=dict(runtime_files_unchanged=54, archive_files_unchanged=398,
        full_cohort_score=None, five_unused_slots_remain_closed=True),
    budget=dict(prior_allocations_preserved=4, fresh_allocation=8, allocated_ceiling=44,
        total_ceiling=100, unallocated_ceiling=56, prior_actual_requests=22,
        current_actual_requests=8, cumulative_actual_requests=30, old_closed_unused_slots=14,
        claim_consumed_no_resume=True, existing_slots_reassigned=False),
    presentation_claims=["Fresh balanced cohort: 3/8 verified additions on four selected-component tasks, two responses each.",
        "All eight outputs passed extraction and the edit guard. Dafny then rejected four for module visibility or ghost/executable typing; one exhausted the frozen solver resource limit.",
        "Three AWS-derived decoder additions verified with the complete pinned source and proof inventory: counted frames 1/2; tagged bounded pair 2/2.",
        "The continuation policy retained frontend failures while completing all eight independent requests without retries or relaxed success criteria."],
    limitations=["Selected dependency-closed components of two real repositories; not complete upstream repository verification or unrestricted repository generation.",
        "Four fixed development tasks with two responses each; no held-out, causal, cross-model or population-success claim.",
        "A solver resource failure is an unresolved bounded verification outcome, not evidence that the program is mathematically incorrect.",
        "Frontend-rejected candidates checked zero proof units. Their functional correctness remains unassessed.",
        "This is native verification of executable Dafny additions, not a compilation/runtime benchmark.",
        "The prior partial cohort remains separate; a fresh cohort with a different continuation policy is not a rescore or a repair of its saved candidates.",
        "Accepted tagged-pair samples have closely related implementations, so 3 accepted responses do not mean 3 independent task designs."],
    reviewed_input_sha256=dict(sorted(pins.items())))
print(json.dumps(result, sort_keys=True, indent=2))
