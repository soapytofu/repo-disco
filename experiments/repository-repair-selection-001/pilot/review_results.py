"""Fail-closed offline audit of the second window-owned 32-request pipeline repair batch.

No transport, verifier, credential, submission, or promotion method is called.
Only hash-pinned archived guard/scoring functions are imported for exact replay.
The completion receipt covers the immutable batch; the separately timed window
snapshot may show the owning Slurm process still running after this batch.
"""
from collections import Counter
from contextlib import contextmanager
from datetime import datetime
import argparse
import csv
import hashlib
import importlib.util
import io
import json
import math
from pathlib import Path, PurePosixPath
import re
import sys

sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parent
BATCH = "repository-repair-selection-001"
PREVIOUS_BATCH = "repair-diversity-pilot-002"
PREVIOUS_ROOT = ROOT.parents[1] / PREVIOUS_BATCH
GLOBAL_CALLS = 64
GLOBAL_OFFSET = 32
PREVIOUS_ADMISSION_SHA = "de2516e216666522cb6ef3eaac6f35bb67f716fb31a4ee917a8ba688e8a9f73f"
PREVIOUS_LEDGER_SHA = "1a0281f6c4e3022b9d434194a1d7c987c8979ce0c41fc942c10300450ac4f6b7"
PREVIOUS_COMPLETION_SHA = "29505eabe3c17d431549baae3369db871db45def4eedf85fa72035df57b0ead7"
DERIVED_REVIEWER_SHA = "3ae0d8368b1b04962ebc125d580bea661416725f4bc49e779cc1d7013c8390d3"
POLICY_ID = "repository-repair-selection-bodies-v1-development"
TASK_IDS = {"intersection_or_separation-pipeline", "conserved_sum_gap-pipeline", "inverse_exchange_pipeline", "masked_override_composition_pipeline"}
GRAPH = {"HelperA.Prove": [], "HelperB.Prove": ["HelperA.Prove"], "ClientA.Target": ["HelperB.Prove"], "ClientB.Target": ["HelperB.Prove"]}
WINDOW = "repodisco-research-20261114"
CALLS = 32
DEADLINE = 1794801912.0
START = 1794715512.0
PROPOSAL_SHA = "9a3ac2546edc6c79307826766af3517bdc8d9a8fe629a2ba0239660f4ead778a"
RUNTIME_SHA = "ca24194ab90c932e0c514c1b390a80dd999645ccf07a9c937ea176f82b701b44"
SCOPE_SHA = "a649bcfca3be0b1120f8c7810778a344dd6fbf395dbeb6b6e362a20c5541ed01"
ADMISSION_SHA = "031903e63cf2d03c9b8a3bc340339832e1976c224b8e6c4e0128d433a440c975"
LAUNCH_SHA = "30f51639352abb451321a847aebc37ab8a230392fdfcc15a82eb8a2ba3bdd1cd"
MODEL = "global.anthropic.claude-opus-4-5-20251101-v1:0"
MODEL_SETTINGS = dict(model_id=MODEL, region="us-east-1",
                      inference_config=dict(temperature=1.0, maxTokens=4096))
COMMAND = ["timeout", "-k", "5s", "60s", "dafny", "verify",
           "--verify-included-files", "--log-format", "csv", "All.dfy"]
DIGEST = re.compile(r"[0-9a-f]{64}\Z")
REVISION = re.compile(r"[0-9a-f]{32}\Z")


class IncompleteEvidence(ValueError):
    """No complete local snapshot yet; this does not imply a request failed."""


class ExecutionStopped(ValueError):
    """Archived state explicitly records a stop or ambiguous request."""


def completion_state(root):
    out = root / "model-001"
    summary_path = out / "summary.json"
    if summary_path.exists():
        summary = load(summary_path)
        if summary.get("fatal_error_type") is not None:
            raise ExecutionStopped("Archive records execution stop: " + str(summary["fatal_error_type"]))
    for path in (out / "requests/ledger.json", root / "window-evidence-001/budget/ledger.json"):
        if path.exists():
            ledger = load(path)
            for row in ledger.get("reservations", []):
                if row.get("status") in ("AMBIGUOUS_OR_UNSAVED", "AMBIGUOUS", "ERROR"):
                    raise ExecutionStopped("Archive records an ambiguous or failed request; no complete score")
    required = [out / "completion.json", summary_path, root / "transfer-001.json",
                root / "window-evidence-001/snapshot-manifest.json"]
    missing = [str(path.relative_to(root)) for path in required if not path.is_file()]
    if missing:
        raise IncompleteEvidence("Incomplete local evidence, not a measured request error: " + ", ".join(missing))
    if not load(summary_path).get("all_trials_processed"):
        raise IncompleteEvidence("Archived batch has no complete trial inventory yet")


def require(condition, message):
    if not condition:
        raise ValueError(message)


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"),
                      ensure_ascii=False, allow_nan=False).encode()


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def unique_pairs(pairs):
    result = {}
    for key, value in pairs:
        require(key not in result, "Duplicate JSON key: " + key)
        result[key] = value
    return result


def load(path):
    require(path.is_file() and not path.is_symlink(), "Missing/unsafe evidence: " + str(path))
    return json.loads(path.read_bytes(), object_pairs_hook=unique_pairs,
                      parse_constant=lambda _: (_ for _ in ()).throw(ValueError("Nonfinite JSON")))


def sha(path):
    require(path.is_file() and not path.is_symlink(), "Missing/unsafe pinned file: " + str(path))
    return digest(path.read_bytes())


def relative(name):
    require(isinstance(name, str) and name and "\\" not in name, "Invalid relative path")
    path = PurePosixPath(name)
    require(not path.is_absolute() and all(x not in ("", ".", "..") for x in name.split("/")),
            "Unsafe relative path: " + name)
    return path


def inventory(root):
    require(root.is_dir() and not root.is_symlink(), "Missing/unsafe evidence directory: " + str(root))
    result = {}
    for path in sorted(root.rglob("*")):
        require(not path.is_symlink(), "Symlink in evidence: " + str(path))
        require(path.is_dir() or path.is_file(), "Special file in evidence: " + str(path))
        if path.is_file():
            result[path.relative_to(root).as_posix()] = sha(path)
    return result


