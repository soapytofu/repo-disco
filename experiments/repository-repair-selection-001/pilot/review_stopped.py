"""Offline audit of the archived first-request timeout; never a proof score.

This separate reviewer preserves the completed-batch reviewer and raw archives.
It accepts only the observed terminal-incomplete shape: the published first32
records, one ambiguous new dispatch, and no new response, candidate, or verifier
run. It imports only pinned existing audit helpers and archived validation code.
"""
import argparse
from datetime import datetime
import json
from pathlib import Path
import re

import review_results as q

COMPLETED_REVIEWER_SHA = "3995e809dde69efc9ac25ab94b9270f32ff964955bacfba2fcac04529dd65545"
COMPLETED_TESTS_SHA = "3e78e87fea63ada3301474fe9dc59ad34ef11e95b02de45058a777135b62f5fd"
ERROR = "ReadTimeoutError"
GLOBAL_RESERVED = 33
NEW_RESERVED = 1


def audit_archive(root):
    out, window = root / "model-001", root / "window-evidence-001"
    q.require(q.sha(Path(q.__file__)) == COMPLETED_REVIEWER_SHA, "Completed reviewer was changed")
    q.require(q.sha(q.ROOT / "test_review_results.py") == COMPLETED_TESTS_SHA, "Completed reviewer tests were changed")
    q.require(not (out / "completion.json").exists(), "Stopped batch cannot have a completion receipt")
    actual = {"model-001/" + n: h for n, h in q.inventory(out).items()}
    actual.update({"window-evidence-001/" + n: h for n, h in q.inventory(window).items()})
    transfer = q.load(root / "transfer-001.json")
    q.require(actual == q.checked_pins(transfer["files"], "Transfer"), "Transfer inventory differs")
    q.require(q.DIGEST.fullmatch(transfer["archive_sha256"]) and transfer["compressed_bytes"] > 0,
              "Missing transfer archive metadata")
    snapshot = q.load(window / "snapshot-manifest.json")
    pins = dict(actual)
    pins.pop("window-evidence-001/snapshot-manifest.json")
    q.require(snapshot == dict(archive_kind="terminal-incomplete-no-score", batch_id=q.BATCH,
              credential_access=False, files=pins, session_still_running=False, utc=snapshot["utc"]),
              "Stopped snapshot metadata differs")
    when = datetime.fromisoformat(snapshot["utc"])
    q.require(when.tzinfo is not None, "Snapshot time requires a timezone")
    return out, window, snapshot, transfer, actual


def audit_admission(out, window, runtime, trials, previous_admission):
    admission = q.load(out / "admission.json")
    q.require(q.sha(out / "admission.json") == q.ADMISSION_SHA, "Reviewed admission differs")
    pins = {"frozen-001/" + n: h for n, h in q.inventory(out / "frozen-001").items()}
    pins.update({"inputs/" + n: h for n, h in q.inventory(out / "inputs").items()})
    pins.update({n: q.sha(out / n) for n in ("batch-binding.json", "runtime-freeze.json")})
    expected = dict(schema="repodisco-session-descriptor-v1", sequence=2,
        previous_descriptor_sha256=q.PREVIOUS_ADMISSION_SHA, batch_id=q.BATCH, handler_id="repair-v1",
        handler_binding_sha256=q.digest(q.canonical(runtime["runtime_sha256"])), artifact_directory=q.BATCH,
        freeze_path="frozen-001/freeze.json", freeze_sha256=q.PROPOSAL_SHA,
        runtime_path="runtime-freeze.json", runtime_sha256=q.RUNTIME_SHA, input_sha256=pins,
        slots=[dict(trial_id=t["trial_id"], request_path="frozen-001/" + t["request_path"],
                    request_sha256=t["request_sha256"]) for t in trials], max_calls=q.CALLS, sdk_total_max_attempts=1)
    q.require(admission == expected, "Frozen input, order, or admission binding differs")
    queue = {"0001-" + q.PREVIOUS_BATCH + ".json": q.PREVIOUS_ADMISSION_SHA,
             "0002-" + q.BATCH + ".json": q.ADMISSION_SHA}
    q.require(q.inventory(window / "session/queue") == queue, "Queue chain differs")
    q.require(q.load(window / "session/queue" / ("0001-" + q.PREVIOUS_BATCH + ".json")) == previous_admission,
              "Predecessor descriptor changed")
    q.require(q.inventory(window / "admissions") == {"000001.json": q.PREVIOUS_ADMISSION_SHA,
              "000002.json": q.ADMISSION_SHA}, "Admission snapshot differs")
    q.require(q.inventory(window / "completions") == {q.PREVIOUS_BATCH + ".json": q.PREVIOUS_COMPLETION_SHA},
              "Only the predecessor has a completion receipt")
    manifest = {k: admission[k] for k in ("batch_id", "freeze_sha256", "runtime_sha256", "max_calls", "sdk_total_max_attempts")}
    manifest["slots"] = [{k: slot[k] for k in ("trial_id", "request_sha256")} for slot in admission["slots"]]
    return manifest


