"""Synthetic evidence and exact saved-record replay; no Dafny/model calls."""
import base64
import copy
import csv
import io
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

import measure as m

ARITH = "capped_endpoint_return_migration"
MAP = "extracted_entry_return_migration"


def task(identifier):
    return next(t for t in m.load(m.ROOT / "metadata/tasks.json") if t["task_id"] == identifier)


def raw_from_record(record):
    raw = {s + ".txt": base64.b64decode(record[s + "_base64"], validate=True) for s in ("stdout", "stderr")}
    raw.update({"csv/" + n: base64.b64decode(v, validate=True) for n, v in record["csv_base64"].items()})
    return raw


def set_stream(record, stream, text):
    value = text.encode()
    record[stream] = text
    record[stream + "_base64"] = base64.b64encode(value).decode()
    record[stream + "_sha256"] = m.sha(value)


def set_csv(record, rows):
    name = "TestResults/synthetic.csv"
    buffer = io.StringIO(newline="")
    writer = csv.writer(buffer, lineterminator="\r\n")
    writer.writerows(rows)
    text = buffer.getvalue()
    record["csv"] = {name: text}
    record["csv_base64"] = {name: base64.b64encode(text.encode()).decode()}
    record["csv_sha256"] = {name: m.sha(text.encode())}


def fake(record):
    value = copy.deepcopy(record)
    for name in ("actual", "diagnostics", "matched", "expected", "expected_diagnostic", "case_id"):
        value.pop(name, None)
    return value


def prepared(base=ARITH, variant="paired_repair", bodies=None):
    identifier = base + "-dual_fault"
    metadata = task(identifier)
    folder = m.ROOT / "controls" / (base + "-" + variant)
    files = m.sources(folder / "sources")
    body_map = m.candidate_bodies(files, metadata) if bodies is None else bodies
    seed = m.sources(m.ROOT / "seeds" / identifier)
    guard = m.guard_module()
    candidate, receipt = guard.parse_response(m.canonical(body_map).decode(),
        {n:b.decode() for n,b in seed.items()}, metadata)
    candidate = {n:t.encode() for n,t in candidate.items()}
    record = m.load(folder / "record.json")
    if bodies is not None:
        record = fake(record)
        record["source_sha256"] = m.source_hashes(candidate)
    return identifier, candidate, receipt, record


def score(parts, record=None, raw=None):
    identifier, files, receipt, original = parts
    record = original if record is None else record
    raw = raw_from_record(record) if raw is None else raw
    return m.score_candidate(identifier, files, m.source_hashes(files), receipt, record, raw)


