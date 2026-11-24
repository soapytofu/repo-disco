"""Offline replay of one frozen eight-request independent extension collection.

Derived from growth-001/execution-002/review_collection.py. This version audits
complete and terminal partial runs; it never dispatches, verifies natively,
issues acceptance, resumes a ledger, or reads credentials. Externally reviewed
archive/authorization/claim pins are the authority. Self-consistent third-party
JSON and hashes do not establish authentic execution provenance.
"""
import argparse
from dataclasses import dataclass
import json
import math
from pathlib import Path
import re

import runtime as rt
import allocation
import build_runtime
from credential_transport import validate_failure_diagnostic


@dataclass(frozen=True)
class CollectionAuthority:
    """Exact artifacts and expected identities supplied by the trusted host."""
    authorization_raw: bytes
    authorization_sha256: str
    claim_raw: bytes
    claim_sha256: str
    budget_raw: bytes
    budget_sha256: str
    job_id: str
    partition: str


def check(value, message):
    rt.require(value, message)


def same(left, right):
    return rt.canonical(left) == rt.canonical(right)


def decoded(raw):
    def unique(pairs):
        value = {}
        for key, item in pairs:
            check(key not in value, "Duplicate authority JSON key")
            value[key] = item
        return value
    check(isinstance(raw, bytes), "Authority must bind exact artifact bytes")
    return json.loads(raw.decode("utf-8"), object_pairs_hook=unique,
                      parse_constant=lambda _: (_ for _ in ()).throw(ValueError("Nonfinite authority JSON")))


def finite_number(value):
    return type(value) in (int, float) and math.isfinite(value)


def _host(host, expected, synthetic):
    check(isinstance(host, dict) and host.get("job_id") == expected["job_id"]
          and host.get("partition") == expected["partition"], "Native host/job differs")
    check(isinstance(host.get("hostname"), str) and host["hostname"]
          and "login" not in host["hostname"].lower(), "Native hostname is not compute provenance")
    if not synthetic:
        check(host.get("cpus_per_task") == 1, "Serial native CPU allocation differs")


def _response(response, ids, synthetic):
    check(isinstance(response, dict) and isinstance(response.get("raw_response"), dict),
          "Missing full raw provider response")
    raw = response["raw_response"]
    check((raw.get("synthetic") is True) == synthetic, "Provider synthetic marker differs")
    metadata = raw.get("ResponseMetadata", {})
    identity = response.get("request_id")
    check(isinstance(identity, str) and identity and identity == metadata.get("RequestId")
          and identity not in ids, "Missing, duplicated or inconsistent request ID")
    check(type(response.get("retry_attempts")) is int and response["retry_attempts"] == 0
          and type(metadata.get("RetryAttempts")) is int and metadata["RetryAttempts"] == 0,
          "Nonzero or missing SDK retry count")
    check(type(metadata.get("HTTPStatusCode")) is int and metadata["HTTPStatusCode"] == 200,
          "Returned response HTTP status differs")
    message = raw.get("output", {}).get("message", {})
    blocks = message.get("content")
    check(message.get("role") == "assistant" and isinstance(blocks, list)
          and all(isinstance(block, dict) for block in blocks), "Provider message is malformed")
    check(all(isinstance(block["text"], str) for block in blocks if "text" in block),
          "Provider text block is not text")
    check(response.get("content") == blocks
          and response.get("text") == "".join(block["text"] for block in blocks if "text" in block),
          "Raw response/content/text differs")
    check(isinstance(response.get("stop_reason"), str) and response["stop_reason"]
          and response["stop_reason"] == raw.get("stopReason"), "Provider stop reason differs")
    usage = response.get("usage")
    check(isinstance(usage, dict) and usage == raw.get("usage"), "Provider usage differs")
    for key in ("inputTokens", "outputTokens", "totalTokens"):
        check(type(usage.get(key)) is int and usage[key] >= 0, "Missing or invalid token count")
    check(usage["inputTokens"] + usage["outputTokens"] == usage["totalTokens"], "Token total differs")
    ids.add(identity)
    return {key: usage[key] for key in ("inputTokens", "outputTokens", "totalTokens")}