def checked_pins(pins, label):
    require(isinstance(pins, dict) and pins, label + " inventory missing")
    for name, expected in pins.items():
        relative(name)
        require(isinstance(expected, str) and DIGEST.fullmatch(expected), label + " invalid digest")
    return pins


def source_files(folder):
    pins = inventory(folder)
    require(pins and all("/" not in n and n.endswith(".dfy") for n in pins), "Unexpected source artifact")
    return {name: (folder / name).read_bytes() for name in pins}


def hashes(files):
    return {name: digest(raw) for name, raw in sorted(files.items())}


def finite(value, label):
    require(type(value) in (int, float) and math.isfinite(value), "Invalid " + label)
    return value


def audit_inventories(root):
    completion_state(root)
    out, window = root / "model-001", root / "window-evidence-001"
    actual = {"model-001/" + n: h for n, h in inventory(out).items()}
    actual.update({"window-evidence-001/" + n: h for n, h in inventory(window).items()})
    transfer = load(root / "transfer-001.json")
    require(actual == checked_pins(transfer["files"], "Transfer"), "Transfer inventory differs")
    require(DIGEST.fullmatch(transfer["archive_sha256"]) and transfer["compressed_bytes"] > 0,
            "Missing transfer archive metadata")
    snapshot = load(window / "snapshot-manifest.json")
    expected = dict(actual)
    expected.pop("window-evidence-001/snapshot-manifest.json")
    require(snapshot["files"] == expected and snapshot["batch_id"] == BATCH
            and snapshot["credential_access"] is False, "Timed snapshot inventory differs")
    datetime.fromisoformat(snapshot["utc"])
    receipt = load(out / "completion.json")
    expected = inventory(out)
    expected.pop("completion.json")
    require(receipt["evidence_sha256"] == expected, "Durable completion inventory differs")
    require(set(receipt) == {"batch_id", "descriptor_sha256", "completed_trials", "evidence_sha256", "request_ids"}
            and receipt["batch_id"] == BATCH, "Completion receipt schema differs")
    return out, window, snapshot, receipt, actual


def audit_freezes(root, out, window):
    require(sha(out / "frozen-001/freeze.json") == PROPOSAL_SHA
            == sha(root / "frozen-001/freeze.json"), "Reviewed proposal differs")
    freeze = load(out / "frozen-001/freeze.json")
    frozen_pins = inventory(out / "frozen-001")
    frozen_pins.pop("freeze.json")
    require(frozen_pins == freeze["files"] and inventory(out / "inputs") == freeze["repository_inputs_sha256"],
            "Frozen source/request/guard input inventory differs")
    require(freeze["source_commit"] == "cfa51ee966b3f54cfcec3badb8c8f77fe310da94"
            and freeze["proposed_calls"] == CALLS, "Reviewed source provenance differs")
    require(sha(out / "runtime-freeze.json") == RUNTIME_SHA, "Reviewed execution runtime differs")
    runtime = load(out / "runtime-freeze.json")
    require(inventory(out / "runtime") == checked_pins(runtime["runtime_sha256"], "Runtime"),
            "Archived runtime differs")
    dependency_pins = {}
    for original, archive in (("runtime", "window-runtime"), ("session-runtime-002", "session-runtime")):
        dependency_pins.update({"../" + original + "/" + n: h for n, h in inventory(out / archive).items()})
    require(dependency_pins == runtime["dependencies_sha256"], "Window/coordinator runtime differs")
    require(runtime["schema"] == "repodisco-session-execution-v1" and runtime["handler_id"] == "repair-v1"
            and runtime["window_id"] == WINDOW and runtime["deadline_epoch"] == DEADLINE
            and runtime["scope_sha256"] == SCOPE_SHA and runtime["automatic_retries"] is False
            and type(runtime["sdk_total_max_attempts"]) is int and runtime["sdk_total_max_attempts"] == 1
            and runtime["model_settings"] == MODEL_SETTINGS, "Runtime scope differs")
    require(sha(out / "scope.json") == SCOPE_SHA == sha(window / "scope.json"), "Window scope differs")
    scope = load(out / "scope.json")
    require(scope["authorized"] is True and scope["max_calls"] == 128 and scope["deadline_epoch"] == DEADLINE
            and scope["no_retries"] is True and scope["automatic_resume"] is False, "Window authorization differs")
    binding = load(out / "batch-binding.json")
    require(binding == dict(window_id=WINDOW, batch_id=BATCH, max_calls=CALLS, authorized=True,
                            automatic_retries=False, max_calls_per_trial=1, model_settings=MODEL_SETTINGS,
                            proposal_freeze_sha256=PROPOSAL_SHA, runtime_freeze_sha256=RUNTIME_SHA),
            "Batch authorization differs")
    metric_scope = load(out / "frozen-001/measurement-scope.json")
    require(metric_scope["interpreter_sha256"] == sha(out / "runtime/target_metrics.py")
            and sha(out / "runtime/repair_protocol.py") == sha(out / "frozen-001/policy/repair_protocol.py"),
            "Scoring/repair adapter differs")
    require(set(metric_scope["tasks"]) == TASK_IDS, "Pipeline task scope differs")
    for task_scope in metric_scope["tasks"].values():
        require(task_scope["editable_targets"] == ["HelperA.Prove", "HelperB.Prove"]
                and task_scope["target_dependencies"] == GRAPH,
                "Pipeline eligible targets or declared graph differs")
    require(sha(out / "frozen-001/policy/policy-freeze.json") ==
            "076ae7cacb620e57ecbc137be0e4ddda4924106852dc8bd87700dcef82c2f7df",
            "Reviewed per-file policy differs")
    return runtime, scope