class MeasurementTests(unittest.TestCase):
    def setUp(self):
        blocker = patch("subprocess.run", side_effect=AssertionError("No verifier/process calls permitted"))
        blocker.start(); self.addCleanup(blocker.stop)
        network = patch("socket.create_connection", side_effect=AssertionError("No network permitted"))
        network.start(); self.addCleanup(network.stop)

    def test_all18_historical_observations_replay_without_new_trials(self):
        before = m.inventory(m.ROOT / "controls")
        result = m.replay_controls()
        self.assertEqual((result["historical_observations"], result["strict_successes"], result["proof_failures"]), (18, 6, 12))
        self.assertEqual(result["unlogged_Endpoint_observations"], 9)
        self.assertFalse(result["candidate_admission"])
        self.assertEqual((result["new_verifier_runs"], result["new_model_calls"]), (0, 0))
        self.assertEqual(m.inventory(m.ROOT / "controls"), before)

    def test_exact_paired_candidates_pass_with_guard_and_protected_source_replay(self):
        for base in (ARITH, MAP):
            with self.subTest(base=base):
                result = score(prepared(base))
                self.assertTrue(result["strict_workspace_verified"])
                self.assertTrue(result["guard_receipt_replayed"])
                self.assertEqual(result["named_evidence"]["local_targets"], {"Helper.Transfer": True, "Client.Target": True})
                self.assertEqual(len(result["named_evidence"]["unlogged_definitions"]), int(base == ARITH))

    def test_client_local_pass_does_not_make_failed_helper_repository_success(self):
        result = score(prepared(MAP, "contract_only"))
        self.assertEqual(result["outcome"], "PROOF_FAILURE")
        self.assertFalse(result["strict_workspace_verified"])
        self.assertEqual(result["named_evidence"]["local_targets"], {"Helper.Transfer": False, "Client.Target": True})

    def test_loose_acceptance_or_forged_policy_receipt_cannot_grant_pass(self):
        parts = prepared()
        for replacement in ({"accepted": True}, dict(parts[2], registry_sha256="0" * 64),
                            dict(parts[2], candidate_sha256={})):
            with self.subTest(receipt=replacement):
                bad = (parts[0], parts[1], replacement, parts[3])
                with self.assertRaisesRegex(m.MeasurementError, "guard receipt replay mismatch"):
                    score(bad)

    def test_old_contract_or_changed_kernel_or_public_contract_is_rejected(self):
        parts = prepared()
        for name, changed in (
            ("Helper.dfy", (m.ROOT / "controls" / (ARITH + "-reference") / "sources/Helper.dfy").read_bytes()),
            ("Kernel.dfy", parts[1]["Kernel.dfy"] + b"\n// changed\n"),
            ("Client.dfy", parts[1]["Client.dfy"].replace(b"requires 0 <= length", b"requires 0 < length"))):
            with self.subTest(file=name):
                files = dict(parts[1], **{name:changed})
                with self.assertRaises(m.MeasurementError):
                    score((parts[0], files, parts[2], parts[3]))

    def test_raw_base64_hash_and_verifier_source_must_all_agree(self):
        parts = prepared()
        for field in ("stdout_base64", "stderr_sha256", "source_sha256", "csv_sha256"):
            record = copy.deepcopy(parts[3])
            if field == "stdout_base64": record[field] = "!!!"
            elif field == "stderr_sha256": record[field] = "0" * 64
            elif field == "source_sha256": record[field]["Helper.dfy"] = "0" * 64
            else: record[field][next(iter(record[field]))] = "0" * 64
            with self.subTest(field=field), self.assertRaises(m.MeasurementError):
                score(parts, record, raw_from_record(parts[3]))
        raw = raw_from_record(parts[3]); raw["stdout.txt"] += b"\n"
        with self.assertRaisesRegex(m.MeasurementError, "Raw archive bytes"):
            score(parts, raw=raw)

    def test_missing_duplicate_unknown_and_wrong_kind_named_units_fail(self):
        parts = prepared(MAP)
        original = list(csv.reader(io.StringIO(next(iter(parts[3]["csv"].values())))))
        mutations = []
        mutations.append([row for row in original if not row[0].startswith("Kernel.Entry ")])
        mutations.append(original + [copy.deepcopy(original[1])])
        unknown = copy.deepcopy(original); unknown[1][0] = "Other.Unit (correctness)"; mutations.append(unknown)
        wrong = copy.deepcopy(original)
        for row in wrong:
            if row[0] == "Client.Target (correctness)": row[0] = "Client.Target (well-formedness)"
        mutations.append(wrong)
        for rows in mutations:
            record = fake(parts[3]); set_csv(record, rows)
            with self.subTest(rows=rows), self.assertRaises(m.MeasurementError):
                score(parts, record)

    def test_failed_observed_Endpoint_cannot_be_hidden_by_unlogged_exception(self):
        parts = prepared()
        record = fake(parts[3])
        rows = list(csv.reader(io.StringIO(next(iter(record["csv"].values())))))
        rows.append(["Kernel.Endpoint (well-formedness)", "Failed", "00:00:00.001", "1", "0"])
        set_csv(record, rows)
        record["exit_code"] = 4
        set_stream(record, "stdout", "Kernel.dfy(1,1): Error: assertion might not hold\nDafny program verifier finished with 2 verified, 1 error\n")
        with self.assertRaisesRegex(m.MeasurementError, "Immutable provider failed"):
            score(parts, record)

    def test_parse_resolution_type_timeout_and_execution_error_are_separate(self):
        parts = prepared()
        cases = [
            (2, "Helper.dfy(1,1): Error: this symbol not expected\n1 parse errors detected in All.dfy\n", False, None, "PARSE_FAILURE"),
            (2, "Helper.dfy(1,1): Error: type mismatch\n1 resolution/type errors detected in All.dfy\n", False, None, "RESOLUTION_OR_TYPE_FAILURE"),
            (124, "", True, None, "TIMEOUT"),
            (None, "", False, "OSError", "VERIFIER_EXECUTION_ERROR"),
        ]
        for code, stdout, timeout, error, expected in cases:
            record = fake(parts[3]); record.update(exit_code=code, timed_out=timeout, execution_error=error, csv={}, csv_base64={}, csv_sha256={})
            set_stream(record, "stdout", stdout)
            with self.subTest(expected=expected):
                result = score(parts, record)
                self.assertEqual(result["outcome"], expected)
                self.assertFalse(result["strict_workspace_verified"])
                self.assertIsNone(result["named_evidence"])

    def test_warning_only_is_not_strict_success_and_unknown_exit_is_not_proof_failure(self):
        parts = prepared()
        for code in (0, 2):
            record = fake(parts[3]); record["exit_code"] = code
            text = "Helper.dfy(1,1): Warning: synthetic trigger warning\nDafny program verifier finished with 2 verified, 0 errors\n"
            if code == 2: text += "--allow-warnings is false\n"
            set_stream(record, "stdout", text)
            result = score(parts, record)
            self.assertEqual(result["outcome"], "WARNING_ONLY")
            self.assertFalse(result["strict_workspace_verified"])
        record = fake(parts[3]); record["exit_code"] = 4
        set_stream(record, "stdout", "Unexpected runtime output\n")
        with self.assertRaisesRegex(m.MeasurementError, "Unclassified verifier output"):
            score(parts, record)

    def test_summary_and_named_failure_disagreement_is_rejected(self):
        parts = prepared(MAP, "contract_only")
        record = fake(parts[3]); record["exit_code"] = 0
        set_stream(record, "stdout", "Dafny program verifier finished with 5 verified, 0 errors\n")
        with self.assertRaisesRegex(m.MeasurementError, "Workspace and named outcome disagree"):
            score(parts, record)

    def test_optional_helper_call_is_descriptive_not_a_pass_requirement(self):
        # These are synthetic verifier records, not semantic validation of these
        # direct implementations. The pure guard admits them; no H call is forced.
        parts = prepared(ARITH, bodies={"Helper.dfy":"    r := K.Endpoint(start,length,cap) - start;\n",
                                       "Client.dfy":"    result := K.Endpoint(start,length,cap);\n"})
        result = score(parts)
        self.assertTrue(result["strict_workspace_verified"])
        self.assertEqual(result["body_annotations"]["bodies"]["Client.dfy"]["call_inventory"]["method"], {})
        self.assertFalse(result["body_annotations"]["helper_call_required"])

    def test_output_rejections_never_receive_verifier_or_proof_scores(self):
        for stage, expected in (("envelope", "ENVELOPE_REJECTED"), ("body_guard", "BODY_GUARD_REJECTED")):
            result = m.rejected_output(stage, "ValueError")
            self.assertEqual(result["outcome"], expected)
            self.assertFalse(result["strict_workspace_verified"])
            self.assertIsNone(result["named_evidence"])
            self.assertEqual(result["new_verifier_runs"], 0)
        with self.assertRaises(m.MeasurementError): m.rejected_output("success", "ValueError")

    def test_guard_bundle_or_seed_metadata_tampering_is_rejected(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp) / "bundle"
            shutil.copytree(m.ROOT, root, ignore=shutil.ignore_patterns("__pycache__"))
            path = root / "guard/registry.json"
            path.write_bytes(path.read_bytes() + b"\n")
            with self.assertRaisesRegex(m.MeasurementError, "guard inventory|Guard",):
                m.guard_module(root)


