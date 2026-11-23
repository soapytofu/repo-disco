"""Archive transport tests: intercepted subprocesses only; no live operations."""
import contextlib
import copy
import io
import json
from pathlib import Path
import shlex
import subprocess
import tempfile
import unittest
from unittest import mock

import stdin_archive as archive


class ArchiveTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.ops, cls.frozen, cls.binding, cls.digest = archive.load_frozen_ops()
        cls.estimate = cls.ops.read(archive.EXECUTION / "reviews/terminal-archive-estimate-001.json")
        cls.originals = {name: (archive.PACKAGE / name).read_bytes() for name in cls.frozen["files"]}
        cls.originals["execution-001/runtime-freeze.json"] = archive.FREEZE_PATH.read_bytes()

    @classmethod
    def tearDownClass(cls):
        for name, raw in cls.originals.items():
            if (archive.PACKAGE / name).read_bytes() != raw:
                raise AssertionError("A frozen input changed: " + name)

    def setUp(self):
        self.transport = archive.ArchiveTransport(self.ops, self.binding, self.digest)

    def call(self, action="fetch", **changes):
        values = dict(seconds=archive.TIMEOUTS.get(action, 240), job=archive.JOB_ID,
                      inventory=self.estimate if action == "fetch" else None)
        values.update(changes)
        return self.transport(action, self.binding, self.digest, **values)

    def test_exact_oversized_program_uses_stdin_and_short_fixed_argv(self):
        expected = self.ops.remote_program("fetch", self.binding, self.digest,
                                           archive.JOB_ID, self.estimate).encode()
        self.assertGreater(len(expected), 131072)
        with mock.patch.object(archive.subprocess, "run", return_value=
                subprocess.CompletedProcess([], 0, b"SYNTHETIC ARCHIVE", b"")) as run:
            self.assertEqual(self.call(), b"SYNTHETIC ARCHIVE")
        run.assert_called_once()
        argv = run.call_args.args[0]
        kwargs = run.call_args.kwargs
        self.assertEqual(kwargs["input"], expected)
        self.assertEqual(kwargs["timeout"], 240)
        self.assertEqual(shlex.split(argv[-1]), [self.ops.PYTHON, "-B", "-"])
        self.assertTrue(all(len(arg.encode()) < 4096 for arg in argv))
        self.assertEqual(argv[:-1], ["ssh", "-S", str(self.ops.SOCKET), "-o", "ControlMaster=no",
            "-o", "BatchMode=yes", "-o", "ConnectTimeout=10", "-o", "ProxyCommand=false",
            "-o", "NumberOfPasswordPrompts=0", self.ops.HOST])
        self.assertNotIn("shell", kwargs)
        self.assertNotIn("-c", shlex.split(argv[-1]))

    def test_estimate_transmits_exact_program_without_payload(self):
        raw = self.ops.canonical(self.estimate)
        with mock.patch.object(archive.subprocess, "run", return_value=
                subprocess.CompletedProcess([], 0, raw, b"")) as run:
            self.assertEqual(self.call("estimate"), raw)
        self.assertEqual(run.call_args.kwargs["input"], self.ops.remote_program(
            "estimate", self.binding, self.digest, archive.JOB_ID, None).encode())
        self.assertEqual(run.call_args.kwargs["timeout"], 90)

    def test_forbidden_actions_never_reach_subprocess(self):
        with mock.patch.object(archive.subprocess, "run") as run:
            for action in ("stage", "preflight", "submit", "status", "inspect", "provider", "", "FETCH"):
                with self.subTest(action=action), self.assertRaises(ValueError):
                    self.call(action)
            run.assert_not_called()

    def test_payload_wallcap_and_job_overrides_are_rejected(self):
        changes = ({"payload": b"authorization"}, {"seconds": 241}, {"seconds": 240.0},
                   {"job": "another-job"}, {"inventory": None},
                   {"inventory": {"job_id": "1"}})
        with mock.patch.object(archive.subprocess, "run") as run:
            for change in changes:
                with self.subTest(change=change), self.assertRaises(ValueError):
                    self.call(**change)
            with self.assertRaises(ValueError):
                self.call("estimate", inventory=self.estimate)
            run.assert_not_called()

    def test_alternate_binding_or_freeze_is_rejected(self):
        changed = copy.deepcopy(self.binding)
        changed["output_path"] += "-other"
        with mock.patch.object(archive.subprocess, "run") as run:
            for binding, digest in ((changed, self.digest), (self.binding, "0" * 64)):
                with self.assertRaises(ValueError):
                    self.transport("fetch", binding, digest, job=archive.JOB_ID,
                                   seconds=240, inventory=self.estimate)
            run.assert_not_called()

    def test_program_byte_cap_blocks_before_subprocess(self):
        with mock.patch.object(self.ops, "remote_program", return_value="x" * (archive.MAX_PROGRAM_BYTES + 1)), \
                mock.patch.object(archive.subprocess, "run") as run, self.assertRaises(ValueError):
            self.call()
        run.assert_not_called()

    def test_timeout_has_one_attempt_and_propagates(self):
        with mock.patch.object(archive.subprocess, "run", side_effect=
                subprocess.TimeoutExpired(["INTERCEPTED SSH"], 240)) as run, \
                self.assertRaises(subprocess.TimeoutExpired):
            self.call()
        run.assert_called_once()

    def test_nonzero_ssh_exit_has_one_attempt(self):
        with mock.patch.object(archive.subprocess, "run", return_value=
                subprocess.CompletedProcess([], 255, b"", b"SYNTHETIC SSH FAILURE")) as run, \
                self.assertRaisesRegex(RuntimeError, "SYNTHETIC SSH FAILURE"):
            self.call()
        run.assert_called_once()

    def test_ops_and_runtime_drift_fail_without_modifying_real_files(self):
        original_read = Path.read_bytes
        for target in (archive.OPS_PATH, archive.FREEZE_PATH,
                       archive.EXECUTION / "execution-binding.json"):
            def drift(path, target=target):
                data = original_read(path)
                return data + b"SYNTHETIC DRIFT" if path == target else data
            with self.subTest(path=str(target)), mock.patch.object(Path, "read_bytes", drift), \
                    mock.patch.object(archive.subprocess, "run") as run, self.assertRaises(ValueError):
                self.call()
            run.assert_not_called()

    @contextlib.contextmanager
    def synthetic_fetch(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            self.ops.save(root / "submissions/model.json", {"job_id": archive.JOB_ID, "synthetic": True})
            files = {"accounting.txt": b"SYNTHETIC ACCOUNTING", "model-001/summary.json": b'{"synthetic":true}'}
            inventory = {name: {"bytes": len(raw), "sha256": self.ops.sha(raw)}
                         for name, raw in sorted(files.items())}
            estimate = dict(job_id=archive.JOB_ID, source_bytes=sum(map(len, files.values())),
                regular_files=len(files), inventory=inventory, inventory_sha256=self.ops.sha(self.ops.canonical(inventory)))
            raw = self.ops.make_archive(files)
            with mock.patch.object(self.ops, "ROOT", root), \
                    mock.patch.object(self.ops, "identity", return_value=(self.frozen, self.binding, self.digest)), \
                    mock.patch.object(self.ops, "remote", self.transport), contextlib.redirect_stdout(io.StringIO()):
                yield root, estimate, raw, files

    def test_original_fetch_writes_original_canonical_intents_and_full_archive(self):
        with self.synthetic_fetch() as (root, estimate, raw, files):
            responses = [subprocess.CompletedProcess([], 0, self.ops.canonical(estimate), b""),
                         subprocess.CompletedProcess([], 0, raw, b"")]
            with mock.patch.object(archive.subprocess, "run", side_effect=responses) as run:
                self.ops.fetch()
                self.assertEqual(run.call_count, 2)
                with self.assertRaisesRegex(ValueError, "no retry"):
                    self.ops.fetch()
                self.assertEqual(run.call_count, 2)
            intent = self.ops.read(root / "fetch.intent.json")
            self.assertEqual(intent, dict(job_id=archive.JOB_ID, inventory_sha256=estimate["inventory_sha256"], no_retry=True))
            self.assertEqual((root / "transfer-001.tar.gz").read_bytes(), raw)
            receipt = self.ops.read(root / "transfer-001.json")
            self.assertEqual(receipt["files"], estimate["inventory"])
            for name, data in files.items():
                self.assertEqual((root / "retrieved-001" / name).read_bytes(), data)

    def test_fetch_timeout_retains_exclusive_intent_and_blocks_repeat(self):
        with self.synthetic_fetch() as (root, estimate, raw, files):
            with mock.patch.object(archive.subprocess, "run", side_effect=[
                    subprocess.CompletedProcess([], 0, self.ops.canonical(estimate), b""),
                    subprocess.TimeoutExpired(["INTERCEPTED SSH"], 240)]) as run:
                with self.assertRaises(subprocess.TimeoutExpired):
                    self.ops.fetch()
                self.assertTrue((root / "fetch.intent.json").is_file())
                self.assertFalse((root / "transfer-001.tar.gz").exists())
                with self.assertRaisesRegex(ValueError, "no retry"):
                    self.ops.fetch()
                self.assertEqual(run.call_count, 2)

    def test_mismatching_archive_retained_and_never_promoted(self):
        with self.synthetic_fetch() as (root, estimate, raw, files):
            different = self.ops.make_archive({"synthetic.txt": b"CHANGED EVIDENCE"})
            with mock.patch.object(archive.subprocess, "run", side_effect=[
                    subprocess.CompletedProcess([], 0, self.ops.canonical(estimate), b""),
                    subprocess.CompletedProcess([], 0, different, b"")]) as run, \
                    self.assertRaisesRegex(ValueError, "differs from terminal estimate"):
                self.ops.fetch()
            self.assertEqual(run.call_count, 2)
            self.assertEqual((root / "transfer-001.tar.gz").read_bytes(), different)
            self.assertFalse((root / "transfer-001.json").exists())
            self.assertFalse((root / "retrieved-001").exists())

    def test_entrypoint_rejects_nonarchive_operations_before_loading(self):
        with mock.patch.object(archive, "load_frozen_ops") as load:
            with self.assertRaises(ValueError):
                archive.run_action("submit")
            load.assert_not_called()
        with contextlib.redirect_stderr(io.StringIO()), self.assertRaises(SystemExit):
            archive.main(["fetch", "--authorization", "forbidden.json"])

    def test_entrypoint_calls_original_fetch_and_restores_transport(self):
        original = self.ops.remote
        with mock.patch.object(archive, "load_frozen_ops", return_value=(
                self.ops, self.frozen, self.binding, self.digest)), \
                mock.patch.object(self.ops, "fetch", side_effect=lambda: self.assertIsInstance(
                    self.ops.remote, archive.ArchiveTransport)) as fetch:
            archive.run_action("fetch")
        fetch.assert_called_once_with()
        self.assertIs(self.ops.remote, original)


if __name__ == "__main__":
    unittest.main(verbosity=2)