@contextmanager
def replay_runtime(out):
    """Import only audited archived code, with bytecode writes disabled."""
    runtime = out / "runtime"
    roots = {"target_metrics", "repair_protocol", "repository_agent", "logging_verifier", "bounded_requests", "execute", "language"}
    old_modules = {n: m for n, m in sys.modules.items() if n.split(".")[0] in roots}
    old_path = list(sys.path)
    for name in old_modules:
        sys.modules.pop(name)
    sys.path.insert(0, str(runtime))
    name = "offline_audited_repair_batch"
    old_batch = sys.modules.get(name)
    spec = importlib.util.spec_from_file_location(name, runtime / "run_batch.py")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    try:
        spec.loader.exec_module(module)
        yield module
    finally:
        sys.path[:] = old_path
        for key in list(sys.modules):
            if key.split(".")[0] in roots:
                sys.modules.pop(key)
        sys.modules.update(old_modules)
        if old_batch is None:
            sys.modules.pop(name, None)
        else:
            sys.modules[name] = old_batch


def previous_evidence():
    window = PREVIOUS_ROOT / "window-evidence-001"
    out = PREVIOUS_ROOT / "model-001"
    require(sha(window / "budget/ledger.json") == PREVIOUS_LEDGER_SHA,
            "Published predecessor ledger differs")
    require(sha(out / "completion.json") == PREVIOUS_COMPLETION_SHA,
            "Published predecessor completion differs")
    require(sha(out / "admission.json") == PREVIOUS_ADMISSION_SHA,
            "Published predecessor admission differs")
    receipt = load(out / "completion.json")
    pins = inventory(out); pins.pop("completion.json")
    require(pins == receipt["evidence_sha256"], "Published predecessor raw archive changed")
    ledger = load(window / "budget/ledger.json")
    require(len(ledger["reservations"]) == GLOBAL_OFFSET and len(ledger["batches"]) == 1,
            "Published predecessor slot count differs")
    return ledger, load(out / "admission.json"), receipt


def audit_session(out, window, runtime, scope, trials, receipt, snapshot):
    prior, previous_admission, previous_receipt = previous_evidence()
    admission = load(out / "admission.json")
    require(isinstance(ADMISSION_SHA, str) and DIGEST.fullmatch(ADMISSION_SHA),
            "Sequence-two admission has not yet been independently pinned")
    require(sha(out / "admission.json") == ADMISSION_SHA, "Reviewed admission differs")
    bundle_pins = {"frozen-001/" + n: h for n, h in inventory(out / "frozen-001").items()}
    bundle_pins.update({"inputs/" + n: h for n, h in inventory(out / "inputs").items()})
    bundle_pins.update({n: sha(out / n) for n in ("batch-binding.json", "runtime-freeze.json")})
    expected = dict(schema="repodisco-session-descriptor-v1", sequence=2,
                    previous_descriptor_sha256=PREVIOUS_ADMISSION_SHA,
                    batch_id=BATCH, handler_id="repair-v1", handler_binding_sha256=digest(canonical(runtime["runtime_sha256"])),
                    artifact_directory=BATCH, freeze_path="frozen-001/freeze.json", freeze_sha256=PROPOSAL_SHA,
                    runtime_path="runtime-freeze.json", runtime_sha256=RUNTIME_SHA, input_sha256=bundle_pins,
                    slots=[dict(trial_id=t["trial_id"], request_path="frozen-001/" + t["request_path"],
                                request_sha256=t["request_sha256"]) for t in trials], max_calls=CALLS, sdk_total_max_attempts=1)
    require(admission == expected, "Frozen second admission/input/order binding differs")
    queued = window / "session/queue" / ("0002-" + BATCH + ".json")
    prior_queued = window / "session/queue" / ("0001-" + PREVIOUS_BATCH + ".json")
    require(inventory(window / "session/queue") == {prior_queued.name: PREVIOUS_ADMISSION_SHA, queued.name: ADMISSION_SHA}
            and load(queued) == admission and load(prior_queued) == previous_admission
            and sha(queued) == receipt["descriptor_sha256"], "Queue/receipt chain differs")
    require(inventory(window / "admissions") == {"000001.json": PREVIOUS_ADMISSION_SHA, "000002.json": ADMISSION_SHA},
            "Admission snapshot differs")
    require(inventory(window / "completions") == {PREVIOUS_BATCH + ".json": PREVIOUS_COMPLETION_SHA,
            BATCH + ".json": sha(out / "completion.json")}, "Completion snapshot differs")
    trial_ids = [t["trial_id"] for t in trials]
    require(receipt["completed_trials"] == trial_ids, "Completion trial order differs")
    events_folder = window / "session/events"
    event_pins = inventory(events_folder)
    require(list(event_pins) == [f"{i:05}.json" for i in range(1, len(event_pins) + 1)], "Session event sequence incomplete")
    for name, h in inventory(PREVIOUS_ROOT / "window-evidence-001/session/events").items():
        require(event_pins.get(name) == h, "Published predecessor session event changed")
    events = [load(events_folder / name) for name in event_pins]
    require(events and load(window / "session/status.json") == events[-1], "Session status is not last durable event")
    previous_time, previous_count = START, 0
    for i, event in enumerate(events, 1):
        timestamp = finite(event["at_epoch"], "event time")
        require(event["schema"] == "repodisco-session-status-v1" and event["event_sequence"] == i
                and event["deadline_epoch"] == DEADLINE and timestamp >= previous_time
                and previous_count <= event["window_reservations"] <= GLOBAL_CALLS, "Incoherent session event")
        require(event["completed_batch_ids"] in ([], [PREVIOUS_BATCH], [PREVIOUS_BATCH, BATCH])
                and event["active_batch_id"] in (None, PREVIOUS_BATCH, BATCH), "Unexpected batch in session history")
        if event["active_batch_id"] == BATCH:
            require(event["completed_batch_ids"] == [PREVIOUS_BATCH], "Second batch started before first completed")
        previous_time, previous_count = timestamp, event["window_reservations"]
    status = events[-1]
    require(status["completed_batch_ids"] == [PREVIOUS_BATCH, BATCH] and status["active_batch_id"] is None
            and status["window_reservations"] == GLOBAL_CALLS, "Second batch not complete at window snapshot")
    require(any(e["phase"] == "completed" and e["reason"] == "batch_complete"
                and e["completed_batch_ids"] == [PREVIOUS_BATCH, BATCH] for e in events), "Missing second completion event")
    require(snapshot["session_still_running"] == (status["phase"] not in ("error", "closed")), "Snapshot process status differs")
    manifest = {k: admission[k] for k in ("batch_id", "freeze_sha256", "runtime_sha256", "max_calls", "sdk_total_max_attempts")}
    manifest["slots"] = [{k: slot[k] for k in ("trial_id", "request_sha256")} for slot in admission["slots"]]
    ledger = load(window / "budget/ledger.json")
    require(ledger["schema"] == "repodisco-window-budget-v1" and ledger["scope"] == scope
            and ledger["scope_sha256"] == digest(canonical(scope)), "Global ledger scope differs")
    require(ledger["batches"] == prior["batches"] + [dict(manifest=manifest, manifest_sha256=digest(canonical(manifest)))],
            "Unexpected global batch allocation")
    require(ledger["owner_session"] == prior["owner_session"], "Global budget owner changed")
    reservations = ledger["reservations"]
    require(len(reservations) == GLOBAL_CALLS, "Expected exactly64 global reservations")
    require(reservations[:GLOBAL_OFFSET] == prior["reservations"], "Published predecessor reservations changed")
    names = {f"{kind}-{i:03}.json" for i in range(1, GLOBAL_CALLS + 1) for kind in ("request", "response")}
    require(set(inventory(window / "budget/requests")) == names, "Unaccounted global request evidence")
    ids = set()
    for i, row in enumerate(reservations, 1):
        request_path = window / "budget/requests" / f"request-{i:03}.json"
        response_path = window / "budget/requests" / f"response-{i:03}.json"
        response = load(response_path)
        require(row["sequence"] == i and row["status"] == "COMPLETED"
                and row["request_sha256"] == sha(request_path) and row["response_sha256"] == sha(response_path),
                "Global slot/request/response binding differs")
        if i <= GLOBAL_OFFSET:
            require(row["batch_id"] == PREVIOUS_BATCH, "Predecessor slot reassigned")
        else:
            trial = trials[i - GLOBAL_OFFSET - 1]
            require(row["batch_id"] == BATCH and row["trial_id"] == trial["trial_id"]
                    and row["manifest_sha256"] == digest(canonical(manifest))
                    and row["request_sha256"] == trial["request_sha256"], "Second global slot reassigned")
            require(request_path.read_bytes() == (out / "frozen-001" / trial["request_path"]).read_bytes(), "Global request byte drift")
        require(START <= finite(row["reserved_at_epoch"], "reservation time")
                <= finite(row["dispatch_intent_at_epoch"], "dispatch time") < DEADLINE
                and row["dispatch_intent_at_epoch"] <= finite(row["returned_at_epoch"], "return time"), "Global dispatch deadline/order")
        rid = response.get("request_id")
        require(isinstance(rid, str) and rid and rid not in ids and row["request_id"] == rid
                and type(response.get("retry_attempts")) is int and response["retry_attempts"] == 0, "Global ID/retry evidence")
        ids.add(rid)
    require(previous_receipt["request_ids"] == [r["request_id"] for r in reservations[:GLOBAL_OFFSET]], "Predecessor receipt IDs differ")
    require(receipt["request_ids"] == [r["request_id"] for r in reservations[GLOBAL_OFFSET:]], "Second receipt request IDs differ")
    return ledger, status