def _render(scope, stages, renderer, slot, package):
    stage = stages[(slot["project"], 1)]
    sources = dict(stage.base_sources)
    check(rt.native.hashes(sources) == stage.edit_profile["base_source_sha256"], "Protected base drift")
    check(stage.edit_profile["stage"] == 1 and stage.edit_profile.get("parent_requirement") is None,
          "Independent task cannot use a current-run parent")
    rendered = renderer.render_stage1(slot["project"], slot["chain_id"], root=package)
    expected = dict(project=slot["project"], stage=1, stage_id=stage.edit_profile["stage_id"],
        chain_id=slot["chain_id"], guard_profile_sha256=rt.sha(rt.canonical(stage.edit_profile)),
        source_revision_sha256=rt.sha(rt.canonical(rt.native.hashes(sources))),
        parent_audit=None, dispatch_eligible=False)
    check(isinstance(rendered, dict) and all(rendered.get(k) == v for k, v in expected.items()),
          "Frozen prompt/base binding differs")
    rt.validate_payload(rendered["payload"], scope["settings"])
    check(rendered.get("payload_sha256") == rt.sha(rt.canonical(rendered["payload"])), "Payload digest differs")
    return stage, sources, rendered


def _preflight(model, stages, expected_host, synthetic, required):
    """Recheck saved version/tool evidence; never execute version commands."""
    folder = model / "native-preflight"
    if not required:
        return dict(required=False, reviewed=False)
    if synthetic:
        value = rt.read_json(folder / "offline.json")
        check(value.get("synthetic") is True and value.get("native_calls") == 0, "Synthetic preflight marker missing")
        return dict(required=True, reviewed=True, synthetic=True, native_calls=0)
    identities, expected_files = set(), set()
    for (project, number), stage in sorted(stages.items()):
        check(number == 1, "Unexpected child stage")
        profile, adapter = stage.native_profile, stage.adapter
        identity = rt.sha(rt.canonical(dict(toolchain=profile["toolchain"], adapter=adapter)))
        if identity in identities:
            continue
        identities.add(identity)
        environment = rt.read_json(folder / project / "environment.json")
        check(environment["toolchain"] == environment["toolchain_after"] == profile["toolchain"],
              "Preflight tool inventory differs")
        _host(environment["host"], expected_host, False)
        expected_files.add(project + "/environment.json")
        commands = (("dafny", [profile["command"][0], "--version"], profile["toolchain"]["dafny_version"]),
                    ("solver", [str(Path(adapter["solver"]).expanduser()), "-version"], profile["toolchain"]["solver_version"]))
        for name, argv, version in commands:
            path = folder / project
            record = rt.read_json(path / (name + ".record.json"))
            check(record.get("argv") == argv and record.get("exit_code") == 0
                  and record.get("timeout") is False and finite_number(record.get("elapsed_seconds"))
                  and record["elapsed_seconds"] >= 0, "Preflight process record differs")
            check((path / (name + ".stdout")).read_text().strip() == version
                  and (path / (name + ".stderr")).read_bytes() == b"", "Preflight native version differs")
            expected_files.update(project + "/" + name + suffix for suffix in (".record.json", ".stdout", ".stderr"))
    check(set(rt.file_snapshot(folder)) == expected_files, "Preflight file inventory differs")
    return dict(required=True, reviewed=True, tool_environments=len(identities))