def audit_events(window, snapshot, prior):
    pins = q.inventory(window / "session/events")
    q.require(list(pins) == [f"{i:05}.json" for i in range(1, len(pins) + 1)], "Session event sequence incomplete")
    old = q.inventory(q.PREVIOUS_ROOT / "window-evidence-001/session/events")
    q.require(all(pins.get(n) == h for n, h in old.items()), "Published predecessor events changed")
    events = [q.load(window / "session/events" / n) for n in pins]
    q.require(len(events) == len(old) + 3, "Unexpected post-predecessor event history")
    tail = events[len(old):]
    q.require([(e["phase"], e["reason"], e["active_batch_id"], e["window_reservations"]) for e in tail] ==
              [("idle", "descriptor_published", None, 32), ("running", "batch_started", q.BATCH, 32),
               ("error", "terminal_execution_error", q.BATCH, 33)], "Terminal event sequence differs")
    expected_queue = [dict(sequence=1, batch_id=q.PREVIOUS_BATCH, descriptor_sha256=q.PREVIOUS_ADMISSION_SHA),
                      dict(sequence=2, batch_id=q.BATCH, descriptor_sha256=q.ADMISSION_SHA)]
    previous_time, previous_count = q.START, 0
    for i, event in enumerate(events, 1):
        timestamp = q.finite(event["at_epoch"], "event time")
        q.require(event["schema"] == "repodisco-session-status-v1" and event["event_sequence"] == i
                  and event["deadline_epoch"] == q.DEADLINE and timestamp >= previous_time
                  and previous_count <= event["window_reservations"] <= GLOBAL_RESERVED,
                  "Incoherent session event")
        previous_time, previous_count = timestamp, event["window_reservations"]
    for event in tail:
        q.require(event["completed_batch_ids"] == [q.PREVIOUS_BATCH] and event["queued"] == expected_queue,
                  "Second batch completion or queue drift was recorded")
    status = events[-1]
    q.require(q.load(window / "session/status.json") == status and status.get("error_type") == ERROR,
              "Terminal status/error differs")
    q.require(datetime.fromisoformat(snapshot["utc"]).timestamp() >= status["at_epoch"], "Snapshot predates error")
    owner = q.load(window / "session/owner.json")
    q.require(owner == q.load(window / "budget/research-session.lock/owner.json")
              == q.load(q.PREVIOUS_ROOT / "window-evidence-001/session/owner.json"), "Coordinator ownership changed")
    q.require(owner["pid"] == prior["owner_session"]["pid"] and owner["scope_sha256"] == prior["scope_sha256"],
              "Coordinator/global owner mismatch")
    q.require(q.load(window / "budget/owner.lock/owner.json") == prior["owner_session"], "Global owner lock changed")
    return status


