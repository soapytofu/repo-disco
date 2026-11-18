"""Fake transport boundary checks; never opens SSH or submits Slurm jobs."""
from pathlib import Path
import subprocess
import unittest
from unittest.mock import patch

import common as c
import ops


class TransportBoundaryTests(unittest.TestCase):
    def test_remote_transport_has_socket_and_hard_timeout(self):
        observed = []

        def fake_run(argv, **kwargs):
            observed.append((argv, kwargs))
            return subprocess.CompletedProcess(argv, 0, stdout=b'fake-result', stderr=b'')

        with patch.object(ops.subprocess, 'run', fake_run), patch.object(c, 'sha', return_value='a' * 64):
            self.assertEqual(ops.remote('print("offline fixture")', seconds=17), b'fake-result')
        self.assertEqual(len(observed), 1)
        argv, kwargs = observed[0]
        self.assertEqual(argv[0], 'ssh')
        self.assertIn(str(Path.home() / '.ssh/repodisco-codex-21.sock'), argv)
        self.assertIn('BatchMode=yes', argv)
        self.assertIn('ProxyCommand=false', argv)
        self.assertEqual(kwargs['timeout'], 17)
        self.assertIn('real-repository-growth-001/qualification-001', argv[-1])
        self.assertNotIn('prepare_key', argv[-1])

    def test_unknown_or_control_submission_rejected_before_transport(self):
        with patch.object(ops, 'remote', side_effect=AssertionError('transport reached')):
            for name in ('pair-alternative', 'batch-empty', 'all-controls'):
                with self.assertRaisesRegex(ValueError, 'Unknown verifier stage'):
                    ops.submit(name)


if __name__ == '__main__':
    unittest.main()
