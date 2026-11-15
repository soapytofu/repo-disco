"""Offline tests on temporary copies of the saved stopped archive.

Mutations below are synthetic tamper tests, never changes to primary evidence.
No transport, verifier, credential, admission, or remote action is performed.
"""
import copy
from pathlib import Path
import shutil
import tempfile
import unittest
from unittest.mock import patch

import review_stopped as s

q = s.q


def write(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(q.canonical(value) + b"\n")


def refresh_outer(root):
    """Recompute only untrusted outer transport inventories after test mutations."""
    window = root / "window-evidence-001"
    actual = {"model-001/" + n: h for n, h in q.inventory(root / "model-001").items()}
    actual.update({"window-evidence-001/" + n: h for n, h in q.inventory(window).items()
                   if n != "snapshot-manifest.json"})
    snapshot = q.load(window / "snapshot-manifest.json")
    snapshot["files"] = actual
    write(window / "snapshot-manifest.json", snapshot)
    actual["window-evidence-001/snapshot-manifest.json"] = q.sha(window / "snapshot-manifest.json")
    transfer = q.load(root / "transfer-001.json")
    transfer["files"] = actual
    write(root / "transfer-001.json", transfer)


class StoppedReviewTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name) / "archive"
        self.root.mkdir()
        for name in ("model-001", "window-evidence-001", "frozen-001"):
            shutil.copytree(q.ROOT / name, self.root / name)
        shutil.copy2(q.ROOT / "transfer-001.json", self.root / "transfer-001.json")
        no_subprocess = patch("subprocess.run", side_effect=AssertionError("No verifier or command allowed"))
        no_subprocess.start()
        self.addCleanup(no_subprocess.stop)
        no_network = patch("socket.create_connection", side_effect=AssertionError("No network allowed"))
        no_network.start()
        self.addCleanup(no_network.stop)

    def test_saved_stop_is_no_score_and_preserves_all_raw_bytes(self):
        before = q.inventory(self.root)
        result = s.review(self.root)
        self.assertIsNone(result["proof_score"])
        self.assertEqual(result["new_batch_evaluable_responses"], 0)
        self.assertEqual(result["new_batch_reserved_calls"], 1)
        self.assertEqual(result["new_batch_undispatched_trials"], 31)
        self.assertEqual(result["aggregate_window"]["declared_calls"], 64)
        self.assertEqual(result["aggregate_window"]["reserved_calls"], 33)
        self.assertEqual(result["aggregate_window"]["completed_responses"], 32)
        self.assertFalse(result["aggregate_window"]["permits_more_dispatch"])
        self.assertIsNone(result["attempted"]["provider_request_id"])
        self.assertIsNone(result["attempted"]["provider_token_usage"])
        self.assertIsNone(result["observed_new_sdk_retry_count"])
        self.assertTrue(result["provider_execution_and_billing_unknown"])
        self.assertIsNone(result["raw_summary_fatal_error_type"])
        self.assertEqual(result["transport_error"], "ReadTimeoutError")
        self.assertEqual(result["session_wrapper_error"], "ValueError")
        self.assertEqual(result["attempted"]["initial_revision"], result["attempted"]["final_observed_HEAD"])
        self.assertEqual(result["new_verifier_runs"], 0)
        self.assertEqual(result["new_promotions"], 0)
        self.assertEqual(q.inventory(self.root), before)

    def test_null_fatal_summary_is_preserved_not_rewritten_to_a_proof_outcome(self):
        path = self.root / "model-001/summary.json"
        summary = q.load(path)
        self.assertIsNone(summary["fatal_error_type"])
        summary["fatal_error_type"] = "ReadTimeoutError"
        write(path, summary)
        refresh_outer(self.root)
        with self.assertRaisesRegex(ValueError, "Raw stopped summary differs"):
            s.review(self.root)

    def test_fabricated_second_completion_receipt_is_rejected(self):
        write(self.root / "model-001/completion.json", {"batch_id": q.BATCH})
        refresh_outer(self.root)
        with self.assertRaisesRegex(ValueError, "cannot have a completion receipt"):
            s.review(self.root)

    def test_fabricated_ambiguous_response_is_rejected(self):
        write(self.root / "window-evidence-001/budget/requests/response-033.json", {"request_id": "synthetic"})
        refresh_outer(self.root)
        with self.assertRaisesRegex(ValueError, "Unexpected returned or additional request"):
            s.review(self.root)

    def test_dispatch_bytes_cannot_change_even_with_fresh_transfer_hashes(self):
        path = self.root / "window-evidence-001/budget/requests/request-033.json"
        request = q.load(path)
        request["inferenceConfig"]["maxTokens"] += 1
        write(path, request)
        refresh_outer(self.root)
        with self.assertRaisesRegex(ValueError, "Exact dispatch request differs"):
            s.review(self.root)

    def test_predecessor_prefix_cannot_be_reassigned_or_rewritten(self):
        path = self.root / "window-evidence-001/budget/ledger.json"
        ledger = q.load(path)
        ledger["reservations"][0]["returned_at_epoch"] += 0.01
        write(path, ledger)
        refresh_outer(self.root)
        with self.assertRaisesRegex(ValueError, "Published predecessor or new reservation count"):
            s.review(self.root)

    def test_ambiguous_slot_cannot_be_labelled_completed_or_given_an_id(self):
        path = self.root / "window-evidence-001/budget/ledger.json"
        ledger = q.load(path)
        ledger["reservations"][-1]["status"] = "COMPLETED"
        ledger["reservations"][-1]["request_id"] = "synthetic"
        write(path, ledger)
        refresh_outer(self.root)
        with self.assertRaisesRegex(ValueError, "Ambiguous slot identity differs"):
            s.review(self.root)

    def test_initial_source_and_contracts_remain_exact(self):
        folder = self.root / "model-001/repair-selection-01"
        revision = q.load(folder / "store/HEAD.json")["revision"]
        source = folder / "store/revisions" / revision / "files/ClientA.dfy"
        source.write_bytes(source.read_bytes() + b"\n// synthetic forbidden mutation\n")
        metadata_path = source.parent.parent / "revision.json"
        metadata = q.load(metadata_path)
        metadata["source_sha256"]["ClientA.dfy"] = q.sha(source)
        write(metadata_path, metadata)
        refresh_outer(self.root)
        with self.assertRaisesRegex(ValueError, "Original revision, source, or contracts changed"):
            s.review(self.root)

    def test_unstarted_trial_and_candidate_artifacts_are_not_allowed(self):
        folder = self.root / "model-001/repair-selection-02"
        write(folder / "trial.json", {"synthetic": True})
        refresh_outer(self.root)
        with self.assertRaisesRegex(ValueError, "Undispatched trial artifacts exist"):
            s.review(self.root)

    def test_future_slot_allocation_cannot_be_reordered(self):
        path = self.root / "window-evidence-001/budget/ledger.json"
        ledger = q.load(path)
        slots = ledger["batches"][1]["manifest"]["slots"]
        slots[0], slots[1] = copy.deepcopy(slots[1]), copy.deepcopy(slots[0])
        ledger["batches"][1]["manifest_sha256"] = q.digest(q.canonical(ledger["batches"][1]["manifest"]))
        write(path, ledger)
        refresh_outer(self.root)
        with self.assertRaisesRegex(ValueError, "Declared allocations changed"):
            s.review(self.root)


if __name__ == "__main__":
    unittest.main(verbosity=2)