def audit_global(window, scope, manifest, trials, prior, previous_receipt, status):
    ledger = q.load(window / "budget/ledger.json")
    q.require(ledger["schema"] == "repodisco-window-budget-v1" and ledger["scope"] == scope
              and ledger["scope_sha256"] == q.digest(q.canonical(scope)), "Global scope differs")
    q.require(ledger["terminal_reason"] == "transport_or_persistence_failure", "Global gate did not stop")
    q.require(ledger["owner_session"] == prior["owner_session"], "Global owner changed")
    q.require(ledger["batches"] == prior["batches"] + [dict(manifest=manifest,
              manifest_sha256=q.digest(q.canonical(manifest)))], "Declared allocations changed")
    q.require(sum(x["manifest"]["max_calls"] for x in ledger["batches"]) == 64, "Declared calls differ")
    rows = ledger["reservations"]
    q.require(len(rows) == GLOBAL_RESERVED and rows[:32] == prior["reservations"],
              "Published predecessor or new reservation count changed")
    names = {f"{kind}-{i:03}.json" for i in range(1, 33) for kind in ("request", "response")}
    names.add("request-033.json")
    q.require(set(q.inventory(window / "budget/requests")) == names, "Unexpected returned or additional request evidence")
    old_requests = q.PREVIOUS_ROOT / "window-evidence-001/budget/requests"
    for name, digest in q.inventory(old_requests).items():
        q.require(q.sha(window / "budget/requests" / name) == digest, "Published predecessor request/response changed")
    ids = []
    for i, row in enumerate(rows[:32], 1):
        request = window / "budget/requests" / f"request-{i:03}.json"
        response_path = window / "budget/requests" / f"response-{i:03}.json"
        response = q.load(response_path)
        q.require(row["status"] == "COMPLETED" and row["sequence"] == i
                  and row["request_sha256"] == q.sha(request) and row["response_sha256"] == q.sha(response_path),
                  "Published predecessor slot bindings differ")
        q.require(row["request_id"] == response["request_id"] and response["request_id"] not in ids
                  and response["retry_attempts"] == 0, "Published predecessor ID/retry evidence differs")
        ids.append(response["request_id"])
    q.require(previous_receipt["request_ids"] == ids, "Predecessor completion IDs differ")
    last, first = rows[-1], trials[0]
    expected_keys = {"sequence", "batch_id", "trial_id", "manifest_sha256", "request_sha256",
                     "reserved_at_epoch", "dispatch_intent_at_epoch", "status", "error_type"}
    q.require(set(last) == expected_keys and last["sequence"] == 33 and last["batch_id"] == q.BATCH
              and last["trial_id"] == first["trial_id"] and last["status"] == "AMBIGUOUS_OR_UNSAVED"
              and last["error_type"] == ERROR and last["manifest_sha256"] == q.digest(q.canonical(manifest))
              and last["request_sha256"] == first["request_sha256"], "Ambiguous slot identity differs")
    q.require(q.START <= q.finite(last["reserved_at_epoch"], "reservation")
              <= q.finite(last["dispatch_intent_at_epoch"], "dispatch") < q.DEADLINE
              and last["dispatch_intent_at_epoch"] <= status["at_epoch"], "Dispatch time is outside scope")
    return ledger, last


def audit_initial_revision(folder, initial, base, task):
    store = folder / "store"
    revision = initial["revision"]
    q.require(isinstance(revision, str) and q.REVISION.fullmatch(revision), "Initial revision identity differs")
    manifest = dict(task_id=task["task_id"], entry=task["entry"], editable=task["editable_files"],
        dependencies={n: re.findall(r'^include "([^"]+)"', b.decode(), re.M) for n, b in base.items()})
    target = store / "revisions" / revision
    q.require(q.source_files(target / "files") == base and q.load(target / "revision.json") ==
              dict(revision=revision, parent=None, manifest=manifest, source_sha256=q.hashes(base), verification=None),
              "Original revision, source, or contracts changed")
    q.require(q.load(store / "HEAD.json") == dict(revision=revision), "Initial HEAD was promoted or changed")
    q.require({p.name for p in (store / "revisions").iterdir()} == {revision}, "Unexpected extra revision")
    q.optional_empty_directory(store / "attempts")
    q.require((store / "write.lock").read_bytes() == b"", "Unexpected store writer evidence")
    expected = {"HEAD.json", "write.lock", "revisions/" + revision + "/revision.json"}
    expected.update("revisions/" + revision + "/files/" + n for n in base)
    q.require(set(q.inventory(store)) == expected, "Unexpected store or attempt artifacts")
    return revision