def same_slurm_node(host, node_list):
    """A single Slurm node may use the socket hostname or its first DNS label.

    Do not expand ranges, split multi-node lists, case-fold, or discard raw
    provenance. The report retains the original environment and accounting.
    """
    label = r"[A-Za-z0-9](?:[A-Za-z0-9-]*[A-Za-z0-9])?"
    single = re.compile(label + r"(?:\." + label + r")*\Z")
    return (isinstance(host, str) and isinstance(node_list, str)
            and single.fullmatch(host) is not None and single.fullmatch(node_list) is not None
            and node_list in (host, host.split(".", 1)[0]))


def audit_launch(out, window, runtime):
    require(sha(window / "launch-manifest.json") == LAUNCH_SHA, "Reviewed launch manifest differs")
    launch = load(window / "launch-manifest.json")
    require(launch["execution_freeze_sha256"] == RUNTIME_SHA and launch["scope_sha256"] == SCOPE_SHA
            and launch["window_limit"] == 128 and launch["initial_batch_calls"] == CALLS
            and launch["no_retries"] is True and launch["automatic_resume"] is False, "Launch policy differs")
    for name, expected in checked_pins(launch["files"], "Launch").items():
        prefix = "batches/" + PREVIOUS_BATCH + "/"
        if name.startswith(prefix):
            path = PREVIOUS_ROOT / "model-001" / name[len(prefix):]
        elif name.startswith("execution-runtime/"):
            tail = name[len("execution-runtime/"):]
            path = out / tail if tail == "runtime-freeze.json" else out / "runtime" / tail
        elif name.startswith("runtime/"):
            path = out / "window-runtime" / name[len("runtime/"):]
        elif name.startswith("session-runtime-002/"):
            path = out / "session-runtime" / name[len("session-runtime-002/"):]
        elif name == "admissions/000001.json":
            path = window / "admissions/000001.json"
        else:
            path = window / name
        require(sha(path) == expected, "Launch pin differs: " + name)
    submission = load(window / "submission-001.json")
    require(submission["launch_manifest_sha256"] == LAUNCH_SHA and submission["no_requeue"] is True
            and submission["no_retries"] is True and submission["maximum_window_calls"] == 128
            and submission["initial_batch_calls"] == CALLS and submission["returncode"] == 0,
            "Submission evidence differs")
    env = load(out / "environment.json")
    job = env["job_id"]
    require(isinstance(job, str) and job.isdigit() and job == submission["job_id"]
            and "login" not in env["host"].lower() and env["host"]
            and env["versions"] == runtime["environment_versions"]
            and env["requeue"] is False and env["model_connectivity_calls"] == 0,
            "Compute environment differs")
    require("PreemptMode=OFF" in submission["partition_evidence"][env["partition"]], "Nonpreemptible partition evidence missing")
    preflight = load(window / "execution-preflight-001.json")
    require(preflight["returncode"] == 0 and preflight["credential_access"] is False
            and preflight["model_calls"] == preflight["verifier_calls"] == 0, "Offline compute preflight missing")
    table = list(csv.DictReader(io.StringIO((window / "accounting-snapshot.txt").read_text()), delimiter="|"))
    jobs = [row for row in table if row.get("JobID") == job]
    require(len(jobs) == 1 and same_slurm_node(env["host"], jobs[0]["NodeList"]), "Scheduler/node evidence differs")
    sha(window / f"session-{job}.log")
    sha(window / f"session-{job}.err")
    return dict(environment=env, accounting=jobs[0], session_stderr_bytes=(window / f"session-{job}.err").stat().st_size)