def _candidate(slot, folder, response, stage, base, rendered, run_id, expected_host,
               expected_output, nonces, synthetic, *, allow_incomplete):
    body, envelope = rt.parse_body_receipt(response["text"])
    rt.guard.render_body(stage.edit_profile, body)
    candidate, edit = rt.guard.reconstruct(stage.edit_profile, body, base, slot["chain_id"],
                                          parent=None, allow_synthetic=synthetic)
    check(edit.get("parent") is None and edit.get("acceptance_issued") is False,
          "Independent edit receipt cannot accept a parent")
    check((folder / "body.txt").read_bytes() == body.encode()
          and same(rt.read_json(folder / "envelope.json"), envelope), "Saved extraction differs")
    check(rt.source_files(folder / "candidate") == candidate
          and rt.file_snapshot(folder / "candidate") == rt.native.hashes(candidate), "Guarded candidate/source inventory differs")
    check(same(rt.read_json(folder / "edit-review.json"), edit), "Edit receipt replay differs")
    profile = rt.materialize_profile(stage.native_profile, candidate)
    check(same(rt.read_json(folder / "native-profile.json"), profile), "Materialized native profile differs")
    check((profile.get("synthetic") is True) == synthetic, "Native policy synthetic marker differs")
    result = dict(body_sha256=rt.sha(body.encode()), guarded_source_sha256=rt.native.hashes(candidate),
                  protected_base_preserved=True, native_reviewed=False)
    event_path = folder / "native-dispatch.json"
    if not event_path.exists():
        check(allow_incomplete and not (folder / "native").exists(), "Missing native dispatch")
        return result
    event = rt.read_json(event_path)
    expected = dict(schema="dafny-library-fresh-native-event-v1", host_run_id=run_id,
        run_id=run_id + ":" + slot["id"], slot_id=slot["id"], request_id=response["request_id"],
        request_sequence=int(slot["id"].split("-")[1]), response_sha256=rt.sha(rt.canonical(response)),
        payload_sha256=rendered["payload_sha256"], candidate_sha256=rt.sha(rt.canonical(rt.native.hashes(candidate))),
        profile_sha256=rt.sha(rt.canonical(profile)), synthetic=synthetic)
    check(set(event) == set(expected) | {"nonce"} and all(event[k] == v for k, v in expected.items()),
          "Native event is not coupled to this exact new request/candidate")
    nonce = event["nonce"]
    check(isinstance(nonce, str) and re.fullmatch(r"[0-9a-f]{32}", nonce) and nonce not in nonces,
          "Native event nonce reused or malformed")
    nonces.add(nonce)
    native_dir = folder / "native"
    record_path = native_dir / "record.json"
    if not record_path.exists():
        check(allow_incomplete and not (folder / "native-review.json").exists(),
              "Native evidence record missing")
        if (native_dir / "event.json").exists():
            check(rt.read_json(native_dir / "event.json") == event, "Partial native event differs")
        result["unfinished_native_dispatch"] = True
        return result
    record = rt.read_json(record_path)
    raw = {p.relative_to(native_dir / "raw").as_posix():p.read_bytes()
           for p in sorted((native_dir / "raw").rglob("*")) if p.is_file()}
    check(rt.file_snapshot(native_dir / "raw") == rt.native.hashes(raw), "Native raw inventory differs")
    check(rt.read_json(native_dir / "event.json") == event, "Native disk event differs")
    check(rt.source_files(native_dir / "workspace") == candidate, "Actual native workspace differs")
    workspace = rt.file_snapshot(native_dir / "workspace")
    expected_workspace = dict(rt.native.hashes(candidate))
    expected_workspace.update({name[4:]:rt.sha(data) for name,data in raw.items() if name.startswith("csv/")})
    check(workspace == expected_workspace, "Native workspace/CSV capture inventory differs")
    origin = "synthetic_offline" if synthetic else "model_candidate"
    check(record.get("origin") == origin and record.get("run_id") == event["run_id"]
          and record.get("attempts") == 1 and record.get("model_calls") == 0, "Native origin/run/attempt differs")
    check(record["run_id"] not in profile["ineligible_parent_runs"]
          and rt.sha(rt.canonical(rt.native.hashes(raw))) not in profile["ineligible_parent_raw_fingerprints"],
          "Known analyst qualification evidence cannot become model evidence")
    _host(record["host"], expected_host, synthetic)
    invocation = rt.read_json(native_dir / "invocation-start.json")
    expected_resources = str(Path(expected_output) / "slots" / slot["id"] / "native/raw/resources.txt")
    check(invocation.get("schema") == "dafny-library-native-invocation-v1"
          and invocation.get("event_sha256") == rt.sha(rt.canonical(event))
          and invocation.get("argv") == profile["command"]
          and invocation.get("wrapper_argv") == ["/usr/bin/time", "-v", "-o", expected_resources] + profile["command"]
          and invocation.get("host") == record["host"]
          and invocation.get("before_sha256") == rt.native.hashes(candidate)
          and invocation.get("wall_seconds") == stage.adapter["wall_seconds"],
          "Native invocation record differs")
    pins = rt.native.EvidencePins(rt.sha(rt.canonical(profile)), rt.sha(rt.canonical(record)),
        rt.sha(rt.canonical(rt.native.hashes(candidate))), tuple(sorted(rt.native.hashes(raw).items())),
        record["run_id"], origin)
    reviewed = rt.native.review(profile, candidate, record, raw, pins, allow_synthetic=synthetic)
    saved_review = folder / "native-review.json"
    if saved_review.exists():
        check(same(reviewed, rt.read_json(saved_review)), "Native reviewer replay differs")
    else:
        check(allow_incomplete, "Saved native review missing")
    result.update(native_reviewed=True, native_report=reviewed, native_record=record,
                  native_report_saved=saved_review.exists(), native_event_sha256=rt.sha(rt.canonical(event)),
                  nonterminal_failure=rt.nonterminal_native_failure(reviewed, record, raw,
                      stage.edit_profile["addition"]["path"]))
    return result


