import json
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch
from preflight import verify,validate_dataset

class PreflightTests(unittest.TestCase):
    def test_exact_bytes_staged_and_timeout_arguments(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);(root/'a.dfy').write_bytes(b'method A() {}\r\n')
            def fake(cmd,cwd,**kwargs):
                self.assertEqual((Path(cwd)/'program.dfy').read_bytes(),b'method A() {}\r\n')
                self.assertEqual(cmd[:5],['timeout','-k','5s','10s','dafny'])
                return SimpleNamespace(returncode=4,stdout='postcondition error',stderr='')
            with patch('preflight.subprocess.run',side_effect=fake):
                r=verify(dict(path='a.dfy',partition='hints_removed',sha256='test',bytes=15),root,root/'out')
            self.assertEqual(r['legacy_outcome'],'GOAL_UNPROVEN')
            self.assertEqual(r['exit_code'],4)
    def test_nonproof_and_success_categories_preserved(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);(root/'a.dfy').write_text('')
            for code,text,outcome in [(124,'','FAIL'),(2,'parse error','FAIL'),(0,'0 errors','SUCCESS')]:
                with patch('preflight.subprocess.run',return_value=SimpleNamespace(returncode=code,stdout=text,stderr='')):
                    r=verify(dict(path='a.dfy'),root,root/'out')
                self.assertEqual((r['exit_code'],r['legacy_outcome']),(code,outcome))
    def test_wrong_revision_rejected(self):
        with patch('preflight.subprocess.check_output',return_value='wrong\n'):
            with self.assertRaises(ValueError):validate_dataset(Path('.'),{'revision':'expected'})
if __name__=='__main__':unittest.main()