class StandaloneTests(unittest.TestCase):
    def test_manifest_only_bundle_replays_without_repository_or_verifier_access(self):
        manifest = m.load(m.ROOT / "measurement-manifest.json")
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp) / "bundle"; root.mkdir()
            for name, digest in manifest["files_sha256"].items():
                source = m.ROOT / name
                self.assertEqual(m.sha(source.read_bytes()), digest)
                target = root / name; target.parent.mkdir(parents=True, exist_ok=True)
                target.write_bytes(source.read_bytes())
            code = "import sys,subprocess,socket;sys.path.insert(0,sys.argv[1]);subprocess.run=lambda *a,**k:(_ for _ in ()).throw(AssertionError('No verifier'));socket.create_connection=lambda *a,**k:(_ for _ in ()).throw(AssertionError('No network'));import measure;from test_measure import prepared,score;r=measure.replay_controls();assert r['historical_observations']==18;assert score(prepared())['strict_workspace_verified'];print('standalone:18 exact historical records and guarded synthetic candidate pass')"
            run = subprocess.run([sys.executable, "-I", "-B", "-c", code, str(root)], cwd=temp,
                capture_output=True, text=True, timeout=60)
            self.assertEqual(run.returncode, 0, run.stdout + run.stderr)
            self.assertIn("standalone:18", run.stdout)


if __name__ == "__main__":
    unittest.main(verbosity=2)