def _native_row(row, replay):
    check(replay["native_reviewed"] and replay["native_report_saved"], "Recorded native outcome has incomplete evidence")
    report, record = replay["native_report"], replay["native_record"]
    expected = dict(category=report["category"], native_run_id=record["run_id"],
        native_record_sha256=report["record_sha256"], passed_units=report["passed_units"],
        failed_units=report["failed_units"], warnings=report["warnings"],
        elapsed_seconds=report["elapsed_seconds"], accepted=report["qualified_success"], native_invoked=True)
    check(all(row.get(k) == v for k,v in expected.items()), "Recorded native outcome differs from full replay")
    if report["qualified_success"]:
        outcome = "ACCEPTED"
    else:
        nonfatal = replay["nonterminal_failure"]
        outcome = "NATIVE_REJECTED" if nonfatal else "TERMINAL_NATIVE_FAILURE"
    check(row.get("outcome") == outcome, "Native terminal/nonterminal classification differs")


def _audit_run(model, scope, stages, renderer, *, package, auth, expected_host,
               expected_output, allow_synthetic=False):
    """Internal replay core; synthetic fixtures require explicit opt-in."""
    model = Path(model)
    scope = rt.validate_scope(scope)
    check(set(stages) == {(task, 1) for task in rt.TASK_ORDER}, "Unexpected stage inventory")
    run, summary = rt.read_json(model / "run.json"), rt.read_json(model / "summary.json")
    ledger = rt.read_json(model / "requests/ledger.json")
    synthetic = run.get("synthetic")
    check(type(synthetic) is bool and run.get("offline") is synthetic
          and summary.get("synthetic") is synthetic and (allow_synthetic or not synthetic),
          "Synthetic collection is rejected by default")
    check(run.get("schema") == "dafny-library-model-run-v1"
          and run.get("scope_sha256") == rt.sha(rt.canonical(scope))
          and run.get("run_id") == summary.get("run_id") and isinstance(run["run_id"], str) and run["run_id"],
          "Run/scope identity differs")
    check(summary.get("schema") == "dafny-library-independent-extension-summary-v1"
          and summary.get("status") in {"COMPLETE", "TERMINAL"} and summary.get("independent_trials") is True,
          "Unsupported collection summary")
    for value in (run, summary):
        check(all(value.get(key) is True for key in ("no_retry", "no_resume", "no_reassignment")),
              "Terminal/no-retry policy differs")
    check(run.get("max_calls") == rt.MAX_CALLS and summary.get("declared_slots") == rt.MAX_CALLS,
          "Declared independent budget differs")
    check(ledger.get("schema") == "bounded-requests-v1" and ledger.get("limit") == rt.MAX_CALLS
          and ledger.get("closed") is True and ledger.get("closed_reason") == summary["status"].lower()
          and ledger.get("deadline") == auth["expires_at_epoch"], "Ledger is not the expected closed terminal ledger")
    check(not (model / "pilot-continuation.json").exists()
          and not list(model.rglob("parent-receipt.json")), "Independent collection cannot contain child acceptance")
    reservations, recorded = ledger.get("reservations"), summary.get("rows")
    check(isinstance(reservations, list) and len(reservations) <= rt.MAX_CALLS
          and isinstance(recorded, list) and len(recorded) <= len(reservations), "Reservation/outcome count invalid")
    if summary["status"] == "COMPLETE":
        check(len(reservations) == len(recorded) == rt.MAX_CALLS and summary.get("fatal") is None
              and not (model / "fatal.json").exists(), "Complete status lacks all eight outcomes")
    else:
        check(isinstance(summary.get("fatal"), dict)
              and rt.read_json(model / "fatal.json") == summary["fatal"], "Terminal fatal record differs")
    slots = scope["slots"]
    slot_root = model / "slots"
    folders = {p.name for p in slot_root.iterdir() if p.is_dir()} if slot_root.exists() else set()
    allowed_folders = {slot["id"] for slot in slots[:len(recorded)]}
    if (summary["status"] == "TERMINAL" and len(recorded) < rt.MAX_CALLS
            and summary["fatal"].get("slot_id") == slots[len(recorded)]["id"]):
        allowed_folders.add(slots[len(recorded)]["id"])
    check(folders <= allowed_folders, "Unexpected or later slot evidence")
    check(len(reservations) <= len(recorded) + (summary["status"] == "TERMINAL"),
          "More than one request lacks a recorded outcome")
    check(not any(r.get("outcome") == "TERMINAL_NATIVE_FAILURE" for r in recorded[:-1]),
          "Dispatch continued after a terminal native outcome")
    ids, nonces, rows, observed = set(), set(), [], []
    totals = dict(inputTokens=0, outputTokens=0, totalTokens=0)
    expected_response_files = set()
    replayed_native = dispatches = 0
    per_task = {task:dict(reserved=0, completed_reservations=0, captured_responses=0,
                         recorded_outcomes=0, accepted=0, output_rejected=0,
                         native_categories={}, tokens=dict(totals)) for task in rt.TASK_ORDER}
    unfinished = []
    for index, reservation in enumerate(reservations, 1):
        slot = slots[index - 1]
        folder = slot_root / slot["id"]
        check(reservation.get("sequence") == index and reservation.get("task_id") == slot["id"]
              and reservation.get("attempt_id") == run["run_id"] + ":" + slot["id"], "Reservation identity/order differs")
        status = reservation.get("status")
        check(status in {"COMPLETED", "AMBIGUOUS_OR_UNSAVED", "RESERVED"}, "Unknown reservation status")
        check(status == "COMPLETED" or (index == len(reservations) and summary["status"] == "TERMINAL"),
              "Dispatch continued after unresolved reservation")
        reserved_time, dispatch_time = reservation.get("reserved_at_epoch"), reservation.get("dispatch_started_at_epoch")
        check(finite_number(reserved_time) and auth["created_at_epoch"] <= reserved_time < auth["expires_at_epoch"],
              "Reservation outside authorization")
        if dispatch_time is not None:
            check(finite_number(dispatch_time) and reserved_time <= dispatch_time < auth["expires_at_epoch"],
                  "Dispatch outside authorization")
        check(status != "COMPLETED" or dispatch_time is not None, "Completed request was never dispatched")
        stage, base, rendered = _render(scope, stages, renderer, slot, package)
        check(same(rendered, rt.read_json(folder / "prompt.json"))
              and reservation.get("prompt") == rendered["payload"], "Frozen request replay differs")
        counters = per_task[slot["project"]]
        counters["reserved"] += 1
        counters["completed_reservations"] += status == "COMPLETED"
        response_path = model / "requests" / ("response-%03d.json" % index)
        row = recorded[index - 1] if index <= len(recorded) else None
        if status != "COMPLETED":
            check(row is None and not (folder / "outcome.json").exists()
                  and not any((folder / name).exists() for name in
                              ("response-binding.json", "candidate", "native-dispatch.json", "native-review.json")),
                  "Unresolved request was given a fabricated candidate/outcome")
            check(status != "RESERVED" or not response_path.exists(), "Undispatched reservation has a response")
            if response_path.exists():
                response = rt.read_json(response_path)
                usage = _response(response, ids, synthetic)
                expected_response_files.add(response_path.name)
                counters["captured_responses"] += 1
                for key, value in usage.items():
                    totals[key] += value
                    counters["tokens"][key] += value
                observed.append(dict(slot_id=slot["id"], request_id=response["request_id"],
                                     state="SAVED_BUT_UNCOMMITTED", usage=usage, score=None))
            unfinished.append(dict(slot_id=slot["id"], reservation_status=status,
                                   response_saved=response_path.exists(), candidate_scored=False))
            continue
        check(response_path.is_file(), "Completed reservation has no response")
        expected_response_files.add(response_path.name)
        response = rt.read_json(response_path)
        usage = _response(response, ids, synthetic)
        counters["captured_responses"] += 1
        for key, value in usage.items():
            totals[key] += value
            counters["tokens"][key] += value
        observed.append(dict(slot_id=slot["id"], request_id=response["request_id"],
                             state="COMPLETED", usage=usage, stop_reason=response["stop_reason"]))
        response_binding = dict(request_sequence=index, request_id=response["request_id"],
                                response_sha256=rt.sha(rt.canonical(response)))
        binding_path = folder / "response-binding.json"
        if binding_path.exists():
            check(rt.read_json(binding_path) == response_binding, "Saved response binding differs")
        if row is None:
            check(summary["status"] == "TERMINAL" and not (folder / "outcome.json").exists(),
                  "Missing outcome outside a terminal interruption")
            if (folder / "candidate").exists():
                check(binding_path.exists(), "Candidate lacks its returned request binding")
                replay = _candidate(slot, folder, response, stage, base, rendered, run["run_id"],
                    expected_host, expected_output, nonces, synthetic, allow_incomplete=True)
                replayed_native += replay["native_reviewed"]
            unfinished.append(dict(slot_id=slot["id"], reservation_status=status,
                                   response_saved=True, candidate_scored=False))
            continue
        check(rt.read_json(folder / "outcome.json") == row and all(row.get(k) == v for k,v in slot.items())
              and row.get("synthetic") is synthetic and all(row.get(k) == v for k,v in response_binding.items())
              and binding_path.exists(), "Slot/outcome/request summary differs")
        counters["recorded_outcomes"] += 1
        if row.get("outcome") == "OUTPUT_REJECTED":
            rejected = False
            try:
                body, _ = rt.parse_body_receipt(response["text"])
                rt.guard.render_body(stage.edit_profile, body)
            except rt.native.EvidenceError as error:
                rejected = True
                check(row.get("rejection_type") == type(error).__name__, "Policy rejection type differs")
            check(rejected and row.get("category") == "ENVELOPE_OR_BODY_POLICY"
                  and row.get("accepted") is False and row.get("native_invoked") is False,
                  "Output rejection does not replay")
            check(not any((folder / name).exists() for name in
                          ("body.txt", "candidate", "native", "native-dispatch.json", "native-review.json")),
                  "Rejected output acquired native evidence")
            counters["output_rejected"] += 1
            detail = {}
        else:
            detail = _candidate(slot, folder, response, stage, base, rendered, run["run_id"],
                expected_host, expected_output, nonces, synthetic, allow_incomplete=False)
            _native_row(row, detail)
            replayed_native += 1
            category = detail["native_report"]["category"]
            counters["native_categories"][category] = counters["native_categories"].get(category, 0) + 1
            if row["outcome"] == "TERMINAL_NATIVE_FAILURE":
                check(summary["status"] == "TERMINAL" and index == len(recorded) == len(reservations)
                      and summary["fatal"].get("native_category") == category
                      and summary["fatal"].get("slot_id") == slot["id"], "Terminal native outcome did not stop collection")
        counters["accepted"] += row["accepted"] is True
        rows.append(dict(slot_id=slot["id"], project=slot["project"], replicate=slot["replicate"],
            request_id=response["request_id"], outcome=row["outcome"], category=row["category"],
            accepted=row["accepted"], usage=usage, body_sha256=detail.get("body_sha256"),
            protected_base_preserved=detail.get("protected_base_preserved", False),
            native_run_id=row.get("native_run_id")))
    response_files = {p.name for p in (model / "requests").glob("response-*.json")}
    check(response_files == expected_response_files, "Missing or extra response artifacts")
    check({p.parent.name for p in slot_root.glob("*/outcome.json")} == {row["id"] for row in recorded},
          "Extra or missing outcome files")
    dispatches = len(list(slot_root.glob("*/native-dispatch.json")))
    check(dispatches == len(nonces), "Native dispatch escaped request/candidate replay")
    expected_counts = dict(reserved=len(reservations),
        completed=sum(r["status"] == "COMPLETED" for r in reservations),
        ambiguous_or_unsaved=sum(r["status"] == "AMBIGUOUS_OR_UNSAVED" for r in reservations),
        accepted_stages=sum(row["accepted"] is True for row in recorded),
        unused_request_capacity=rt.MAX_CALLS-len(reservations), recorded_slots=len(recorded),
        unprocessed_slots=rt.MAX_CALLS-len(recorded), native_dispatches=dispatches)
    check(all(type(summary.get(k)) is int and summary[k] == v for k,v in expected_counts.items()),
          "Summary accounting differs from durable artifacts")
    expected_per_task = {task:dict(returned=c["recorded_outcomes"], accepted=c["accepted"])
                         for task,c in per_task.items()}
    check(summary.get("per_task") == expected_per_task and summary.get("earlier_scores_unchanged") is True,
          "Per-task summary differs")
    native_observations = summary.get("native_observations")
    # A complete native record may exist just before the host increments its
    # in-memory counter. Preserve that one terminal boundary as uncertainty.
    saved_native_reviews = len(list(slot_root.glob("*/native-review.json")))
    check(type(native_observations) is int and saved_native_reviews <= native_observations <= replayed_native,
          "Native observation counter is unsupported by exact evidence")
    if not unfinished:
        check(native_observations == replayed_native, "Completed native observation count differs")
    if summary["status"] == "TERMINAL":
        fatal_slot = summary["fatal"].get("slot_id")
        if unfinished:
            check(fatal_slot == unfinished[-1]["slot_id"], "Fatal slot differs from unfinished request")
        elif len(recorded) < rt.MAX_CALLS:
            check(fatal_slot in {None, slots[len(recorded)]["id"],
                                recorded[-1]["id"] if recorded else None}, "Fatal slot is not the current boundary")
    diagnostic = None
    if (model / "transport-failure.json").exists():
        check(summary["status"] == "TERMINAL" and reservations
              and reservations[-1]["status"] == "AMBIGUOUS_OR_UNSAVED", "Transport error lacks its unresolved reservation")
        diagnostic = validate_failure_diagnostic(rt.read_json(model / "transport-failure.json"))
        retries = diagnostic["provider_error"]["ResponseMetadata"]["RetryAttempts"]
        check(retries in {None, 0}, "Failed request reports an SDK retry")
    preflight = _preflight(model, stages, expected_host, synthetic, required=bool(reservations))
    return dict(schema="dafny-library-independent-collection-review-v1",
        status="PASS_COMPLETE" if summary["status"] == "COMPLETE" else "PASS_TERMINAL_ACCOUNTING",
        synthetic=synthetic, run_id=run["run_id"], collection_status=summary["status"],
        declared_slots=rt.MAX_CALLS, reserved=len(reservations), completed_reservations=expected_counts["completed"],
        ambiguous_or_unsaved=expected_counts["ambiguous_or_unsaved"],
        uncommitted_reservations=sum(r["status"] != "COMPLETED" for r in reservations),
        reservations_without_saved_response=sum(not item["response_saved"] for item in unfinished),
        undispatched_slots=rt.MAX_CALLS-len(reservations), captured_responses=len(observed),
        unique_request_ids=len(ids), returned_response_sdk_retries=0,
        sdk_retries=(None if any(not item["response_saved"] for item in unfinished)
                     and (diagnostic is None or diagnostic["provider_error"]["ResponseMetadata"]["RetryAttempts"] is None)
                     else 0),
        transport_failure=diagnostic, tokens_from_saved_responses=totals,
        tokens_for_missing_responses=None if any(not item["response_saved"] for item in unfinished) else 0,
        recorded_outcomes=len(rows), accepted_additions=expected_counts["accepted_stages"],
        score=(dict(accepted=expected_counts["accepted_stages"], returned_trials=rt.MAX_CALLS)
               if summary["status"] == "COMPLETE" else None),
        per_task=per_task, outcome_counts={kind:sum(row["outcome"] == kind for row in rows)
            for kind in ("ACCEPTED", "OUTPUT_REJECTED", "NATIVE_REJECTED", "TERMINAL_NATIVE_FAILURE")},
        rows=rows, observed_responses=observed, unfinished_slots=unfinished,
        native_dispatch_records=dispatches, declared_native_observations=native_observations,
        replayed_native_records=replayed_native, native_preflight=preflight,
        fatal=summary["fatal"], primary_scores_changed=False, acceptance_issued=False,
        native_or_provider_calls_in_review=0)


