"""New pipeline reviewer tests using32 fake responses and the pinned prior ledger.

The first32 records are copied only as immutable predecessor evidence. The new
32 responses/CSV rows are synthetic, never research measurements. No provider,
credential, verification command, admission, or remote action is performed.
"""
from contextlib import redirect_stdout
import copy
import csv
from datetime import datetime, timezone
import io
import json
from pathlib import Path
import shutil
import tempfile
import unittest
from unittest.mock import patch

import review_results as q

WINDOW = q.ROOT.parents[1] / "research-window-20261114"
REPO = q.ROOT.parents[2]


def write(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(q.canonical(value) + b"\n")


def refresh_inventories(root):
    out, window = root / "model-001", root / "window-evidence-001"
    receipt = q.load(out / "completion.json")
    receipt["evidence_sha256"] = {n: h for n, h in q.inventory(out).items() if n != "completion.json"}
    write(out / "completion.json", receipt)
    shutil.copy2(out / "completion.json", window / "completions" / (q.BATCH + ".json"))
    actual = {"model-001/" + n: h for n, h in q.inventory(out).items()}
    actual.update({"window-evidence-001/" + n: h for n, h in q.inventory(window).items() if n != "snapshot-manifest.json"})
    state = q.load(window / "session/status.json")
    write(window / "snapshot-manifest.json", dict(utc=datetime.fromtimestamp(state["at_epoch"] + 1, timezone.utc).isoformat(), batch_id=q.BATCH,
          session_still_running=state["phase"] not in ("closed", "error"), credential_access=False, files=actual))
    actual["window-evidence-001/snapshot-manifest.json"] = q.sha(window / "snapshot-manifest.json")
    write(root / "transfer-001.json", dict(compressed_bytes=1, archive_sha256="0" * 64, files=actual))


def synthetic_archive(root):
    """Use the frozen collector with fakes; construct a second-batch snapshot."""
    out, window = root / "model-001", root / "window-evidence-001"
    shutil.copytree(q.ROOT / "frozen-001", root / "frozen-001")
    shutil.copytree(q.ROOT / "frozen-001", out / "frozen-001")
    frozen = q.load(out / "frozen-001/freeze.json")
    for name, h in frozen["repository_inputs_sha256"].items():
        source = REPO / name
        assert q.sha(source) == h
        target = out / "inputs" / name
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, target)
    shutil.copy2(WINDOW / "execution-runtime/runtime-freeze.json", out / "runtime-freeze.json")
    binding = dict(window_id=q.WINDOW, batch_id=q.BATCH, max_calls=32, authorized=True,
        automatic_retries=False, max_calls_per_trial=1, model_settings=q.MODEL_SETTINGS,
        proposal_freeze_sha256=q.PROPOSAL_SHA, runtime_freeze_sha256=q.RUNTIME_SHA)
    write(out / "batch-binding.json", binding)
    runtime = q.load(out / "runtime-freeze.json")
    trials = q.load(out / "frozen-001/trials.json")
    admission = dict(schema="repodisco-session-descriptor-v1", sequence=2,
        previous_descriptor_sha256=q.PREVIOUS_ADMISSION_SHA, batch_id=q.BATCH, handler_id="repair-v1",
        handler_binding_sha256=q.digest(q.canonical(runtime["runtime_sha256"])), artifact_directory=q.BATCH,
        freeze_path="frozen-001/freeze.json", freeze_sha256=q.PROPOSAL_SHA,
        runtime_path="runtime-freeze.json", runtime_sha256=q.RUNTIME_SHA,
        input_sha256=q.inventory(out), slots=[dict(trial_id=t["trial_id"],
        request_path="frozen-001/" + t["request_path"], request_sha256=t["request_sha256"]) for t in trials],
        max_calls=32, sdk_total_max_attempts=1)
    write(out / "admission.json", admission)
    for name in runtime["runtime_sha256"]:
        target = out / "runtime" / name
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(WINDOW / "execution-runtime" / name, target)
    for original, archive in (("runtime", "window-runtime"), ("session-runtime-002", "session-runtime")):
        shutil.copytree(WINDOW / original, out / archive, ignore=shutil.ignore_patterns("__pycache__"))
    shutil.copy2(WINDOW / "scope.json", out / "scope.json")
    env = q.load(q.PREVIOUS_ROOT / "model-001/environment.json")
    write(out / "environment.json", env)
    kinds = {0: "PROOF_FAILURE_B", 1: "PROOF_FAILURE_A", 2: "OUTPUT_REJECTED", 3: "WARNING_ONLY", 4: "FRONTEND_ERROR", 5: "OUTPUT_TRUNCATED", 6: "BODY_REJECTED", 7: "NO_HELPER_CALL"}
    responses = []
    prior = q.load(q.PREVIOUS_ROOT / "window-evidence-001/budget/ledger.json")
    last_event = q.load(q.PREVIOUS_ROOT / "window-evidence-001/session/status.json")
    now = max(last_event["at_epoch"], max(r["returned_at_epoch"] for r in prior["reservations"])) + 10
    settings = q.load(out / "frozen-001/settings.json")
    with q.replay_runtime(out) as r:
        def response(payload):
            index = len(responses); trial = trials[index]
            assert payload == q.load(out / "frozen-001" / trial["request_path"])
            parent, task, base, template = r.parent_parts(out, trial)
            family = settings["task_groups"][trial["task_id"]]
            reference = out / "inputs" / settings["source_roots"][family] / "fixtures" / trial["task_id"] / "reference"
            guard, _ = r.policy(out)
            bodies = {}
            for name in task["editable_files"]:
                prefix, suffix = guard.split_seed(template[name].decode())
                source = base[name].decode() if kinds.get(index, "").startswith("PROOF_FAILURE") else (reference / name).read_text()
                bodies[name] = source[len(prefix):-len(suffix)]
            if kinds.get(index) == "NO_HELPER_CALL":
                bodies["HelperB.dfy"] = "    assert true;\n"  # Fake verifier below; not a real proof claim.
            text = json.dumps(bodies)
            if kinds.get(index) == "OUTPUT_REJECTED": text = "unstructured fake response"
            elif kinds.get(index) == "BODY_REJECTED": text = json.dumps({name:"assume false;" for name in bodies})
            content = [dict(text=text)]; usage = dict(inputTokens=100, outputTokens=10, totalTokens=110)
            stop = "max_tokens" if kinds.get(index) == "OUTPUT_TRUNCATED" else "end_turn"
            rid = f"offline-second-{index + 1}"
            raw = dict(output=dict(message=dict(role="assistant", content=content)), usage=usage, stopReason=stop,
                ResponseMetadata=dict(RequestId=rid, RetryAttempts=0))
            result = dict(text=text,content=content,usage=usage,stop_reason=stop,request_id=rid,retry_attempts=0,raw_response=raw)
            responses.append(result); return result

        def verifier(files):
            index = len(responses) - 1; kind = kinds.get(index, "VERIFIED"); trial = trials[index]
            scope = q.load(out / "frozen-001/measurement-scope.json")["tasks"][trial["task_id"]]
            buffer = io.StringIO(); writer = csv.writer(buffer, lineterminator="\r\n"); writer.writerow(r.target_metrics.HEADER)
            total = 0; failed = "HelperB.Prove" if kind == "PROOF_FAILURE_B" else "HelperA.Prove" if kind == "PROOF_FAILURE_A" else None
            for symbol, units in scope["expected_units"].items():
                for unit in units:
                    total += 1
                    writer.writerow([f"{symbol} ({unit})", "Failed" if symbol == failed else "Passed", "0:00:00.001", "1", "0"])
            csv_files = {"TestResults/offline-fake.csv": buffer.getvalue()}; errors = int(failed is not None)
            text = f"Dafny program verifier finished with {total-errors} verified, {errors} errors\n"
            if failed: text = failed.split('.')[0]+".dfy(1,1): Error: a precondition for this call could not be proved\n"+text
            if kind == "WARNING_ONLY": text = "HelperA.dfy(1,1): Warning: FAKE trigger\n"+text+"--allow-warnings is false\n"
            if kind == "FRONTEND_ERROR":
                text = "HelperA.dfy(1,1): Error: FAKE parse diagnostic\n1 parse errors detected in All.dfy\n"; csv_files = {}
            return dict(command=q.COMMAND, exit_code=4 if errors else 2 if kind in ("WARNING_ONLY","FRONTEND_ERROR") else 0,
                stdout=text,stderr="",source_sha256=q.hashes(files),attempts=1,model_calls=0,csv=csv_files,
                csv_sha256={n:q.digest(t.encode()) for n,t in csv_files.items()})

        with patch("subprocess.run", side_effect=AssertionError("Real subprocess forbidden")), redirect_stdout(io.StringIO()):
            r.collect(out,response,verifier,q.DEADLINE,root=out,clock=lambda:now,check_runtime=False)
    previous_window = q.PREVIOUS_ROOT / "window-evidence-001"
    window.mkdir()
    for name in ("scope.json","launch-manifest.json","session.sbatch","session_ops.py","execution-preflight-001.json","stage-002.json","submission-001.json","accounting-snapshot.txt"):
        shutil.copy2(previous_window/name,window/name)
    (window/"submission-001.lock").write_bytes(b"")
    results = q.load(out/"results.json")
    job = env["job_id"]
    (window/f"session-{job}.log").write_text((previous_window/f"session-{job}.log").read_text()+"".join(row["trial_id"]+" "+row["outcome"]+"\n" for row in results))
    shutil.copy2(previous_window/f"session-{job}.err",window/f"session-{job}.err")
    shutil.copytree(previous_window/"session/events",window/"session/events")
    shutil.copytree(previous_window/"session/queue",window/"session/queue")
    write(window/"session/queue"/("0002-"+q.BATCH+".json"),admission)
    (window/"admissions").mkdir(); (window/"completions").mkdir()
    shutil.copy2(q.PREVIOUS_ROOT/"model-001/admission.json",window/"admissions/000001.json")
    shutil.copy2(out/"admission.json",window/"admissions/000002.json")
    shutil.copy2(q.PREVIOUS_ROOT/"model-001/completion.json",window/"completions"/(q.PREVIOUS_BATCH+".json"))
    shutil.copytree(previous_window/"budget/requests",window/"budget/requests")
    manifest = {k:admission[k] for k in ("batch_id","freeze_sha256","runtime_sha256","max_calls","sdk_total_max_attempts")}
    manifest["slots"] = [{k:s[k] for k in ("trial_id","request_sha256")} for s in admission["slots"]]
    rows = copy.deepcopy(prior["reservations"])
    for i,(trial,result) in enumerate(zip(trials,responses),q.GLOBAL_OFFSET+1):
        request = window/"budget/requests"/f"request-{i:03}.json"; shutil.copy2(out/"frozen-001"/trial["request_path"],request)
        returned=request.with_name(f"response-{i:03}.json"); write(returned,result)
        rows.append(dict(sequence=i,batch_id=q.BATCH,trial_id=trial["trial_id"],manifest_sha256=q.digest(q.canonical(manifest)),
            request_sha256=q.sha(request),reserved_at_epoch=now,dispatch_intent_at_epoch=now,returned_at_epoch=now,
            status="COMPLETED",response_sha256=q.sha(returned),request_id=result["request_id"]))
    ledger = copy.deepcopy(prior); ledger["batches"].append(dict(manifest=manifest,manifest_sha256=q.digest(q.canonical(manifest))))
    ledger["reservations"] = rows; write(window/"budget/ledger.json",ledger)
    state = copy.deepcopy(last_event); state.update(phase="completed",reason="batch_complete",event_sequence=state["event_sequence"]+1,
        at_epoch=now,completed_batch_ids=[q.PREVIOUS_BATCH,q.BATCH],active_batch_id=None,window_reservations=64)
    state["queued"].append(dict(sequence=2,batch_id=q.BATCH,descriptor_sha256=q.sha(out/"admission.json")))
    write(window/"session/events"/f"{state['event_sequence']:05}.json",state); write(window/"session/status.json",state)
    write(out/"completion.json",dict(batch_id=q.BATCH,descriptor_sha256=q.sha(out/"admission.json"),
        completed_trials=[t["trial_id"] for t in trials],request_ids=[r["request_id"] for r in responses],evidence_sha256={}))
    refresh_inventories(root)
    return q.sha(out/"admission.json")


