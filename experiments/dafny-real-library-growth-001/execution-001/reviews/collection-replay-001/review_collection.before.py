"""Offline audit of job 63153129's archived twelve-response collection.

Replays the frozen guard, renderer and native evidence reviewer. No verifier,
provider, credential, SSH, acceptance issuance or model execution is available.
The archive came from the root-owned submission; hashes establish identity
within that provenance, not authenticity of arbitrary third-party receipts.
"""
import json
from pathlib import Path
import sys

HERE = Path(__file__).resolve().parent
ARCHIVE = HERE / "retrieved-001"
PACKAGE = ARCHIVE / "package"
EXPECTED_RUNTIME = "69d07a07241982e21bf06cf16ed038187c8fd2d2a7fff1e71443515745f49548"
sys.path.insert(0, str(PACKAGE / "execution-001"))
import runtime as rt
import ops
from build_runtime import validate_complete


def check(value, message):
    if not value:
        raise ValueError(message)


def review():
    transfer = rt.read_json(HERE / "transfer-001.json")
    check(transfer["job_id"] == "63153129", "Wrong archive job")
    check(rt.sha((HERE / "transfer-001.tar.gz").read_bytes()) == transfer["archive_sha256"], "Archive bytes changed")
    actual = rt.file_snapshot(ARCHIVE)
    expected = {name: data["sha256"] for name, data in transfer["files"].items()}
    check(actual == expected, "Full archive inventory differs")
    freeze, scope, stages = validate_complete(PACKAGE, "pilot/draft-002/scope.json",
        PACKAGE / "execution-001/runtime-freeze.json", EXPECTED_RUNTIME)
    for name, digest in freeze["files"].items():
        check(rt.sha((HERE.parent / name).read_bytes()) == digest, "Local frozen input drift")
    accounting = ops.terminal_accounting((ARCHIVE / "accounting.txt").read_text(), "63153129")
    check(all(row["normalized_state"] == "COMPLETED" for row in accounting["rows"]), "Non-complete scheduler state")
    submission = rt.read_json(ARCHIVE / "submissions/model.json")
    check(submission == rt.read_json(HERE / "submissions/model.json"), "Submission changed")
    check(submission["submission_attempts"] == 1 and submission["resources"] ==
          dict(cpus=1, memory_gb=4, seconds=10800, no_requeue=True), "Wrong resources/submission count")
    check("PreemptMode=OFF" in submission["partition_record"] and "State=UP" in submission["partition_record"], "Partition was not qualified")
    model = ARCHIVE / "model-001"
    summary = rt.read_json(model / "summary.json")
    ledger = rt.read_json(model / "requests/ledger.json")
    run = rt.read_json(model / "run.json")
    check(summary["status"] == "COMPLETE" and summary["synthetic"] is False and summary["fatal"] is None, "Unexpected cohort status")
    check(run["run_id"] == summary["run_id"] and run["offline"] is False, "Synthetic/foreign run")
    check(ledger["closed"] is True and ledger["closed_reason"] == "complete" and ledger["limit"] == 12, "Ledger not closed")
    check(len(ledger["reservations"]) == 12 and len(summary["rows"]) == 12, "Incomplete accounting")
    check(rt.read_json(model / "authorization.json") == rt.read_json(ARCHIVE / "authorization.json") == rt.read_json(HERE / "authorization.json"), "Authorization differs")
    check((model / "allocation-claim.json").read_bytes() == (ARCHIVE / "canonical-allocation-claim.json").read_bytes(), "Claim differs")
    check((model / "budget-snapshot.json").read_bytes() == (ARCHIVE / "canonical-budget-snapshot.json").read_bytes() == (HERE / "budget-snapshot.json").read_bytes(), "Budget differs")
    auth = rt.read_json(model / "authorization.json")
    check(auth["runtime_manifest_sha256"] == EXPECTED_RUNTIME and auth["scope_sha256"] == rt.sha((PACKAGE / freeze["scope"]).read_bytes()), "Authorization freeze differs")
    claim = rt.read_json(ARCHIVE / "canonical-allocation-claim.json")
    check(claim["state"] == "CONSUMED_NO_RESUME" and claim["execution_binding"] == scope["execution_binding"] and
          claim["runtime_manifest_sha256"] == EXPECTED_RUNTIME and claim["authorization_sha256"] == rt.sha((model / "authorization.json").read_bytes()) and
          claim["scope_sha256"] == auth["scope_sha256"] and claim["scope_canonical_sha256"] == rt.sha(rt.canonical(scope)), "Canonical allocation identity differs")
    check(claim["budget_counts"] == dict(total_allocated=28, total_ceiling=100, current_allocation=12, prior_allocated=16, remaining_unallocated=72), "Allocation budget differs")
    renderer = rt.load_renderer(PACKAGE, scope["renderer"])
    parents, rows, ids, nonces = {}, [], set(), set()
    totals = dict(inputTokens=0, outputTokens=0, totalTokens=0)
    for index, slot in enumerate(scope["slots"], 1):
        folder = model / "slots" / slot["id"]
        row = rt.read_json(folder / "outcome.json")
        check(row == summary["rows"][index - 1] and all(row[k] == v for k, v in slot.items()), "Slot/summary differs")
        check(row["outcome"] == "ACCEPTED" and row["accepted"] is True and row["request_sequence"] == index, "Expected reviewed success missing")
        reservation = ledger["reservations"][index - 1]
        check(reservation["sequence"] == index and reservation["status"] == "COMPLETED" and reservation["task_id"] == slot["id"], "Reservation mismatch")
        check(reservation["attempt_id"] == run["run_id"] + ":" + slot["id"], "Foreign attempt")
        check(auth["created_at_epoch"] <= reservation["reserved_at_epoch"] <= reservation["dispatch_started_at_epoch"] < auth["expires_at_epoch"], "Dispatch outside authorization")
        response = rt.read_json(model / "requests" / ("response-%03d.json" % index))
        metadata = response["raw_response"]["ResponseMetadata"]
        check(response["request_id"] == metadata["RequestId"] == row["request_id"] and response["request_id"] not in ids, "Request ID mismatch/duplicate")
        ids.add(response["request_id"])
        check(response["retry_attempts"] == metadata["RetryAttempts"] == 0 and metadata["HTTPStatusCode"] == 200, "Provider retry or failed response")
        check(response["content"] == response["raw_response"]["output"]["message"]["content"] and
              response["text"] == "".join(block["text"] for block in response["content"] if "text" in block), "Raw provider text differs")
        check(response["usage"] == response["raw_response"]["usage"] and response["stop_reason"] == "end_turn", "Usage/truncation mismatch")
        for key in totals:
            value = response["usage"][key]
            check(type(value) is int and value >= 0, "Invalid token count")
            totals[key] += value
        check(rt.sha(rt.canonical(response)) == row["response_sha256"], "Response digest differs")
        binding = rt.read_json(folder / "response-binding.json")
        check(binding == {k: row[k] for k in ("request_sequence", "request_id", "response_sha256")}, "Response binding differs")
        stage = stages[(slot["project"], slot["stage"])]
        key = (slot["project"], slot["chain_id"])
        sources, evidence = (dict(stage.base_sources), None) if slot["stage"] == 1 else parents[key]
        rendered = (renderer.render_stage1(slot["project"], slot["chain_id"], root=PACKAGE)
            if slot["stage"] == 1 else renderer.render_stage2(slot["project"], slot["chain_id"], sources, evidence, root=PACKAGE))
        check(rendered == rt.read_json(folder / "prompt.json") and rendered["payload"] == reservation["prompt"], "Exact prompt/parent replay differs")
        body, envelope = rt.parse_body_receipt(response["text"])
        check(body.encode() == (folder / "body.txt").read_bytes() and envelope == rt.read_json(folder / "envelope.json"), "Response extraction differs")
        candidate, edit = rt.guard.reconstruct(stage.edit_profile, body, sources, slot["chain_id"], parent=evidence)
        check(candidate == rt.source_files(folder / "candidate") == rt.source_files(folder / "native/workspace"), "Guarded/native source differs")
        check(edit == rt.read_json(folder / "edit-review.json"), "Edit receipt differs")
        profile = rt.materialize_profile(stage.native_profile, candidate)
        check(profile == rt.read_json(folder / "native-profile.json"), "Materialized native policy differs")
        record = rt.read_json(folder / "native/record.json")
        raw = {p.relative_to(folder / "native/raw").as_posix(): p.read_bytes() for p in (folder / "native/raw").rglob("*") if p.is_file()}
        event = rt.read_json(folder / "native-dispatch.json")
        check(event == rt.read_json(folder / "native/event.json") and event["nonce"] not in nonces, "Native event reused/changed")
        nonces.add(event["nonce"])
        check(event["request_id"] == row["request_id"] and event["response_sha256"] == row["response_sha256"] and event["payload_sha256"] == rendered["payload_sha256"], "Fresh native request provenance differs")
        check(event["candidate_sha256"] == rt.sha(rt.canonical(rt.native.hashes(candidate))) and event["profile_sha256"] == rt.sha(rt.canonical(profile)), "Native candidate event differs")
        check(record["origin"] == "model_candidate" and record["run_id"] == event["run_id"] == run["run_id"] + ":" + slot["id"], "Native origin/run differs")
        check(record["host"]["job_id"] == "63153129" and record["host"]["partition"] == "test" and record["host"]["cpus_per_task"] == 1 and "login" not in record["host"]["hostname"], "Native compute provenance differs")
        pins = rt.native.EvidencePins(rt.sha(rt.canonical(profile)), rt.sha(rt.canonical(record)),
            rt.sha(rt.canonical(rt.native.hashes(candidate))), tuple(sorted(rt.native.hashes(raw).items())), record["run_id"], "model_candidate")
        reviewed = rt.native.review(profile, candidate, record, raw, pins)
        check(reviewed == rt.read_json(folder / "native-review.json") and reviewed["qualified_success"] and reviewed["strict_zero_warning_success"], "Native replay failed")
        check(record["attempts"] == 1 and not record["timeout"] and record["exit_code"] == 0, "Native retries or failure")
        expected_units = {("stdlib", 1): 58, ("stdlib", 2): 60, ("aws", 1): 75, ("aws", 2): 77}
        check(reviewed["passed_units"] == expected_units[(slot["project"], slot["stage"])], "Wrong required inventory")
        if slot["stage"] == 1:
            receipt = rt.read_json(folder / "parent-receipt.json")
            check(receipt["request_id"] == row["request_id"] and receipt["slot_id"] == slot["id"] and receipt["host_run_id"] == run["run_id"] and receipt["synthetic"] is False, "Parent request provenance differs")
            check(receipt["native_event_sha256"] == rt.sha(rt.canonical(event)), "Parent native event differs")
            evidence = rt.guard.ParentEvidence(profile, record, raw, pins, receipt, rt.sha(rt.canonical(receipt)))
            parents[key] = (candidate, evidence)
        rows.append(dict(slot_id=slot["id"], project=slot["project"], stage=slot["stage"], chain_id=slot["chain_id"],
            request_id=row["request_id"], body_sha256=rt.sha(body.encode()), source_revision_sha256=reviewed["source_revision_sha256"],
            passed_units=reviewed["passed_units"], unlogged_definitions=len(reviewed["unlogged_definitions"]),
            elapsed_seconds=reviewed["elapsed_seconds"], usage=response["usage"], parent_source_preserved=slot["stage"] == 2,
            actual_native_host=record["host"], resources=reviewed["resources"]))
    pilot = rt.read_json(model / "pilot-continuation.json")
    check(pilot["complete_accounting"] and pilot["accepted_first_stages"] == 2 and pilot["continue_expansion"] and not pilot["infrastructure_failure"], "Pilot continuation differs")
    for ident, snapshot in pilot["artifacts"].items():
        check(rt.file_snapshot(model / "slots" / ident) == snapshot, "Pilot evidence changed after continuation")
    check(totals["inputTokens"] + totals["outputTokens"] == totals["totalTokens"], "Token sum differs")
    return dict(schema="dafny-library-model-collection-review-v1", job_id="63153129", status="PASS", runtime_sha256=EXPECTED_RUNTIME,
        archive_files=len(actual), request_count=12, unique_request_ids=len(ids), sdk_retries=0, ambiguous_requests=0,
        accepted_additions=12, completed_lineages=6, exact_child_parent_replays=6, parser_guard_admissions=12,
        fresh_native_observations=12, warnings=0, failed_units=0, tokens=totals, rows=rows,
        primary_score_changed=False, native_or_provider_calls_in_review=0, acceptance_issued=False,
        accounting=accounting, review_code_sha256=rt.sha(Path(__file__).read_bytes()))


if __name__ == "__main__":
    result = review()
    destination = HERE / "collection-review-001.json"
    with destination.open("x") as stream:
        json.dump(result, stream, indent=2, sort_keys=True)
        stream.write("\n")
    print(json.dumps({k: v for k, v in result.items() if k not in {"rows", "accounting"}}, indent=2))
