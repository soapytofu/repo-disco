"""Offline synthetic-evidence tests; injected fake transport/verifier only.

Fixtures live in a TemporaryDirectory and are never research measurements.
Tampering tests refresh outer inventories so inner audit checks must catch it.
"""
from contextlib import redirect_stdout
import csv
import io
import json
from pathlib import Path
import shutil
import tempfile
import unittest
from unittest.mock import patch

import review_results as q

WINDOW = q.ROOT.parent / "research-window-20261114"


def write(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(q.canonical(value) + b"\n")


def refresh_inventories(root):
    out, window = root / "model-001", root / "window-evidence-001"
    receipt = q.load(out / "completion.json")
    receipt["evidence_sha256"] = {n: h for n, h in q.inventory(out).items() if n != "completion.json"}
    write(out / "completion.json", receipt)
    actual = {"model-001/" + n: h for n, h in q.inventory(out).items()}
    actual.update({"window-evidence-001/" + n: h for n, h in q.inventory(window).items() if n != "snapshot-manifest.json"})
    write(window / "snapshot-manifest.json", dict(utc="2026-11-15T05:30:00+00:00", batch_id=q.BATCH,
          session_still_running=True, credential_access=False, files=actual))
    actual["window-evidence-001/snapshot-manifest.json"] = q.sha(window / "snapshot-manifest.json")
    write(root / "transfer-001.json", dict(compressed_bytes=1, archive_sha256="0" * 64, files=actual))


def synthetic_archive(root):
    """Exercise the frozen collector with local fakes, then construct receipts."""
    out, window = root / "model-001", root / "window-evidence-001"
    shutil.copytree(q.ROOT / "frozen-001", root / "frozen-001")
    shutil.copytree(WINDOW / "batches" / q.BATCH, out)
    runtime = q.load(out / "runtime-freeze.json")
    for name in runtime["runtime_sha256"]:
        target = out / "runtime" / name
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(WINDOW / "execution-runtime" / name, target)
    for original, archive in (("runtime", "window-runtime"), ("session-runtime-002", "session-runtime")):
        shutil.copytree(WINDOW / original, out / archive, ignore=shutil.ignore_patterns("__pycache__"))
    shutil.copy2(WINDOW / "scope.json", out / "scope.json")
    shutil.copy2(WINDOW / "admissions/000001.json", out / "admission.json")
    env = dict(job_id="99999", host="offline-fake-compute", partition="shared", python="FAKE",
               versions=runtime["environment_versions"], requeue=False, model_connectivity_calls=0)
    write(out / "environment.json", env)
    trials = q.load(out / "frozen-001/trials.json")
    kinds = {0: "PROOF_FAILURE", 1: "OUTPUT_REJECTED", 2: "WARNING_ONLY", 3: "FRONTEND_ERROR", 4: "OUTPUT_TRUNCATED", 5: "BODY_REJECTED"}
    responses = []
    with q.replay_runtime(out) as r:
        def response(payload):
            index = len(responses)
            trial = trials[index]
            assert payload == q.load(out / "frozen-001" / trial["request_path"])
            parent, task, base, template = r.parent_parts(out, trial)
            family = {"saturating_assoc": "arithmetic", "compression_fixed_point": "sequence",
                      "exact_gap_pair": "witness", "overlap_override_restrict": "maps"}[trial["semantic_instance"]]
            reference = out / "inputs/experiments/repair-diversity-expansion-001" / family / "fixtures" / trial["task_id"] / "reference"
            guard, _ = r.policy(out)
            bodies = {}
            for name in task["editable_files"]:
                prefix, suffix = guard.split_seed(template[name].decode())
                source = base[name].decode() if kinds.get(index) == "PROOF_FAILURE" else (reference / name).read_text()
                bodies[name] = source[len(prefix):-len(suffix)]
            text = json.dumps(bodies)
            if kinds.get(index) == "OUTPUT_REJECTED":
                text = "unstructured fake response"
            elif kinds.get(index) == "BODY_REJECTED":
                text = json.dumps({name: "assume false;" for name in task["editable_files"]})
            content = [dict(text=text)]
            usage = dict(inputTokens=100, outputTokens=10, totalTokens=110)
            stop = "max_tokens" if kinds.get(index) == "OUTPUT_TRUNCATED" else "end_turn"
            rid = f"offline-fake-{index + 1}"
            raw = dict(output=dict(message=dict(role="assistant", content=content)), usage=usage, stopReason=stop,
                       ResponseMetadata=dict(RequestId=rid, RetryAttempts=0))
            result = dict(text=text, content=content, usage=usage, stop_reason=stop, request_id=rid,
                          retry_attempts=0, raw_response=raw)
            responses.append(result)
            return result

        def verifier(files):
            index = len(responses) - 1
            kind = kinds.get(index, "VERIFIED")
            trial = trials[index]
            scope = q.load(out / "frozen-001/measurement-scope.json")["tasks"][trial["task_id"]]
            buffer = io.StringIO()
            writer = csv.writer(buffer, lineterminator="\r\n")
            writer.writerow(r.target_metrics.HEADER)
            total = 0
            for symbol, units in scope["expected_units"].items():
                for unit in units:
                    total += 1
                    passed = not (kind == "PROOF_FAILURE" and symbol == "HelperA.Prove")
                    writer.writerow([f"{symbol} ({unit})", "Passed" if passed else "Failed", "0:00:00.001", "1", "0"])
            csv_files = {"TestResults/offline-fake.csv": buffer.getvalue()}
            errors = int(kind == "PROOF_FAILURE")
            text = f"Dafny program verifier finished with {total-errors} verified, {errors} errors\n"
            if kind == "PROOF_FAILURE":
                text = "HelperA.dfy(1,1): Error: a precondition for this call could not be proved\n" + text
            if kind == "WARNING_ONLY":
                text = "HelperA.dfy(1,1): Warning: FAKE trigger\n" + text + "--allow-warnings is false\n"
            if kind == "FRONTEND_ERROR":
                text = "HelperA.dfy(1,1): Error: FAKE parse diagnostic\n1 parse errors detected in All.dfy\n"
                csv_files = {}
            return dict(command=q.COMMAND, exit_code=4 if errors else 2 if kind in ("WARNING_ONLY", "FRONTEND_ERROR") else 0,
                        stdout=text, stderr="", source_sha256=q.hashes(files), attempts=1, model_calls=0,
                        csv=csv_files, csv_sha256={n: q.digest(t.encode()) for n, t in csv_files.items()})

        with patch("subprocess.run", side_effect=AssertionError("Real subprocess forbidden")), redirect_stdout(io.StringIO()):
            r.collect(out, response, verifier, q.DEADLINE, root=out, clock=lambda: q.START + 3600, check_runtime=False)
    window.mkdir()
    for name in ("scope.json", "launch-manifest.json", "session.sbatch", "session_ops.py", "execution-preflight-001.json", "stage-002.json"):
        shutil.copy2(WINDOW / name, window / name)
    (window / "submission-001.lock").write_bytes(b"")  # Synthetic remote-only marker.
    submission = q.load(WINDOW / "submission-001.json")
    submission.update(job_id=env["job_id"], stdout=env["job_id"] + "\n")
    write(window / "submission-001.json", submission)
    (window / "accounting-snapshot.txt").write_text("JobID|State|Elapsed|ExitCode|NodeList\n99999|RUNNING|00:01:00|0:0|offline-fake-compute\n")
    results = q.load(out / "results.json")
    (window / "session-99999.log").write_text("".join(row["trial_id"] + " " + row["outcome"] + "\n" for row in results))
    (window / "session-99999.err").write_bytes(b"")
    admission = q.load(out / "admission.json")
    queued = window / "session/queue" / ("0001-" + q.BATCH + ".json")
    write(queued, admission)
    manifest = {k: admission[k] for k in ("batch_id", "freeze_sha256", "runtime_sha256", "max_calls", "sdk_total_max_attempts")}
    manifest["slots"] = [{k: s[k] for k in ("trial_id", "request_sha256")} for s in admission["slots"]]
    rows = []
    for i, (trial, result) in enumerate(zip(trials, responses), 1):
        request = window / "budget/requests" / f"request-{i:03}.json"
        request.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(out / "frozen-001" / trial["request_path"], request)
        returned = request.with_name(f"response-{i:03}.json")
        write(returned, result)
        rows.append(dict(sequence=i, batch_id=q.BATCH, trial_id=trial["trial_id"], manifest_sha256=q.digest(q.canonical(manifest)),
                         request_sha256=q.sha(request), reserved_at_epoch=q.START+3600, dispatch_intent_at_epoch=q.START+3600,
                         returned_at_epoch=q.START+3600, status="COMPLETED", response_sha256=q.sha(returned), request_id=result["request_id"]))
    scope = q.load(out / "scope.json")
    write(window / "budget/ledger.json", dict(schema="repodisco-window-budget-v1", scope=scope, scope_sha256=q.digest(q.canonical(scope)),
          batches=[dict(manifest=manifest, manifest_sha256=q.digest(q.canonical(manifest)))], reservations=rows, terminal_reason=None,
          owner_session=dict(pid=1, host=env["host"], acquired_at_epoch=q.START+3600)))
    state = dict(schema="repodisco-session-status-v1", phase="completed", reason="batch_complete", event_sequence=1,
                 at_epoch=q.START+3600, queued=[dict(sequence=1, batch_id=q.BATCH, descriptor_sha256=q.sha(queued))],
                 completed_batch_ids=[q.BATCH], active_batch_id=None, window_reservations=32, deadline_epoch=q.DEADLINE)
    write(window / "session/events/00001.json", state)
    write(window / "session/status.json", state)
    write(out / "completion.json", dict(batch_id=q.BATCH, descriptor_sha256=q.sha(queued),
          completed_trials=[t["trial_id"] for t in trials], request_ids=[r["request_id"] for r in rows], evidence_sha256={}))
    refresh_inventories(root)


class EditLabelTests(unittest.TestCase):
    def test_exact_whitespace_reordered_and_changed_lines_are_distinct(self):
        original = "  O.First();\n  O.Second();\n"
        self.assertEqual(q.classify_body_edit(original, original), "unchanged")
        self.assertEqual(q.classify_body_edit(original, "\nO.First();\n    O.Second();\n\n"), "whitespace_only")
        self.assertEqual(q.classify_body_edit(original, "O.Second();\nO.First();\n"), "reorder_only")
        self.assertEqual(q.classify_body_edit(original, "O.First();\nO.Third();\n"), "other_edit")
        self.assertEqual(q.classify_body_edit(original, "O.First();\nO.First();\nO.Second();\n"), "other_edit")


class FileOnlyArchiveTests(unittest.TestCase):
    def test_absent_empty_attempts_are_valid_but_unrecorded_attempts_are_not(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / "synthetic"
            synthetic_archive(root)
            before = q.inventory(root / "model-001")
            attempts = sorted((root / "model-001").glob("repair-diversity-*/store/attempts"))
            self.assertEqual(len(attempts), 32)
            for path in attempts:
                path.rmdir()
            self.assertEqual(q.inventory(root / "model-001"), before)
            with patch("subprocess.run", side_effect=AssertionError("Offline review cannot execute")):
                report = q.review(root)
            self.assertEqual(report["overall"]["strict_passes"], 26)
            attempts[0].mkdir()
            (attempts[0] / "unrecorded.json").write_text("{}")
            with self.assertRaisesRegex(ValueError, "Transfer inventory differs"):
                q.review(root)
            refresh_inventories(root)
            with self.assertRaisesRegex(ValueError, "Nonempty or non-directory attempt evidence"):
                q.review(root)

    def test_optional_empty_directory_rejects_files_symlinks_and_nested_directories(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            target = root / "attempts"
            q.optional_empty_directory(target)
            target.mkdir()
            q.optional_empty_directory(target)
            (target / "nested").mkdir()
            with self.assertRaises(ValueError):
                q.optional_empty_directory(target)
            (target / "nested").rmdir()
            target.rmdir()
            target.write_text("unexpected")
            with self.assertRaises(ValueError):
                q.optional_empty_directory(target)
            target.unlink()
            target.symlink_to(root / "absent")
            with self.assertRaises(ValueError):
                q.optional_empty_directory(target)


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


class ReviewerTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory()
        cls.base = Path(cls.temp.name) / "synthetic"
        synthetic_archive(cls.base)

    @classmethod
    def tearDownClass(cls):
        cls.temp.cleanup()

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name) / "archive"
        shutil.copytree(self.base, self.root)

    def test_complete_fake_archive_replays_all_failure_categories_and_closed_clients(self):
        with patch("subprocess.run", side_effect=AssertionError("Offline review cannot execute")):
            result = q.review(self.root)
        self.assertEqual(result["overall"]["strict_passes"], 26)
        self.assertEqual(result["overall"]["outcomes"], dict(FRONTEND_ERROR=1, OUTPUT_REJECTED=2, OUTPUT_TRUNCATED=1, PROOF_FAILURE=1, VERIFIED=26, WARNING_ONLY=1))
        self.assertEqual(result["rows"][0]["target_metrics"]["supplied_clients_local"]["passed"], 2)
        self.assertEqual(result["rows"][0]["target_metrics"]["supplied_clients_closed"]["passed"], 0)
        self.assertEqual(result["rows"][0]["diagnostic_categories"], ["precondition"])
        self.assertEqual(len(result["descriptive_feedback_pairs"]), 16)

    def test_duplicate_global_id_fails_despite_refreshed_outer_inventories(self):
        path = self.root / "window-evidence-001/budget/ledger.json"
        ledger = q.load(path)
        ledger["reservations"][1]["request_id"] = ledger["reservations"][0]["request_id"]
        write(path, ledger)
        refresh_inventories(self.root)
        with self.assertRaisesRegex(ValueError, "Global ID/retry"):
            q.review(self.root)

    def test_missing_named_csv_fails_even_when_csv_hash_is_updated(self):
        folder = self.root / "model-001/repair-diversity-07"
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
        path = self.root / "model-001/repair-diversity-01/verification.json"
        evidence = q.load(path)
        evidence["stdout"] = "Unexpected infrastructure output\n"
        write(path, evidence)
        refresh_inventories(self.root)
        with self.assertRaises(ValueError):
            q.review(self.root)

    def test_accepted_contract_change_fails_even_with_updated_revision_hash(self):
        folder = self.root / "model-001/repair-diversity-07"
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