class SchedulerNodeTests(unittest.TestCase):
    def test_single_short_or_full_hostname_matches_but_other_nodes_and_ranges_fail(self):
        host = "holy8a24107.rc.fas.harvard.edu"
        self.assertTrue(q.same_slurm_node(host, "holy8a24107"))
        self.assertTrue(q.same_slurm_node(host, host))
        self.assertTrue(q.same_slurm_node("holy8a24107", "holy8a24107"))
        for node in ("holy8a24108", "holy8a24107.other.example", "holy8a[24107-24108]",
                     "holy8a24107,holy8a24108", " holy8a24107", "holy8a24107 ", "", None):
            with self.subTest(node=node):
                self.assertFalse(q.same_slurm_node(host, node))


class BodyAnnotationTests(unittest.TestCase):
    def test_byte_whitespace_and_token_changes_are_distinct(self):
        self.assertEqual(q.classify_body_edit("assert true;", "assert true;", ["assert", "true", ";"], ["assert", "true", ";"]), "unchanged")
        self.assertEqual(q.classify_body_edit("assert true;", "  assert  true;\n", ["assert", "true", ";"], ["assert", "true", ";"]), "whitespace_only")
        self.assertEqual(q.classify_body_edit("assert true;", "assert false;", ["assert", "true", ";"], ["assert", "false", ";"]), "token_change")

    def test_nested_syntactic_sites_are_not_dynamic_execution_counts(self):
        tree = [["if", ["bool", True], [["call", "H.Prove", [["id", "x"]]]], []],
                ["forall", "i", ["call", "O.Fact", [["id", "i"]]]]]
        self.assertEqual([x["symbol"] for x in q.call_sites(tree)], ["H.Prove", "O.Fact"])
        self.assertEqual(q.call_sites([["assert", ["id", "H.Prove"]]]), [])


class ReviewerTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory()
        cls.base = Path(cls.temp.name) / "synthetic"
        cls.admission_sha = synthetic_archive(cls.base)

    @classmethod
    def tearDownClass(cls):
        cls.temp.cleanup()

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name) / "archive"
        patcher = patch.object(q, "ADMISSION_SHA", self.admission_sha)
        patcher.start(); self.addCleanup(patcher.stop)
        shutil.copytree(self.base, self.root)

    def test_complete_fake_archive_replays_all_failure_categories_and_closed_clients(self):
        with patch("subprocess.run", side_effect=AssertionError("Offline review cannot execute")):
            result = q.review(self.root)
        self.assertEqual(result["overall"]["strict_passes"], 25)
        self.assertEqual(result["overall"]["outcomes"], dict(FRONTEND_ERROR=1, OUTPUT_REJECTED=2, OUTPUT_TRUNCATED=1, PROOF_FAILURE=2, VERIFIED=25, WARNING_ONLY=1))
        self.assertEqual(result["rows"][0]["target_metrics"]["supplied_clients_local"]["passed"], 2)
        self.assertEqual(result["rows"][0]["target_metrics"]["supplied_clients_closed"]["passed"], 0)
        self.assertEqual(result["rows"][0]["diagnostic_categories"], ["precondition"])
        self.assertEqual(len(result["descriptive_feedback_pairs"]), 16)
        first, second, no_call = result["rows"][0], result["rows"][1], result["rows"][7]
        self.assertEqual(first["originally_failing_helper_files"], ["HelperB.dfy"])
        self.assertEqual(second["originally_failing_helper_files"], ["HelperA.dfy"])
        self.assertTrue(first["target_metrics"]["local_targets"]["HelperA.Prove"])
        self.assertFalse(first["target_metrics"]["local_targets"]["HelperB.Prove"])
        self.assertFalse(second["target_metrics"]["local_targets"]["HelperA.Prove"])
        self.assertTrue(second["target_metrics"]["local_targets"]["HelperB.Prove"])
        self.assertFalse(second["target_metrics"]["dependency_closed_targets"]["HelperB.Prove"])
        self.assertTrue(second["named_declarations"]["HelperB.Prove"]["all_units_passed"])
        self.assertEqual(second["named_declarations"]["HelperB.Prove"]["role"], "helper")
        self.assertEqual(second["named_declarations"]["ClientA.Target"]["role"], "client")
        self.assertEqual(second["file_selection"]["unchanged_originally_failing_files"], ["HelperA.dfy"])
        self.assertEqual(no_call["outcome"], "VERIFIED")  # Synthetic evidence only.
        self.assertEqual(no_call["body_edits"]["files"]["HelperB.dfy"]["helper_call_site_count"], 0)
        self.assertEqual(no_call["body_edits"]["observed_helper_edges"], [])
        self.assertEqual(no_call["body_edits"]["declared_target_dependencies"], q.GRAPH)
        self.assertTrue(any(row["role"] == "provider" for row in no_call["named_declarations"].values()))
        self.assertEqual(result["global_calls_reserved"], 64)
        self.assertEqual(result["global_sequences"], [33, 64])

    def test_duplicate_global_id_fails_despite_refreshed_outer_inventories(self):
        path = self.root / "window-evidence-001/budget/ledger.json"
        ledger = q.load(path)
        ledger["reservations"][33]["request_id"] = ledger["reservations"][32]["request_id"]
        write(path, ledger)
        refresh_inventories(self.root)
        with self.assertRaisesRegex(ValueError, "Global ID/retry"):
            q.review(self.root)

    def test_published_predecessor_is_immutable_even_with_refreshed_outer_hashes(self):
        path = self.root / "window-evidence-001/budget/ledger.json"
        ledger = q.load(path)
        ledger["reservations"][0]["returned_at_epoch"] += 0.01
        write(path, ledger)
        refresh_inventories(self.root)
        with self.assertRaisesRegex(ValueError, "Published predecessor reservations changed"):
            q.review(self.root)

    def test_new_request_id_cannot_reuse_previous_batch_id(self):
        path = self.root / "window-evidence-001/budget/ledger.json"
        ledger = q.load(path)
        response_path = self.root / "window-evidence-001/budget/requests/response-033.json"
        response = q.load(response_path)
        prior_id = ledger["reservations"][0]["request_id"]
        response["request_id"] = prior_id
        response["raw_response"]["ResponseMetadata"]["RequestId"] = prior_id
        write(response_path, response)
        ledger["reservations"][32]["request_id"] = prior_id
        ledger["reservations"][32]["response_sha256"] = q.sha(response_path)
        write(path, ledger)
        refresh_inventories(self.root)
        with self.assertRaisesRegex(ValueError, "Global ID/retry"):
            q.review(self.root)

    def test_later_deadline_close_does_not_invalidate_completed_batch(self):
        folder = self.root / "window-evidence-001"
        state = q.load(folder / "session/status.json")
        state.update(phase="closed", reason="deadline", at_epoch=q.DEADLINE + 60,
                     event_sequence=state["event_sequence"] + 1)
        write(folder / "session/events" / f"{state['event_sequence']:05}.json", state)
        write(folder / "session/status.json", state)
        ledger = q.load(folder / "budget/ledger.json")
        ledger["terminal_reason"] = "deadline"
        write(folder / "budget/ledger.json", ledger)
        refresh_inventories(self.root)
        result = q.review(self.root)
        self.assertEqual(result["overall"]["strict_passes"], 25)
        self.assertEqual(result["window_status_at_snapshot"]["phase"], "closed")
        self.assertGreater(result["window_status_at_snapshot"]["at_epoch"], q.DEADLINE)

    def test_missing_archive_is_distinct_from_recorded_execution_stop(self):
        (self.root / "model-001/completion.json").unlink()
        with self.assertRaises(q.IncompleteEvidence):
            q.review(self.root)
        summary_path = self.root / "model-001/summary.json"
        summary = q.load(summary_path)
        summary["fatal_error_type"] = "TransportFailure"
        write(summary_path, summary)
        with self.assertRaises(q.ExecutionStopped):
            q.review(self.root)
        summary["fatal_error_type"] = None
        write(summary_path, summary)
        ledger_path = self.root / "window-evidence-001/budget/ledger.json"
        ledger = q.load(ledger_path)
        ledger["reservations"][-1]["status"] = "AMBIGUOUS"
        write(ledger_path, ledger)
        with self.assertRaises(q.ExecutionStopped):
            q.review(self.root)

    def test_missing_named_csv_fails_even_when_csv_hash_is_updated(self):
        folder = self.root / "model-001/repair-selection-10"
        evidence = q.load(folder / "verification.json")
        name, text = next(iter(evidence["csv"].items()))
        text = "\r\n".join(text.split("\r\n")[:-2]) + "\r\n"
        evidence["csv"][name] = text
        evidence["csv_sha256"][name] = q.digest(text.encode())
        write(folder / "verification.json", evidence)
        (folder / "raw-csv" / name).write_bytes(text.encode())
        refresh_inventories(self.root)
        with self.assertRaisesRegex(ValueError, "metric replay"):
            q.review(self.root)

    def test_code_four_without_proof_summary_cannot_be_rescored_as_failure(self):
        path = self.root / "model-001/repair-selection-01/verification.json"
        evidence = q.load(path)
        evidence["stdout"] = "Unexpected infrastructure output\n"
        write(path, evidence)
        refresh_inventories(self.root)
        with self.assertRaises(ValueError):
            q.review(self.root)

    def test_accepted_contract_change_fails_even_with_updated_revision_hash(self):
        folder = self.root / "model-001/repair-selection-10"
        revision = q.load(folder / "store/HEAD.json")["revision"]
        target = folder / "store/revisions" / revision
        source = target / "files/ClientA.dfy"
        source.write_bytes(source.read_bytes() + b"\n// unexpected edit\n")
        meta = q.load(target / "revision.json")
        meta["source_sha256"]["ClientA.dfy"] = q.sha(source)
        write(target / "revision.json", meta)
        refresh_inventories(self.root)
        with self.assertRaisesRegex(ValueError, "Accepted revision source"):
            q.review(self.root)

    def test_runtime_mutation_missing_receipt_and_extra_transfer_file_fail_closed(self):
        path = self.root / "model-001/runtime/target_metrics.py"
        path.write_bytes(path.read_bytes() + b"\n# altered\n")
        refresh_inventories(self.root)
        with self.assertRaisesRegex(ValueError, "Archived runtime"):
            q.review(self.root)
        path = self.root / "model-001/completion.json"
        path.unlink()
        with self.assertRaises(ValueError):
            q.review(self.root)
        (self.root / "window-evidence-001/unaccounted.txt").write_text("unexpected")
        with self.assertRaises(ValueError):
            q.review(self.root)


if __name__ == "__main__":
    unittest.main(verbosity=2)
