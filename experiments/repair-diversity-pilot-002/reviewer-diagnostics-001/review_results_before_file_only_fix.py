"""Fail-closed offline audit of the first window-owned 32-request repair batch.

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
BATCH = "repair-diversity-pilot-002"
WINDOW = "repodisco-research-20261114"
CALLS = 32
DEADLINE = 1794801912.0
START = 1794715512.0
PROPOSAL_SHA = "ef318bdd394b11cc981c15165bcc8cbf1ffdc06945582bc025afe7b27cd317e8"
RUNTIME_SHA = "ca24194ab90c932e0c514c1b390a80dd999645ccf07a9c937ea176f82b701b44"
SCOPE_SHA = "a649bcfca3be0b1120f8c7810778a344dd6fbf395dbeb6b6e362a20c5541ed01"
ADMISSION_SHA = "de2516e216666522cb6ef3eaac6f35bb67f716fb31a4ee917a8ba688e8a9f73f"
LAUNCH_SHA = "30f51639352abb451321a847aebc37ab8a230392fdfcc15a82eb8a2ba3bdd1cd"
MODEL = "global.anthropic.claude-opus-4-5-20251101-v1:0"
MODEL_SETTINGS = dict(model_id=MODEL, region="us-east-1",
                      inference_config=dict(temperature=1.0, maxTokens=4096))
COMMAND = ["timeout", "-k", "5s", "60s", "dafny", "verify",
           "--verify-included-files", "--log-format", "csv", "All.dfy"]
DIGEST = re.compile(r"[0-9a-f]{64}\Z")
REVISION = re.compile(r"[0-9a-f]{32}\Z")


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
    require(freeze["source_commit"] == "b7760712027c4fee16b217592d4d20d400581265"
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


def audit_session(out, window, runtime, scope, trials, receipt, snapshot):
    admission = load(out / "admission.json")
    require(sha(out / "admission.json") == ADMISSION_SHA, "Reviewed admission differs")
    bundle_pins = {"frozen-001/" + n: h for n, h in inventory(out / "frozen-001").items()}
    bundle_pins.update({"inputs/" + n: h for n, h in inventory(out / "inputs").items()})
    bundle_pins.update({n: sha(out / n) for n in ("batch-binding.json", "runtime-freeze.json")})
    expected = dict(schema="repodisco-session-descriptor-v1", sequence=1, previous_descriptor_sha256="0" * 64,
                    batch_id=BATCH, handler_id="repair-v1", handler_binding_sha256=digest(canonical(runtime["runtime_sha256"])),
                    artifact_directory=BATCH, freeze_path="frozen-001/freeze.json", freeze_sha256=PROPOSAL_SHA,
                    runtime_path="runtime-freeze.json", runtime_sha256=RUNTIME_SHA, input_sha256=bundle_pins,
                    slots=[dict(trial_id=t["trial_id"], request_path="frozen-001/" + t["request_path"],
                                request_sha256=t["request_sha256"]) for t in trials], max_calls=CALLS, sdk_total_max_attempts=1)
    require(admission == expected, "Frozen admission/input/order binding differs")
    queued = window / "session/queue" / ("0001-" + BATCH + ".json")
    require(inventory(window / "session/queue") == {queued.name: sha(queued)}
            and load(queued) == admission and sha(queued) == receipt["descriptor_sha256"], "Queue/receipt binding differs")
    trial_ids = [t["trial_id"] for t in trials]
    require(receipt["completed_trials"] == trial_ids, "Completion trial order differs")
    events_folder = window / "session/events"
    event_pins = inventory(events_folder)
    require(list(event_pins) == [f"{i:05}.json" for i in range(1, len(event_pins) + 1)], "Session event sequence incomplete")
    events = [load(events_folder / name) for name in event_pins]
    require(events and load(window / "session/status.json") == events[-1], "Session status is not last durable event")
    previous_time = START
    previous_count = 0
    for i, event in enumerate(events, 1):
        timestamp = finite(event["at_epoch"], "event time")
        require(event["schema"] == "repodisco-session-status-v1" and event["event_sequence"] == i
                and event["deadline_epoch"] == DEADLINE and timestamp >= previous_time
                and previous_count <= event["window_reservations"] <= CALLS, "Incoherent session event")
        require(event["completed_batch_ids"] in ([], [BATCH]) and event["active_batch_id"] in (None, BATCH),
                "Unexpected batch in session history")
        previous_time, previous_count = timestamp, event["window_reservations"]
    status = events[-1]
    require(status["completed_batch_ids"] == [BATCH] and status["active_batch_id"] is None
            and status["window_reservations"] == CALLS, "Batch not complete at window snapshot")
    require(any(e["phase"] == "completed" and e["reason"] == "batch_complete" for e in events), "Missing completion event")
    require(snapshot["session_still_running"] == (status["phase"] not in ("error", "closed")), "Snapshot process status differs")
    manifest = {k: admission[k] for k in ("batch_id", "freeze_sha256", "runtime_sha256", "max_calls", "sdk_total_max_attempts")}
    manifest["slots"] = [{k: slot[k] for k in ("trial_id", "request_sha256")} for slot in admission["slots"]]
    ledger = load(window / "budget/ledger.json")
    require(ledger["schema"] == "repodisco-window-budget-v1" and ledger["scope"] == scope
            and ledger["scope_sha256"] == digest(canonical(scope)), "Global ledger scope differs")
    require(ledger["batches"] == [dict(manifest=manifest, manifest_sha256=digest(canonical(manifest)))],
            "Unexpected global batch allocation")
    reservations = ledger["reservations"]
    require(len(reservations) == CALLS, "Expected exactly 32 global reservations")
    names = {f"{kind}-{i:03}.json" for i in range(1, CALLS + 1) for kind in ("request", "response")}
    require(set(inventory(window / "budget/requests")) == names, "Unaccounted global request evidence")
    ids = set()
    for i, (row, trial) in enumerate(zip(reservations, trials), 1):
        request_path = window / "budget/requests" / f"request-{i:03}.json"
        response_path = window / "budget/requests" / f"response-{i:03}.json"
        response = load(response_path)
        require(row["sequence"] == i and row["status"] == "COMPLETED" and row["batch_id"] == BATCH
                and row["trial_id"] == trial["trial_id"] and row["manifest_sha256"] == digest(canonical(manifest))
                and row["request_sha256"] == trial["request_sha256"] == sha(request_path)
                and row["response_sha256"] == sha(response_path), "Global slot/request/response binding differs")
        require(request_path.read_bytes() == (out / "frozen-001" / trial["request_path"]).read_bytes(), "Global request byte drift")
        require(START <= finite(row["reserved_at_epoch"], "reservation time")
                <= finite(row["dispatch_intent_at_epoch"], "dispatch time") < DEADLINE
                and row["dispatch_intent_at_epoch"] <= finite(row["returned_at_epoch"], "return time"), "Global dispatch deadline/order")
        rid = response.get("request_id")
        require(isinstance(rid, str) and rid and rid not in ids and row["request_id"] == rid
                and type(response.get("retry_attempts")) is int and response["retry_attempts"] == 0, "Global ID/retry evidence")
        ids.add(rid)
    require(receipt["request_ids"] == [r["request_id"] for r in reservations], "Receipt request IDs differ")
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
        prefix = "batches/" + BATCH + "/"
        if name.startswith(prefix):
            path = out / name[len(prefix):]
        elif name.startswith("execution-runtime/"):
            tail = name[len("execution-runtime/"):]
            path = out / tail if tail == "runtime-freeze.json" else out / "runtime" / tail
        elif name.startswith("runtime/"):
            path = out / "window-runtime" / name[len("runtime/"):]
        elif name.startswith("session-runtime-002/"):
            path = out / "session-runtime" / name[len("session-runtime-002/"):]
        elif name == "admissions/000001.json":
            path = out / "admission.json"
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
    require(inventory(store / "attempts") == {} and (store / "write.lock").read_bytes() == b"", "Unexpected store writer artifacts")
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
                require(len(selected) == 2, "Missing balanced cell")
                cells["/".join((instance, sharing, arm))] = counts(selected)
    pairs = []
    for parent in sorted({x["parent_id"] for x in rows}):
        for replicate in (1, 2):
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
                by_sharing={name: counts([r for r in rows if r["sharing"] == name]) for name in plan["sharing_conditions"]},
                by_feedback={name: counts([r for r in rows if r["feedback_condition"] == name]) for name in plan["feedback_conditions"]},
                descriptive_feedback_pairs=pairs, pair_outcomes=dict(sorted(Counter(p["category"] for p in pairs).items())))


def review(root=ROOT):
    root = Path(root).resolve()
    out, window, snapshot, receipt, before = audit_inventories(root)
    runtime, scope = audit_freezes(root, out, window)
    with replay_runtime(out) as r:
        plan, parents, trials = r.validate_bundle(out)
        require(len(trials) == CALLS and len(parents) == 8 and plan["unique_semantic_instances"] == 4
                and len({t["request_sha256"] for t in trials}) == 16, "Study counts differ")
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
            global_row = global_ledger["reservations"][i-1]
            require(START <= finite(reservation["reserved_at_epoch"], "local reservation time")
                    <= finite(reservation["dispatch_started_at_epoch"], "local dispatch time")
                    <= global_row["reserved_at_epoch"] < DEADLINE, "Local/global dispatch order differs")
            initial = load(folder / "initial.json")
            require(initial["source_sha256"] == parent["source_sha256"] and initial["reused_original_verification"] is True
                    and initial["new_verifier_runs"] == 0 and initial["evidence_path"] == parent["original_verifier_path"]
                    and initial["evidence_sha256"] == sha(out / "frozen-001" / parent["original_verifier_path"]),
                    "Original failure provenance differs")
            response = load(out / "requests" / f"response-{i:03}.json")
            require(response == load(folder / "response.json") == load(window / "budget/requests" / f"response-{i:03}.json"),
                    "Global/local/trial response copies differ")
            audit_response(response, result, seen)
            tokens.update(response["usage"])
            row = dict(trial, outcome=result["outcome"], request_id=response["request_id"], usage=response["usage"],
                       admitted=False, verified=False, promoted=False, evidence_directory="model-001/" + trial["trial_id"])
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
                    bodies, classes = [], {}
                    for name, original in base.items():
                        if name not in task["editable_files"]:
                            require(edited[name] == original, "Protected source changed")
                            protected += 1
                        else:
                            prefix, suffix = guard.split_seed(template[name].decode())
                            text = edited[name].decode()
                            require(text.startswith(prefix) and text.endswith(suffix), "Protected helper contract changed")
                            boundaries += 1
                            old_body, new_body = original.decode()[len(prefix):-len(suffix)], text[len(prefix):-len(suffix)]
                            bodies.append(new_body)
                            lines = lambda value: [line.strip() for line in value.splitlines() if line.strip()]
                            classes[name] = "unchanged" if old_body == new_body else "reorder_only" if Counter(lines(old_body)) == Counter(lines(new_body)) else "other_edit"
                    row.update(body_edit_classification=classes,
                               separate_bodies_identical=len(set(bodies)) == 1 if task["sharing"] == "separate" else None)
                    evidence = load(folder / "verification.json")
                    outcome, metrics, diagnostics = audit_verifier(folder, evidence, edited, task, out, r, result)
                    row.update(verifier_outcome=outcome, target_metrics=metrics, diagnostic_categories=diagnostics,
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
        printed = re.findall(r"^(repair-diversity-\d{2}) ([A-Z_]+)$", log, re.M)
        require(printed == [(r["trial_id"], r["outcome"]) for r in rows], "Scheduler stdout trial inventory differs")
        report = dict(schema="repodisco-repair-diversity-result-review-v1", batch_id=BATCH, all_evidence_checks_passed=True,
                      calls_reserved=CALLS, unique_returned_requests=len(seen), zero_sdk_retries=True, no_model_or_verifier_reruns=True,
                      proposal_freeze_sha256=PROPOSAL_SHA, runtime_freeze_sha256=RUNTIME_SHA,
                      completion_sha256=sha(out / "completion.json"), snapshot_sha256=sha(window / "snapshot-manifest.json"),
                      transfer_sha256=sha(root / "transfer-001.json"), snapshot_utc=snapshot["utc"],
                      window_status_at_snapshot=status, window_terminal_reason=global_ledger["terminal_reason"],
                      scheduler=launch, tokens=dict(tokens), protected_file_comparisons=protected, protected_body_boundaries=boundaries,
                      unique_semantic_instances=4, unique_failing_workspaces=8, fresh_independent_responses=CALLS,
                      interpretation_limits=["Constructed development faults; not natural failure prevalence.",
                          "Four semantic instances; the 32 responses are not 32 independent tasks.",
                          "Pairs match parent and replicate index, but responses use independent contexts.",
                          "Shared mode changes a forwarding dependency, editable body count and output size; no clean causal sharing/depth claim.",
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