def audit_response(response, result, seen):
    raw = response["raw_response"]
    rid = response["request_id"]
    require(isinstance(rid, str) and rid and rid not in seen
            and rid == raw["ResponseMetadata"]["RequestId"] == result["request_id"], "Unique provider request ID")
    retries = [response["retry_attempts"], raw["ResponseMetadata"]["RetryAttempts"], result["retry_attempts"]]
    require(all(type(n) is int and n == 0 for n in retries), "SDK retry metadata differs")
    require(response["content"] == raw["output"]["message"]["content"]
            and response["text"] == "".join(b["text"] for b in response["content"] if "text" in b), "Raw content normalization differs")
    require(response["stop_reason"] == raw["stopReason"] == result["stop_reason"]
            and response["usage"] == raw.get("usage") == result["usage"], "Raw response metadata differs")
    usage = response["usage"]
    require(isinstance(usage, dict) and all(type(v) is int and v >= 0 for v in usage.values())
            and usage["inputTokens"] + usage["outputTokens"] == usage["totalTokens"], "Token evidence differs")
    seen.add(rid)


def diagnostic_categories(evidence):
    text = evidence["stdout"] + "\n" + evidence["stderr"]
    patterns = {
        "precondition": r"(?:precondition.*(?:could not|cannot|might not)|(?:could not|cannot).*precondition)",
        "postcondition": r"(?:postcondition.*(?:could not|cannot|might not)|(?:could not|cannot).*postcondition)",
        "assertion": r"assertion (?:might not|could not)",
        "termination": r"decreases|termination|might not decrease",
        "parse": r"parse errors? detected",
        "resolution_type": r"resolution/type errors? detected",
        "warning": r": Warning:",
    }
    return [name for name, pattern in patterns.items() if re.search(pattern, text, re.I)]


def audit_verifier(folder, evidence, edited, task, out, replay, result):
    require(evidence["source_sha256"] == hashes(edited) and evidence["command"] == COMMAND
            and type(evidence["attempts"]) is int and evidence["attempts"] == 1
            and type(evidence["model_calls"]) is int and evidence["model_calls"] == 0,
            "Verifier source/command/attempts differ")
    csv_files = evidence["csv"]
    require(isinstance(csv_files, dict) and all(isinstance(t, str) for t in csv_files.values()), "CSV evidence missing")
    for name in csv_files:
        relative(name)
    csv_pins = {name: digest(text.encode()) for name, text in csv_files.items()}
    require(evidence["csv_sha256"] == csv_pins, "CSV digest differs")
    raw_pins = inventory(folder / "raw-csv") if (folder / "raw-csv").exists() else {}
    require(raw_pins == csv_pins, "Raw CSV bytes/inventory differ")
    outcome = replay.outcome_for_evidence(evidence)
    metrics, stop = replay.measurement(evidence, task, out)
    require(metrics == load(folder / "target-metrics.json"), "Named scope/dependency metric replay differs")
    expected_outcome = "MEASUREMENT_STOP" if stop else outcome
    require(result["outcome"] == expected_outcome and result["verifier_outcome"] == outcome
            and result["measurement_available"] == metrics["available"]
            and result["stop"] == (stop or outcome not in replay.NORMAL_OUTCOMES), "Verifier category/stop mismatch")
    if outcome == "PROOF_FAILURE" and metrics["available"]:
        require(not all(metrics["local_targets"].values()), "Proof failure has no failed named proof target")
    return outcome, metrics, diagnostic_categories(evidence)


def optional_empty_directory(path):
    """File-only evidence archives legitimately omit an empty directory."""
    require(not path.is_symlink(), "Symlink in empty-directory evidence")
    if path.exists():
        require(path.is_dir() and not any(path.iterdir()), "Nonempty or non-directory attempt evidence")


def audit_revision(folder, initial, base, task, edited=None, evidence=None):
    store = folder / "store"
    first = initial["revision"]
    require(isinstance(first, str) and REVISION.fullmatch(first), "Invalid initial revision ID")
    old = store / "revisions" / first
    manifest = dict(task_id=task["task_id"], entry=task["entry"], editable=task["editable_files"],
                    dependencies={n: re.findall(r'^include "([^"]+)"', b.decode(), re.M) for n, b in base.items()})
    require(source_files(old / "files") == base and load(old / "revision.json") ==
            dict(revision=first, parent=None, manifest=manifest, source_sha256=hashes(base), verification=None),
            "Original revision/source/contracts changed")
    optional_empty_directory(store / "attempts")
    require((store / "write.lock").read_bytes() == b"", "Unexpected store writer artifacts")
    head = load(store / "HEAD.json")
    require(set(head) == {"revision"} and REVISION.fullmatch(head["revision"]), "Invalid accepted HEAD")
    final_id = head["revision"]
    promoted = edited is not None
    if promoted:
        require(final_id != first, "Verified candidate not promoted")
        final = store / "revisions" / final_id
        require(source_files(final / "files") == edited and load(final / "revision.json") ==
                dict(revision=final_id, parent=first, manifest=manifest, source_sha256=hashes(edited), verification=evidence),
                "Accepted revision source/specification/evidence differs")
        require(load(folder / "accepted.json") == dict(base_revision=first, revision=final_id,
                parent_sha256=hashes(base), candidate_sha256=hashes(edited), verification_sha256=sha(folder / "verification.json")),
                "Promotion receipt differs")
    else:
        require(final_id == first and not (folder / "accepted.json").exists(), "Failed/rejected repair promoted")
    require({p.name for p in (store / "revisions").iterdir()} == ({first, final_id} if promoted else {first}), "Unexpected revisions")
    require(load(folder / "final-head.json") == dict(revision=final_id, source_sha256=hashes(edited if promoted else base)),
            "Final HEAD evidence differs")
    return first, final_id