def review_archive(archive_root, manifest_raw, expected_manifest_sha256):
    """Optional exact full-transfer inventory, itself pinned by the trusted host."""
    check(rt.sha(manifest_raw) == expected_manifest_sha256, "Archive manifest pin differs")
    manifest = decoded(manifest_raw)
    expected = {name:(entry if isinstance(entry, str) else entry["sha256"])
                for name,entry in manifest["files"].items()}
    check(all(rt.native.safe_path(name) for name in expected), "Unsafe archive inventory path")
    actual = rt.file_snapshot(archive_root)
    check(actual == expected, "Full archive file inventory differs")
    return len(actual)


def review_collection(package, model_output, *, expected_runtime_sha256, authority,
                      archive_root=None, archive_manifest_raw=None, expected_archive_sha256=None):
    """Strict production entry point. All authority pins must come from root review."""
    check(type(authority) is CollectionAuthority, "Typed externally pinned host authority required")
    for raw, expected in ((authority.authorization_raw, authority.authorization_sha256),
                          (authority.claim_raw, authority.claim_sha256),
                          (authority.budget_raw, authority.budget_sha256)):
        check(isinstance(expected, str) and rt.native.HEX.fullmatch(expected)
              and rt.sha(raw) == expected, "Externally expected artifact identity differs")
    check(all(isinstance(value, str) and value for value in (authority.job_id, authority.partition)),
          "Externally reviewed Slurm job/partition required")
    package, model = Path(package), Path(model_output)
    freeze_path = package / "execution-002/runtime-freeze.json"
    freeze = rt.validate_runtime(package, freeze_path, expected_runtime_sha256)
    freeze, scope, stages = build_runtime.validate_complete(package, freeze["scope"], freeze_path, expected_runtime_sha256)
    # This reviewer executes local reviewed Python, not arbitrary archived code.
    local_inputs = ("execution-002/review_collection.py", "execution-002/runtime.py",
                    "execution-002/build_runtime.py", "execution-002/allocation.py",
                    "execution-002/bounded_requests.py", "execution-002/extract_response.py",
                    "execution-002/credential_transport.py", "execution-002/provider_error.py",
                    "common/guard.py", "common/review_native.py")
    for name in local_inputs:
        check(name in freeze["files"] and rt.sha(rt.checked_path(rt.PACKAGE, name).read_bytes()) == freeze["files"][name],
              "Reviewer/dependency differs from frozen package: " + name)
    check(Path(rt.__file__).resolve() == rt.HERE / "runtime.py"
          and Path(rt.guard.__file__).resolve() == rt.COMMON / "guard.py"
          and Path(rt.native.__file__).resolve() == rt.COMMON / "review_native.py",
          "Mixed runtime module imports")
    auth, claim, budget = map(decoded, (authority.authorization_raw, authority.claim_raw, authority.budget_raw))
    scope_sha = rt.sha(rt.checked_path(package, freeze["scope"]).read_bytes())
    rt.validate_authorization(auth, scope_sha, expected_runtime_sha256, auth["created_at_epoch"])
    binding, frozen_budget, counts = allocation.validate_frozen_budget(package, scope)
    check(frozen_budget == authority.budget_raw and rt.sha(frozen_budget) == authority.budget_sha256,
          "Budget archive differs from frozen allocation")
    check(all(auth.get(key) == binding[key] for key in allocation.BINDING_FIELDS), "Authorization allocation binding differs")
    expected_claim = dict(schema="dafny-library-allocation-claim-v1", state="CONSUMED_NO_RESUME",
        authorization_sha256=authority.authorization_sha256, scope_sha256=scope_sha,
        scope_canonical_sha256=rt.sha(rt.canonical(scope)), runtime_manifest_sha256=expected_runtime_sha256,
        execution_binding=binding, budget_counts=counts, no_retry=True, no_resume=True, no_reassignment=True)
    check(all(claim.get(k) == v for k,v in expected_claim.items())
          and finite_number(claim.get("created_at_epoch"))
          and auth["created_at_epoch"] <= claim["created_at_epoch"] < auth["expires_at_epoch"],
          "Canonical consumed claim differs")
    check(same(rt.read_json(model / "authorization.json"), auth)
          and (model / "allocation-claim.json").read_bytes() == authority.claim_raw
          and (model / "budget-snapshot.json").read_bytes() == authority.budget_raw
          and same(rt.read_json(model / "runtime-freeze.json"), freeze), "Run authority artifacts differ")
    result = _audit_run(model, scope, stages, rt.load_renderer(package, scope["renderer"]),
        package=package, auth=auth, expected_host=dict(job_id=authority.job_id, partition=authority.partition),
        expected_output=binding["output_path"], allow_synthetic=False)
    result.update(runtime_sha256=expected_runtime_sha256, scope_sha256=scope_sha,
        authority_sha256=dict(authorization=authority.authorization_sha256,
                              claim=authority.claim_sha256, budget=authority.budget_sha256),
        budget_counts=counts, job_id=authority.job_id, partition=authority.partition,
        review_code_sha256=rt.sha(Path(__file__).read_bytes()), full_archive_reviewed=False)
    if any(value is not None for value in (archive_root, archive_manifest_raw, expected_archive_sha256)):
        check(all(value is not None for value in (archive_root, archive_manifest_raw, expected_archive_sha256)),
              "Incomplete full-archive authority")
        result.update(full_archive_reviewed=True, archive_files=review_archive(
            archive_root, archive_manifest_raw, expected_archive_sha256))
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--package", type=Path, required=True)
    parser.add_argument("--model-output", type=Path, required=True)
    parser.add_argument("--expected-runtime-sha256", required=True)
    for name in ("authorization", "claim", "budget"):
        parser.add_argument("--" + name, type=Path, required=True)
        parser.add_argument("--expected-" + name + "-sha256", required=True)
    parser.add_argument("--job-id", required=True)
    parser.add_argument("--partition", required=True)
    parser.add_argument("--archive-root", type=Path)
    parser.add_argument("--archive-manifest", type=Path)
    parser.add_argument("--expected-archive-sha256")
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    authority = CollectionAuthority(args.authorization.read_bytes(), args.expected_authorization_sha256,
        args.claim.read_bytes(), args.expected_claim_sha256, args.budget.read_bytes(),
        args.expected_budget_sha256, args.job_id, args.partition)
    result = review_collection(args.package, args.model_output,
        expected_runtime_sha256=args.expected_runtime_sha256, authority=authority,
        archive_root=args.archive_root,
        archive_manifest_raw=args.archive_manifest.read_bytes() if args.archive_manifest else None,
        expected_archive_sha256=args.expected_archive_sha256)
    rt.save(args.output, result)
    print(rt.canonical({k:result[k] for k in ("status", "reserved", "captured_responses",
          "recorded_outcomes", "accepted_additions", "score", "tokens_from_saved_responses")}).decode())


if __name__ == "__main__":
    main()
