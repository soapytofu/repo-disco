"""Offline process and source-boundary checks; no native verifier invoked."""
import tempfile
from pathlib import Path
import sys
import unittest
import collect


class CaptureTests(unittest.TestCase):
    def test_exact_streams_and_exit(self):
        with tempfile.TemporaryDirectory() as tmp:
            r,out,err=collect.capture([sys.executable,'-c','import sys;print("out");print("err",file=sys.stderr);sys.exit(4)'],tmp,5)
            self.assertEqual((r['exit_code'],out,err),(4,b'out\n',b'err\n'))
            self.assertFalse(r['timeout'])

    def test_timeout_records_and_stops_child(self):
        with tempfile.TemporaryDirectory() as tmp:
            r,out,err=collect.capture([sys.executable,'-c','import time;print("started",flush=True);time.sleep(30)'],tmp,.75)
            self.assertTrue(r['timeout']);self.assertIn(b'started',out)
            self.assertLess(r['elapsed_seconds'],6)

    def test_scope_hashes_and_symlink_rejection(self):
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp);(p/'A.dfy').write_bytes(b'module A {}\n')
            self.assertEqual(collect.sources(p),{'A.dfy':collect.sha(b'module A {}\n')})
            (p/'B.dfy').symlink_to(p/'A.dfy')
            with self.assertRaises(AssertionError):collect.sources(p)

    def test_exclusive_evidence(self):
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp)/'record.json';collect.write(p,{'a':1})
            with self.assertRaises(FileExistsError):collect.write(p,{'a':2})


if __name__ == '__main__': unittest.main(verbosity=2)