def classify_body_edit(original, edited, before_tokens, after_tokens):
    """Exact source versus normalized-token edits; no semantic/minimality claim."""
    if original == edited:
        return "unchanged"
    if before_tokens == after_tokens:
        return "whitespace_only"
    return "token_change"


def call_sites(tree):
    """Count syntactic lemma-call sites, not dynamic branch/quantifier executions."""
    result = []
    def visit(node):
        if not isinstance(node, list):
            return
        if node and node[0] == "call":
            result.append(dict(symbol=node[1], arguments=node[2]))
        for child in node:
            if isinstance(child, list):
                visit(child)
    visit(tree)
    return result


def body_review(guard, task, template, base, edited, decision):
    require(decision["original_guard_decision"]["body_guard"]["policy_id"] == POLICY_ID,
            "Distinct prospective policy identity missing")
    entry = guard.task_entry(task)
    require(task["editable_files"] == ["HelperA.dfy", "HelperB.dfy"], "Pipeline editable files differ")
    files = {}
    for name in task["editable_files"]:
        prefix, suffix = guard.split_seed(template[name].decode())
        before, after = base[name].decode(), edited[name].decode()
        require(before.startswith(prefix) and before.endswith(suffix)
                and after.startswith(prefix) and after.endswith(suffix), "Protected helper contract changed")
        old_body = before[len(prefix):-len(suffix)]
        new_body = after[len(prefix):-len(suffix)]
        rules = entry["file_rules"][name]
        old_parser, new_parser = guard.Grammar(old_body, rules), guard.Grammar(new_body, rules)
        old_tree, new_tree = old_parser.sequence(), new_parser.sequence()
        require(old_parser.peek() is None and new_parser.peek() is None, "Unexpected trailing body tokens")
        guard.Types(rules).statements(old_tree)
        guard.Types(rules).statements(new_tree)
        sites = call_sites(new_tree)
        helper_sites = [site for site in sites if site["symbol"] == "H.Prove"]
        require(name == "HelperB.dfy" or not helper_sites, "Reverse helper call observed")
        files[name] = dict(edit_classification=classify_body_edit(old_body, new_body, old_parser.tokens, new_parser.tokens),
            exact_changed=old_body != new_body, tokens_changed=old_parser.tokens != new_parser.tokens,
            original_body_sha256=digest(old_body.encode()), candidate_body_sha256=digest(new_body.encode()),
            original_tokens_sha256=digest(canonical(old_parser.tokens)), candidate_tokens_sha256=digest(canonical(new_parser.tokens)),
            original_tokens=len(old_parser.tokens), candidate_tokens=len(new_parser.tokens),
            lemma_call_sites=sites, helper_call_site_count=len(helper_sites),
            call_count_interpretation="Syntactic sites, not dynamic execution count")
    observed = [["HelperB.Prove", "HelperA.Prove"]] if files["HelperB.dfy"]["helper_call_site_count"] else []
    return dict(files=files, exact_changed_files=[n for n,v in files.items() if v["exact_changed"]],
        token_changed_files=[n for n,v in files.items() if v["tokens_changed"]],
        observed_helper_edges=observed, declared_target_dependencies=GRAPH,
        closure_basis="Frozen declared module graph; observed call use does not change primary scores or closure")


def declaration_outcomes(evidence, replay):
    """Expose the already validated named CSV units, including supplied providers."""
    rows = {}
    for text in evidence["csv"].values():
        for row in csv.DictReader(io.StringIO(text)):
            match = replay.target_metrics.NAME.fullmatch(row[replay.target_metrics.HEADER[0]])
            require(match is not None, "Unrecognized named declaration")
            symbol, kind, batch = match.groups()
            rows.setdefault(symbol, []).append(dict(unit=kind, assertion_batch=int(batch) if batch else None,
                passed=row[replay.target_metrics.HEADER[1]] == "Passed"))
    return {symbol:dict(role="helper" if symbol.startswith("Helper") else "client" if symbol.startswith("Client") else "provider",
        all_units_passed=all(row["passed"] for row in values), units=values) for symbol,values in sorted(rows.items())}