def audit_attempt(out, window, trials, runtime, global_slot):
    first = trials[0]
    parent, task, base, _ = runtime.parent_parts(out, first)
    folder = out / first["trial_id"]
    q.require({p.name for p in out.iterdir() if p.name.startswith("repair-selection-")} == {first["trial_id"]},
              "Undispatched trial artifacts exist")
    q.require({p.name for p in folder.iterdir()} == {"initial.json", "request.json", "result.json", "store", "task.json", "trial.json"},
              "Stopped attempt has response, candidate, verifier, or unexpected artifacts")
    q.require(q.load(folder / "trial.json") == first and q.load(folder / "task.json") == task, "Trial/task drift")
    frozen_request = out / "frozen-001" / first["request_path"]
    payload = q.load(frozen_request)
    q.require(q.sha(folder / "request.json") == first["request_sha256"]
              and (folder / "request.json").read_bytes() == frozen_request.read_bytes()
              == (window / "budget/requests/request-033.json").read_bytes(), "Exact dispatch request differs")
    q.require(set(payload) == {"modelId", "system", "messages", "inferenceConfig"}
              and payload["modelId"] == q.MODEL and payload["inferenceConfig"] == q.MODEL_SETTINGS["inference_config"],
              "Model or generation settings changed")
    ledger = q.load(out / "requests/ledger.json")
    q.require(set(q.inventory(out / "requests")) == {"ledger.json"}, "Local response evidence unexpectedly exists")
    q.require(set(ledger) == {"schema", "limit", "deadline", "reservations", "closed", "closed_reason"}
              and ledger["schema"] == "bounded-requests-v1" and ledger["limit"] == q.CALLS
              and ledger["deadline"] == q.DEADLINE and ledger["closed"] is True
              and ledger["closed_reason"] == "transport_or_response_failure" and len(ledger["reservations"]) == 1,
              "Local gate did not preserve the single terminal reservation")
    local = ledger["reservations"][0]
    q.require(set(local) == {"sequence", "status", "reserved_at_epoch", "task_id", "attempt_id", "prompt",
              "dispatch_started_at_epoch", "error_type"} and local["sequence"] == 1
              and local["status"] == "AMBIGUOUS_OR_UNSAVED" and local["task_id"] == first["task_id"]
              and local["attempt_id"] == first["trial_id"] and local["prompt"] == payload and local["error_type"] == ERROR,
              "Local ambiguous reservation differs")
    q.require(q.START <= q.finite(local["reserved_at_epoch"], "local reservation")
              <= q.finite(local["dispatch_started_at_epoch"], "local dispatch") <= global_slot["reserved_at_epoch"],
              "Local/global dispatch ordering differs")
    expected_result = dict(first, outcome="REQUEST_STOP", error_type=ERROR, stop=True)
    q.require(q.load(folder / "result.json") == expected_result and q.load(out / "results.json") == [expected_result],
              "Stopped outcome was rewritten or augmented")
    summary = q.load(out / "summary.json")
    q.require(summary == dict(maximum_calls=32, reserved_calls=1, dispatch_started=1, completed_responses=0,
              verified=0, fatal_error_type=None, all_trials_processed=False, unused_calls_not_reassigned=31,
              results=[expected_result]), "Raw stopped summary differs")
    initial = q.load(folder / "initial.json")
    q.require(set(initial) == {"revision", "source_sha256", "evidence_path", "evidence_sha256", "reused_original_verification", "new_verifier_runs"}
              and initial["source_sha256"] == parent["source_sha256"] == q.hashes(base)
              and initial["evidence_path"] == parent["original_verifier_path"]
              and initial["evidence_sha256"] == q.sha(out / "frozen-001" / parent["original_verifier_path"])
              and initial["reused_original_verification"] is True and initial["new_verifier_runs"] == 0,
              "Original evidence provenance changed")
    revision = audit_initial_revision(folder, initial, base, task)
    return dict(trial_id=first["trial_id"], task_id=task["task_id"], global_sequence=33, local_sequence=1,
        request_sha256=first["request_sha256"], outcome="REQUEST_STOP", error_type=ERROR,
        provider_request_id=None, saved_response=False, provider_token_usage=None,
        source_sha256=q.hashes(base), initial_revision=revision, final_observed_HEAD=revision,
        changed_files=[], promoted=False, new_verifier_runs=0), summary


