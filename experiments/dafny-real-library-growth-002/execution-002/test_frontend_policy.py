"""Focused synthetic tests for the prospective frontend-continuation policy.

No provider or native process is invoked. The actual historical slot-03 replay
is recorded separately under reviews/frontend-policy-review-001; these fixtures
are deliberately synthetic and remain rejected by the production reviewer.
"""
import copy
from pathlib import Path
import tempfile
import unittest

import review_collection as review
import runtime as rt
from run_pilot import Runner
from test_review_collection import FullFakeHost, FullFakeTransport, write_json
from test_runner import FakeRenderer, scope, stages


class FrontendFakeHost(FullFakeHost):
    """Produce marked fake diagnostics with ordinary source locations."""

    def __init__(self):
        super().__init__()
        self.frontends = {"slot-01": "parse"}
        self.adjust = None

    def run(self, profile, sources, event, destination, adapter):
        kind = self.frontends.get(event["slot_id"])
        previous = self.mutate
        if kind is not None:
            self.outcomes[event["slot_id"]] = "FRONTEND_PARSE_FAILURE"

            def mutate(record, raw, current_event):
                text = "// SYNTHETIC OFFLINE: no verifier invocation\n"
                if kind == "resolution/type":
                    text += ("Added1.dfy(6,2): Warning: unusual indentation in right-hand operand of ==>\n"
                             "Added1.dfy(5,2): Error: member 'data' has not been imported in this scope\n")
                else:
                    text += "Added1.dfy(5,2): Error: expected semicolon\n"
                # Actual Dafny names the first input in its summary even when
                # every located error belongs to the new addition.
                text += "1 " + kind + " error detected in Base.dfy\n"
                raw["stdout.txt"] = text.encode()
                raw["csv/TestResults/fake.csv"] = (",".join(profile["csv_columns"]) + "\n").encode()
                record["raw_sha256"] = rt.native.hashes(raw)
                if self.adjust is not None:
                    self.adjust(record, raw, current_event)

            self.mutate = mutate
        try:
            return super().run(profile, sources, event, destination, adapter)
        finally:
            self.mutate = previous


class FrontendPolicyTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name).resolve()

    def tearDown(self):
        self.temp.cleanup()

    def scenario(self, name="run", *, host=None, integrity=None):
        stages_ = stages()
        scope_ = scope()
        renderer = FakeRenderer(stages_)
        transport = FullFakeTransport()
        host = host or FrontendFakeHost()
        output = self.root / name
        runner = Runner(scope_, stages_, renderer, host, transport, output,
            deadline=100, integrity_check=integrity or (lambda: None), clock=lambda: 1,
            offline=True, run_id="SYNTHETIC-FRONTEND-" + name)
        return dict(runner=runner, output=output, stages=stages_, scope=scope_,
                    renderer=renderer, transport=transport, host=host)

    def audit(self, value, *, allow_synthetic=True):
        return review._audit_run(value["output"], value["scope"], value["stages"],
            value["renderer"], package=self.root,
            auth=dict(created_at_epoch=0, expires_at_epoch=100),
            expected_host=dict(job_id="SYNTHETIC", partition="synthetic"),
            expected_output=str(value["output"]), allow_synthetic=allow_synthetic)

    def assert_terminal_one(self, value):
        summary = value["runner"].run()
        self.assertEqual((summary["status"], summary["reserved"], summary["completed"]),
                         ("TERMINAL", 1, 1))
        self.assertEqual(summary["accepted_stages"], 0)
        self.assertEqual(len(value["transport"].calls), 1)
        self.assertEqual(len(value["host"].calls), 1)
        self.assertTrue(all(not row["accepted"] for row in summary["rows"]))
        return summary

    @staticmethod
    def rehash(record, raw):
        record["raw_sha256"] = rt.native.hashes(raw)

    def test_eight_slot_runner_and_reviewer_continue_both_frontend_kinds(self):
        host = FrontendFakeHost()
        host.frontends = {"slot-01": "parse", "slot-02": "resolution/type"}
        host.outcomes.update({"slot-03": "PROOF_FAILURE", "slot-04": "RESOURCE_FAILURE"})
        value = self.scenario(host=host)
        summary = value["runner"].run()
        self.assertEqual((summary["status"], summary["reserved"], summary["completed"]),
                         ("COMPLETE", 8, 8))
        self.assertEqual(summary["accepted_stages"], 4)
        self.assertEqual(len(value["transport"].calls), 8)
        self.assertEqual(len(host.calls), 8)
        self.assertEqual([row["category"] for row in summary["rows"][:2]],
                         ["FRONTEND_PARSE_FAILURE", "FRONTEND_RESOLUTION_FAILURE"])
        for row in summary["rows"][:4]:
            self.assertEqual(row["outcome"], "NATIVE_REJECTED")
            self.assertFalse(row["accepted"])
        result = self.audit(value)
        self.assertEqual(result["status"], "PASS_COMPLETE")
        self.assertEqual(result["score"], {"accepted": 4, "returned_trials": 8})
        self.assertEqual(result["unique_request_ids"], 8)
        self.assertEqual(result["sdk_retries"], 0)
        self.assertEqual(result["outcome_counts"]["NATIVE_REJECTED"], 4)
        self.assertFalse(result["acceptance_issued"])
        self.assertTrue(result["synthetic"])
        with self.assertRaisesRegex(rt.native.EvidenceError, "Synthetic"):
            self.audit(value, allow_synthetic=False)

    def test_frontend_warning_and_absent_proof_coverage_are_preserved_not_accepted(self):
        host = FrontendFakeHost()
        host.frontends = {"slot-01": "resolution/type"}
        value = self.scenario(host=host)
        summary = value["runner"].run()
        folder = value["output"] / "slots/slot-01"
        report = rt.read_json(folder / "native-review.json")
        self.assertEqual(summary["status"], "COMPLETE")
        self.assertEqual(report["warnings"], 1)
        self.assertFalse(report["warning_policy_matches"])
        self.assertFalse(report["qualified_success"])
        self.assertFalse(report["proof_coverage_complete"])
        self.assertEqual((report["passed_units"], report["failed_units"]), (0, 0))
        self.assertEqual(len(report["missing_units"]), 2)
        self.assertEqual(len(report["warning_lines"]), 1)
        stdout = (folder / "native/raw/stdout.txt").read_text()
        self.assertIn(report["warning_lines"][0], stdout)
        self.assertEqual(summary["rows"][0]["warnings"], 1)
        self.assertFalse(summary["rows"][0]["accepted"])
        self.assertEqual(self.audit(value)["accepted_additions"], 7)

    def test_recorded_frontend_rejection_cannot_be_relabeled_as_acceptance(self):
        value = self.scenario()
        value["runner"].run()
        path = value["output"] / "slots/slot-01/outcome.json"
        row = rt.read_json(path)
        row.update(accepted=True, outcome="ACCEPTED")
        write_json(path, row)
        summary = rt.read_json(value["output"] / "summary.json")
        summary["rows"][0] = row
        summary["accepted_stages"] += 1
        summary["per_task"][row["project"]]["accepted"] += 1
        write_json(value["output"] / "summary.json", summary)
        with self.assertRaises(rt.native.EvidenceError):
            self.audit(value)

    def test_dependency_error_or_dependency_warning_is_terminal(self):
        for label in ("Error", "Warning"):
            with self.subTest(label=label):
                host = FrontendFakeHost()
                host.frontends = {"slot-01": "resolution/type"}
                def adjust(record, raw, event):
                    raw["stdout.txt"] = raw["stdout.txt"].replace(
                        ("Added1.dfy(5,2): " + label).encode(),
                        ("Base.dfy(5,2): " + label).encode()) if label == "Error" else raw["stdout.txt"].replace(
                        b"Added1.dfy(6,2): Warning", b"Base.dfy(6,2): Warning")
                    self.rehash(record, raw)
                host.adjust = adjust
                self.assert_terminal_one(self.scenario(label, host=host))

    def test_infrastructure_stderr_or_unlocated_error_is_terminal(self):
        for name in ("stderr", "unlocated"):
            with self.subTest(name=name):
                host = FrontendFakeHost()
                def adjust(record, raw, event):
                    if name == "stderr":
                        raw["stderr.txt"] = b"SYNTHETIC: failed to start native tool\n"
                    else:
                        raw["stdout.txt"] += b"Error: failed to start native tool\n"
                    self.rehash(record, raw)
                host.adjust = adjust
                self.assert_terminal_one(self.scenario(name, host=host))

    def test_stdout_infrastructure_markers_are_terminal(self):
        markers = ["Unhandled exception: SYNTHETIC", "Fatal error: SYNTHETIC",
                   "Traceback (most recent call last):", "Stack trace: SYNTHETIC",
                   "Segmentation fault", "Aborted", "Internal error: SYNTHETIC",
                   "Could not start solver", "System.IO.IOException: SYNTHETIC"]
        for index, marker in enumerate(markers):
            with self.subTest(marker=marker):
                host = FrontendFakeHost()
                def adjust(record, raw, event):
                    raw["stdout.txt"] += (marker + "\n").encode()
                    self.rehash(record, raw)
                host.adjust = adjust
                self.assert_terminal_one(self.scenario("infra-" + str(index), host=host))

    def test_unknown_exit_timeout_and_resource_mismatch_are_terminal(self):
        for name in ("exit", "timeout", "resources", "resource-exit"):
            with self.subTest(name=name):
                host = FrontendFakeHost()
                def adjust(record, raw, event):
                    if name == "exit":
                        record["exit_code"] = 9
                        raw["resources.txt"] = raw["resources.txt"].replace(b"Exit status: 2", b"Exit status: 9")
                    elif name == "timeout":
                        record["timeout"] = True
                    elif name == "resources":
                        raw["resources.txt"] = b"SYNTHETIC incomplete resource observation\n"
                    else:
                        raw["resources.txt"] = raw["resources.txt"].replace(b"Exit status: 2", b"Exit status: 1")
                    self.rehash(record, raw)
                host.adjust = adjust
                self.assert_terminal_one(self.scenario(name, host=host))

    def test_missing_primary_raw_evidence_is_terminal(self):
        for name in ("stdout.txt", "stderr.txt", "resources.txt"):
            with self.subTest(name=name):
                host = FrontendFakeHost()
                def adjust(record, raw, event):
                    raw.pop(name)
                    self.rehash(record, raw)
                host.adjust = adjust
                self.assert_terminal_one(self.scenario(name, host=host))

    def test_raw_hash_or_source_command_tool_drift_is_terminal(self):
        for name in ("raw-hash", "before-source", "after-source", "command", "tool"):
            with self.subTest(name=name):
                host = FrontendFakeHost()
                def adjust(record, raw, event):
                    if name == "raw-hash":
                        raw["stdout.txt"] += b"SYNTHETIC unbound new bytes\n"
                    elif name == "before-source":
                        record["source_before_sha256"]["Base.dfy"] = "f" * 64
                    elif name == "after-source":
                        record["source_after_sha256"]["Base.dfy"] = "f" * 64
                    elif name == "command":
                        record["argv"] = record["argv"][:-1]
                    else:
                        record["toolchain_after"] = dict(record["toolchain_after"], executable_sha256="f" * 64)
                host.adjust = adjust
                self.assert_terminal_one(self.scenario(name, host=host))

    def test_missing_or_inconsistent_frontend_summary_is_terminal(self):
        changes = {
            "no-summary": lambda data: data.replace(b"1 parse error detected in Base.dfy\n", b""),
            "count": lambda data: data.replace(b"1 parse error", b"2 parse errors"),
            "two-summaries": lambda data: data + b"1 parse error detected in Base.dfy\n",
            "mixed-kinds": lambda data: data + b"1 resolution/type error detected in Base.dfy\n",
            "unlocated": lambda data: data.replace(b"Added1.dfy(5,2): Error:", b"Error:"),
        }
        for name, change in changes.items():
            with self.subTest(name=name):
                host = FrontendFakeHost()
                def adjust(record, raw, event):
                    raw["stdout.txt"] = change(raw["stdout.txt"])
                    self.rehash(record, raw)
                host.adjust = adjust
                self.assert_terminal_one(self.scenario(name, host=host))

    def test_frontend_with_logged_proof_units_or_native_summary_is_terminal(self):
        for name in ("proof-unit", "native-summary"):
            with self.subTest(name=name):
                host = FrontendFakeHost()
                def adjust(record, raw, event):
                    if name == "proof-unit":
                        raw["csv/TestResults/fake.csv"] += b"Base.Next (well-formedness),Passed,00:00:00.0001000,10,0\n"
                    else:
                        raw["stdout.txt"] += b"Dafny program verifier finished with 0 verified, 0 errors\n"
                    self.rehash(record, raw)
                host.adjust = adjust
                self.assert_terminal_one(self.scenario(name, host=host))

    def test_warning_only_unknown_coverage_and_process_failures_stay_terminal(self):
        for category in ("WARNING_ONLY", "NEW_WARNING", "COVERAGE_FAILURE", "TIMEOUT"):
            with self.subTest(category=category):
                host = FullFakeHost()
                host.outcomes = {"slot-01": category}
                self.assert_terminal_one(self.scenario(category, host=host))

    def test_completed_frontend_evidence_drift_stops_before_second_request(self):
        output = self.root / "drift"
        changed = []
        def integrity():
            path = output / "slots/slot-01/outcome.json"
            if path.exists() and not changed:
                raw = output / "slots/slot-01/native/raw/stdout.txt"
                raw.write_bytes(raw.read_bytes() + b"SYNTHETIC later modification\n")
                changed.append(True)
        value = self.scenario("drift", integrity=integrity)
        self.assert_terminal_one(value)
        self.assertEqual(changed, [True])

    def test_missing_saved_frontend_csv_is_rejected_by_collection_replay(self):
        value = self.scenario()
        value["runner"].run()
        csv = value["output"] / "slots/slot-01/native/raw/csv/TestResults/fake.csv"
        csv.unlink()
        with self.assertRaises(rt.native.EvidenceError):
            self.audit(value)

    def test_frontend_classification_does_not_confer_real_native_authenticity(self):
        value = self.scenario()
        value["runner"].run()
        folder = value["output"] / "slots/slot-01"
        profile = rt.read_json(folder / "native-profile.json")
        record = rt.read_json(folder / "native/record.json")
        sources = rt.source_files(folder / "candidate")
        raw_root = folder / "native/raw"
        raw = {p.relative_to(raw_root).as_posix(): p.read_bytes() for p in raw_root.rglob("*") if p.is_file()}
        pins = rt.native.EvidencePins(rt.sha(rt.canonical(profile)), rt.sha(rt.canonical(record)),
            rt.sha(rt.canonical(rt.native.hashes(sources))), tuple(sorted(rt.native.hashes(raw).items())),
            record["run_id"], "synthetic_offline")
        with self.assertRaisesRegex(rt.native.EvidenceError, "Synthetic"):
            rt.native.review(profile, sources, record, raw, pins)


if __name__ == "__main__":
    unittest.main()