def summarize(rows, plan):
    def counts(selected):
        return dict(trials=len(selected), admitted=sum(x["admitted"] for x in selected),
                    strict_passes=sum(x["verified"] for x in selected), promoted=sum(x["promoted"] for x in selected),
                    outcomes=dict(sorted(Counter(x["outcome"] for x in selected).items())))
    cells = {}
    for instance in plan["semantic_instances"]:
        for sharing in plan["sharing_conditions"]:
            for arm in plan["feedback_conditions"]:
                selected = [x for x in rows if (x["semantic_instance"], x["sharing"], x["feedback_condition"]) == (instance, sharing, arm)]
                require(len(selected) == 4, "Missing balanced cell")
                cells["/".join((instance, sharing, arm))] = counts(selected)
    pairs = []
    for parent in sorted({x["parent_id"] for x in rows}):
        for replicate in (1, 2, 3, 4):
            group = {x["feedback_condition"]: x for x in rows if x["parent_id"] == parent and x["replicate"] == replicate}
            require(set(group) == set(plan["feedback_conditions"]), "Incomplete descriptive feedback pair")
            diagnostic, notice = group["verifier_diagnostics"], group["failure_notice_only"]
            category = ("both_verified" if diagnostic["verified"] and notice["verified"] else
                        "diagnostics_only_verified" if diagnostic["verified"] else
                        "notice_only_verified" if notice["verified"] else "neither_verified")
            pairs.append(dict(parent_id=parent, replicate=replicate, category=category,
                              diagnostics_trial=diagnostic["trial_id"], notice_trial=notice["trial_id"],
                              diagnostics_outcome=diagnostic["outcome"], notice_outcome=notice["outcome"]))
    return dict(overall=counts(rows), cells=cells,
                by_instance={name: counts([r for r in rows if r["semantic_instance"] == name]) for name in plan["semantic_instances"]},
                by_architecture={name: counts([r for r in rows if r["sharing"] == name]) for name in plan["sharing_conditions"]},
                by_task={name: counts([r for r in rows if r["task_id"] == name]) for name in sorted(TASK_IDS)},
                by_feedback={name: counts([r for r in rows if r["feedback_condition"] == name]) for name in plan["feedback_conditions"]},
                descriptive_feedback_pairs=pairs, pair_outcomes=dict(sorted(Counter(p["category"] for p in pairs).items())))


