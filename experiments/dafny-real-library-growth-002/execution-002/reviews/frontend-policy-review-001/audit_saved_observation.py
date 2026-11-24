"""Read-only replay of the old observed failure, not a new native trial."""
import json
from pathlib import Path
import re
import sys

HERE = Path(__file__).resolve().parent
EXECUTION = HERE.parents[1]
PACKAGE = EXECUTION.parent
sys.path.insert(0, str(EXECUTION))
import runtime as rt

used = {}


def read(path):
    path = Path(path)
    data = path.read_bytes()
    used[str(path.relative_to(PACKAGE))] = rt.sha(data)
    return data


def obj(path):
    return json.loads(read(path))


old = PACKAGE / "execution-001"
slot = old / "retrieved-001/model-001/slots/slot-03"
scope_path = obj(old / "runtime-freeze.json")["scope"]
scope = obj(PACKAGE / scope_path)
spec = scope["projects"]["stdlib-splice"]["stages"]["1"]
edit = obj(PACKAGE / spec["edit_profile"])
profile_template = obj(PACKAGE / spec["native_profile"])
base = {name: read(PACKAGE / pin["path"]) for name, pin in spec["base_sources"].items()}
assert rt.native.hashes(base) == edit["base_source_sha256"]
outcome = obj(slot / "outcome.json")
body = read(slot / "body.txt").decode("utf-8")
candidate, guarded = rt.guard.reconstruct(edit, body, base, outcome["chain_id"])
assert rt.canonical(guarded) == rt.canonical(obj(slot / "edit-review.json"))
for name, source in candidate.items():
    assert read(slot / "candidate" / name) == source
    assert read(slot / "native/workspace" / name) == source
profile = obj(slot / "native-profile.json")
assert profile == rt.materialize_profile(profile_template, candidate)
record = obj(slot / "native/record.json")
raw = {path.relative_to(slot / "native/raw").as_posix(): read(path)
       for path in sorted((slot / "native/raw").rglob("*")) if path.is_file()}
for name, data in raw.items():
    if name.startswith("csv/"):
        assert read(slot / "native/workspace" / name[4:]) == data
pins = rt.native.EvidencePins(rt.sha(rt.canonical(profile)), rt.sha(rt.canonical(record)),
    rt.sha(rt.canonical(rt.native.hashes(candidate))), tuple(sorted(rt.native.hashes(raw).items())),
    record["run_id"], "model_candidate")
report = rt.native.review(profile, candidate, record, raw, pins)
assert rt.canonical(report) == rt.canonical(obj(slot / "native-review.json"))
event = obj(slot / "native-dispatch.json")
assert event == obj(slot / "native/event.json")
response_binding = obj(slot / "response-binding.json")
response = obj(old / "retrieved-001/model-001/requests/response-003.json")
assert event["request_id"] == outcome["request_id"] == response_binding["request_id"] == response["request_id"]
assert event["response_sha256"] == rt.sha(rt.canonical(response)) == response_binding["response_sha256"]
assert event["candidate_sha256"] == pins.source_revision_sha256
assert event["profile_sha256"] == pins.profile_sha256
assert record["run_id"] == event["run_id"]
assert response["retry_attempts"] == 0
assert outcome["accepted"] is False and outcome["outcome"] == "TERMINAL_NATIVE_FAILURE"
assert report["category"] == "FRONTEND_RESOLUTION_FAILURE" and not report["qualified_success"]
assert rt.candidate_frontend_failure(report, record, raw, edit["addition"]["path"])
assert rt.nonterminal_native_failure(report, record, raw, edit["addition"]["path"])
for name in ("runtime.py", "run_pilot.py", "review_collection.py", "test_frontend_policy.py"):
    read(EXECUTION / name)
for name in ("guard.py", "review_native.py"):
    read(PACKAGE / "common" / name)
read(Path(__file__))
text = raw["stdout.txt"].decode("utf-8")
errors = re.findall(r"^.*\bError\s*:[^\n]*$", text, re.M)
assert len(errors) == 10
assert all("member 'data' has not been imported in this scope" in line for line in errors)
assert report["warnings"] == 1 and not report["warning_policy_matches"]
assert report["units"] == [] and report["summaries"] == []
assert record["exit_code"] == report["resources"]["exit_status"] == 2
assert record["timeout"] is False and report["resources"]["complete"]
assert all(rt.sha((PACKAGE / name).read_bytes()) == pin for name, pin in used.items())

result = dict(schema="repodisco-frontend-prospective-policy-audit-v1", status="PASS",
    observation="execution-001/retrieved-001/model-001/slots/slot-03",
    run_id=record["run_id"], request_id=response["request_id"], sdk_retries=0,
    native_observations_reused=1, new_native_observations=0, provider_calls=0,
    exact_guard_reconstruction=True, protected_base_preserved=True,
    native_reviewer_replay_exact=True, source_command_tool_raw_pins_match=True,
    exact_current_request_binding=True,
    actual=dict(exit_code=2, timeout=False, complete_resources=True, frontend_errors=10,
        error_lines=errors, warnings=report["warnings"], warning_lines=report["warning_lines"],
        warning_policy_matches=False, logged_proof_units=0, passed_proof_units=0,
        failed_proof_units=0, proof_coverage_complete=False,
        missing_required_units=len(report["missing_units"]),
        elapsed_seconds=record["elapsed_seconds"], max_rss_kib=report["resources"]["max_rss_kib"]),
    original_outcome="TERMINAL_NATIVE_FAILURE", original_accepted=False,
    prospective_policy_result="NATIVE_REJECTED_CONTINUE", prospective_accepted=False,
    historical_result_modified=False, acceptance_issued=False,
    limitations=["This is a read-only prospective-policy replay of saved evidence, not a new run or a historical rescore.",
        "No proof unit was checked for this frontend-rejected candidate; empty coverage is not a pass.",
        "Candidate warnings remain in raw evidence and the review. The success warning policy is unchanged.",
        "Hashes bind evidence relative to the trusted host records; arbitrary receipt JSON is not self-authenticating."],
    input_sha256=dict(sorted(used.items())))
print(json.dumps(result, indent=2, sort_keys=True))