def review(root=q.ROOT):
    root = Path(root).resolve()
    out, window, snapshot, transfer, before = audit_archive(root)
    runtime, scope = q.audit_freezes(root, out, window)
    prior, previous_admission, previous_receipt = q.previous_evidence()
    with q.replay_runtime(out) as replay:
        plan, parents, trials = replay.validate_bundle(out)
        q.require(len(trials) == q.CALLS and set(parents) == q.TASK_IDS and plan["proposed_calls"] == 32,
                  "Frozen batch scope differs")
        manifest = audit_admission(out, window, runtime, trials, previous_admission)
        status = audit_events(window, snapshot, prior)
        ledger, last = audit_global(window, scope, manifest, trials, prior, previous_receipt, status)
        launch = q.audit_launch(out, window, runtime)
        q.require(launch["accounting"]["State"] == "FAILED" and launch["accounting"]["ExitCode"] == "1:0",
                  "Scheduler terminal failure differs")
        attempted, summary = audit_attempt(out, window, trials, replay, last)
    job = launch["environment"]["job_id"]
    log = (window / f"session-{job}.log").read_text()
    old_log = (q.PREVIOUS_ROOT / "window-evidence-001" / f"session-{job}.log").read_text()
    q.require(log == old_log and not re.search(r"^repair-selection-", log, re.M), "Unexpected second-batch trial stdout")
    stderr = (window / f"session-{job}.err").read_text()
    q.require(stderr == "Session stopped: ValueError\n", "Session wrapper error differs")
    report = dict(schema="repodisco-repair-selection-stopped-review-v1", batch_id=q.BATCH,
        all_evidence_checks_passed=True, outcome="TERMINAL_REQUEST_STOP", proof_score=None,
        new_batch_evaluable_responses=0, new_batch_reserved_calls=1, new_batch_recorded_dispatch_attempts=1,
        new_batch_ambiguous_requests=1, new_batch_undispatched_trials=31,
        undispatched_trial_ids=[t["trial_id"] for t in trials[1:]], undispatched_calls_reassigned=False,
        aggregate_window=dict(cap=128, declared_calls=64, reserved_calls=33, completed_responses=32,
            ambiguous_requests=1, terminal_reason=ledger["terminal_reason"], permits_more_dispatch=False),
        configured_sdk_total_max_attempts=1, observed_new_sdk_retry_count=None,
        provider_execution_and_billing_unknown=True, no_automatic_retry_or_resume_recorded=True,
        proposal_freeze_sha256=q.PROPOSAL_SHA, admission_sha256=q.ADMISSION_SHA, runtime_freeze_sha256=q.RUNTIME_SHA,
        predecessor_ledger_sha256=q.PREVIOUS_LEDGER_SHA, predecessor_completion_sha256=q.PREVIOUS_COMPLETION_SHA,
        predecessor_archive_and_accepted_revisions_unchanged=True, new_candidates=0, new_verifier_runs=0,
        new_promotions=0, attempted=attempted, raw_summary_fatal_error_type=summary["fatal_error_type"],
        summary_caveat="The raw summary fatal_error_type is null; REQUEST_STOP, both ambiguous ledgers and the terminal session event establish the stop. Raw verified=0 is not a 0/32 proof score.",
        session=status, scheduler=launch, session_wrapper_error="ValueError", transport_error=ERROR,
        archive_file_count=len(before), snapshot_utc=snapshot["utc"], transfer_sha256=q.sha(root / "transfer-001.json"),
        compressed_archive_sha256=transfer["archive_sha256"], compressed_bytes=transfer["compressed_bytes"],
        audit_code_sha256=q.sha(Path(__file__)), completed_reviewer_sha256=COMPLETED_REVIEWER_SHA,
        limitations=["No model response was saved for the new batch; no mathematical or repair success rate is measurable.",
            "A read timeout does not reveal whether the provider executed or billed the request.",
            "One configured SDK attempt is verified from frozen code; absent response metadata cannot prove a returned retry count.",
            "The 31 unstarted trials have no outcomes and were not reassigned.",
            "The first batch's published results and accepted revisions remain unchanged."])
    _, _, _, _, after = audit_archive(root)
    q.require(before == after, "Stopped evidence changed during review")
    return report


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=q.ROOT)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    result = review(args.root)
    if args.output:
        target = args.output.resolve()
        q.require(all(not target.is_relative_to((args.root / name).resolve()) for name in
                  ("model-001", "window-evidence-001", "frozen-001")), "Never write into immutable evidence")
        with target.open("x") as stream:
            json.dump(result, stream, indent=2, sort_keys=True, allow_nan=False)
            stream.write("\n")
    print(json.dumps(result, indent=2, sort_keys=True, allow_nan=False))