def review(root=ROOT):
    root = Path(root).resolve()
    out, window, snapshot, receipt, before = audit_inventories(root)
    runtime, scope = audit_freezes(root, out, window)
    with replay_runtime(out) as r:
        plan, parents, trials = r.validate_bundle(out)
        require(len(trials) == CALLS and set(parents) == TASK_IDS and plan["unique_semantic_instances"] == 4
                and len({t["request_sha256"] for t in trials}) == 8, "Study counts differ")
        global_ledger, status = audit_session(out, window, runtime, scope, trials, receipt, snapshot)
        launch = audit_launch(out, window, runtime)
        ledger = load(out / "requests/ledger.json")
        reservations = ledger["reservations"]
        require(ledger["schema"] == "bounded-requests-v1" and ledger["closed"] is True
                and ledger["closed_reason"] == "finished" and ledger["limit"] == CALLS
                and ledger["deadline"] == DEADLINE and len(reservations) == CALLS, "Local ledger incomplete")
        require(set(inventory(out / "requests")) == {"ledger.json"} | {f"response-{i:03}.json" for i in range(1, CALLS + 1)},
                "Unaccounted local response evidence")
        results = load(out / "results.json")
        require(isinstance(results, list) and len(results) == CALLS, "Incomplete results")
        rows, seen, tokens, revisions = [], set(), Counter(), set()
        original_metrics = {}
        protected = boundaries = 0
        for i, (reservation, trial) in enumerate(zip(reservations, trials), 1):
            parent, task, base, template = r.parent_parts(out, trial)
            folder = out / trial["trial_id"]
            result = load(folder / "result.json")
            require(result == results[i-1] and all(result[k] == v for k, v in trial.items())
                    and load(folder / "trial.json") == trial and load(folder / "task.json") == task,
                    "Trial identity/order differs")
            require(result["outcome"] in r.NORMAL_OUTCOMES and result["stop"] is False, "Receipt claims completed stopped batch")
            payload = load(out / "frozen-001" / trial["request_path"])
            require(reservation["prompt"] == payload == load(folder / "request.json")
                    and sha(folder / "request.json") == trial["request_sha256"]
                    and set(payload) == {"modelId", "system", "messages", "inferenceConfig"}
                    and payload["modelId"] == MODEL and payload["inferenceConfig"] == MODEL_SETTINGS["inference_config"],
                    "Exact frozen request/model differs")
            require(reservation["task_id"] == task["task_id"] and reservation["attempt_id"] == trial["trial_id"]
                    and reservation["sequence"] == i and reservation["status"] == "COMPLETED", "Local slot identity differs")
            global_row = global_ledger["reservations"][GLOBAL_OFFSET+i-1]
            require(START <= finite(reservation["reserved_at_epoch"], "local reservation time")
                    <= finite(reservation["dispatch_started_at_epoch"], "local dispatch time")
                    <= global_row["reserved_at_epoch"] < DEADLINE, "Local/global dispatch order differs")
            initial = load(folder / "initial.json")
            require(initial["source_sha256"] == parent["source_sha256"] and initial["reused_original_verification"] is True
                    and initial["new_verifier_runs"] == 0 and initial["evidence_path"] == parent["original_verifier_path"]
                    and initial["evidence_sha256"] == sha(out / "frozen-001" / parent["original_verifier_path"]),
                    "Original failure provenance differs")
            if task["task_id"] not in original_metrics:
                original = load(out / "frozen-001" / parent["original_verifier_path"])
                require(original["source_sha256"] == hashes(base) and r.outcome_for_evidence(original) == "PROOF_FAILURE",
                        "Original failure source/category differs")
                original_score, stopped = r.measurement(original, task, root=out)
                require(not stopped and original_score["available"], "Original named metrics unavailable")
                original_metrics[task["task_id"]] = original_score
            parent_score = original_metrics[task["task_id"]]
            failing_files = [name for name in task["editable_files"]
                             if not parent_score["local_targets"][name[:-4] + ".Prove"]]
            response = load(out / "requests" / f"response-{i:03}.json")
            require(response == load(folder / "response.json") == load(window / "budget/requests" / f"response-{GLOBAL_OFFSET+i:03}.json"),
                    "Global/local/trial response copies differ")
            audit_response(response, result, seen)
            tokens.update(response["usage"])
            row = dict(trial, outcome=result["outcome"], request_id=response["request_id"], usage=response["usage"],
                       admitted=False, verified=False, promoted=False, evidence_directory="model-001/" + trial["trial_id"],
                       original_target_metrics=parent_score, originally_failing_helper_files=failing_files)
            extraction = load(folder / "extraction.json")
            edited = evidence = None
            if response["stop_reason"] == "max_tokens":
                require(result["outcome"] == "OUTPUT_TRUNCATED" and extraction == dict(accepted=False, stage="truncation"),
                        "Truncation outcome differs")
            else:
                try:
                    edited, decision = r.decode(response["text"], out, trial)
                except r.OutputRejected as error:
                    require(result["outcome"] == "OUTPUT_REJECTED" and extraction == dict(accepted=False, stage=error.stage,
                            error_type=type(error.__cause__).__name__, reason=str(error)), "Output extraction replay differs")
                    row.update(rejection_stage=error.stage, rejection_reason=str(error))
                else:
                    require(extraction == dict(accepted=True, **decision), "Exact body guard replay differs")
                    require(source_files(folder / "candidate") == edited and load(folder / "candidate-hashes.json") ==
                            dict(parent_sha256=hashes(base), candidate_sha256=hashes(edited)), "Candidate bytes differ")
                    row["admitted"] = True
                    guard, _ = r.policy(out)
                    for name, original in base.items():
                        if name not in task["editable_files"]:
                            require(edited[name] == original, "Protected source changed")
                            protected += 1
                    edits = body_review(guard, task, template, base, edited, decision)
                    boundaries += len(edits["files"])
                    row.update(body_edits=edits, body_edit_classification={n:v["edit_classification"] for n,v in edits["files"].items()},
                        file_selection=dict(
                            token_changed_originally_failing_files=[n for n in edits["token_changed_files"] if n in failing_files],
                            token_changed_other_eligible_files=[n for n in edits["token_changed_files"] if n not in failing_files],
                            unchanged_originally_failing_files=[n for n in failing_files if not edits["files"][n]["exact_changed"]],
                            interpretation="Original named verification failures and syntactic edit locations; not necessary edits or semantic minimality"))
                    evidence = load(folder / "verification.json")
                    outcome, metrics, diagnostics = audit_verifier(folder, evidence, edited, task, out, r, result)
                    row.update(verifier_outcome=outcome, target_metrics=metrics, diagnostic_categories=diagnostics,
                               named_declarations=declaration_outcomes(evidence,r) if metrics["available"] else {},
                               verified=outcome == "VERIFIED" and metrics["available"], promoted=outcome == "VERIFIED" and metrics["available"])
            if not row["admitted"]:
                require(not any((folder / name).exists() for name in ("candidate", "candidate-hashes.json", "verification.json", "target-metrics.json", "raw-csv")),
                        "Rejected/truncated response has candidate/verifier evidence")
            first, final = audit_revision(folder, initial, base, task, edited if row["promoted"] else None, evidence)
            require(first not in revisions and (final == first or final not in revisions), "Reused revision identity across trials")
            revisions.update((first, final))
            rows.append(row)
        summary = load(out / "summary.json")
        expected_summary = dict(maximum_calls=CALLS, reserved_calls=CALLS, dispatch_started=CALLS,
                                completed_responses=CALLS, verified=sum(r["verified"] for r in rows),
                                fatal_error_type=None, all_trials_processed=True, unused_calls_not_reassigned=0, results=results)
        require(summary == expected_summary, "Run summary/counts differ")
        log = (window / f"session-{launch['environment']['job_id']}.log").read_text()
        printed = re.findall(r"^(repair-selection-\d{2}) ([A-Z_]+)$", log, re.M)
        require(printed == [(r["trial_id"], r["outcome"]) for r in rows], "Scheduler stdout trial inventory differs")
        report = dict(schema="repodisco-repair-selection-result-review-v1", batch_id=BATCH, all_evidence_checks_passed=True,
                      calls_reserved=CALLS, global_calls_reserved=GLOBAL_CALLS, global_sequences=[GLOBAL_OFFSET+1, GLOBAL_CALLS],
                      predecessor_ledger_sha256=PREVIOUS_LEDGER_SHA, predecessor_completion_sha256=PREVIOUS_COMPLETION_SHA,
                      unique_returned_requests=len(seen), zero_sdk_retries=True, no_model_or_verifier_reruns=True,
                      proposal_freeze_sha256=PROPOSAL_SHA, runtime_freeze_sha256=RUNTIME_SHA,
                      completion_sha256=sha(out / "completion.json"), snapshot_sha256=sha(window / "snapshot-manifest.json"),
                      transfer_sha256=sha(root / "transfer-001.json"), snapshot_utc=snapshot["utc"],
                      window_status_at_snapshot=status, window_terminal_reason=global_ledger["terminal_reason"],
                      scheduler=launch, tokens=dict(tokens), protected_file_comparisons=protected, protected_body_boundaries=boundaries,
                      unique_semantic_instances=4, unique_failing_workspaces=4, fresh_independent_responses=CALLS,
                      interpretation_limits=["Constructed development faults; not natural failure prevalence.",
                          "Four semantic instances; the 32 responses are not 32 independent tasks.",
                          "Pairs match parent and replicate index, but responses use independent contexts.",
                          "One fixed pipeline architecture; no sharing/depth treatment or causal sharing/depth claim.",
                          "Declared graph closure is separate from observed call sites and is not minimal proof dependence.",
                          "Token changes are not a claim of semantic change or minimal repair.",
                          "No held-out/generalization claim; prior experiments are not rescored."],
                      **summarize(rows, plan), rows=rows)
    _, _, _, _, after = audit_inventories(root)
    require(before == after, "Evidence changed during offline review")
    return report


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=ROOT)
    parser.add_argument("--output", type=Path, help="Optional NEW review JSON outside the immutable evidence directories")
    args = parser.parse_args()
    result = review(args.root)
    if args.output:
        target = args.output.resolve()
        require(all(not target.is_relative_to((args.root / name).resolve()) for name in ("model-001", "window-evidence-001", "frozen-001")),
                "Never write review artifacts into immutable evidence")
        with target.open("x") as stream:
            json.dump(result, stream, indent=2, sort_keys=True, allow_nan=False)
            stream.write("\n")
    print(json.dumps({k: v for k, v in result.items() if k not in ("rows", "descriptive_feedback_pairs")}, indent=2, sort_keys=True))
