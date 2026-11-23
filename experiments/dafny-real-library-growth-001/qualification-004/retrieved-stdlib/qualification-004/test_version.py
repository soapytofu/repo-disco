import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import collect


class VersionTests(unittest.TestCase):
    def test_solver_uses_single_dash_and_retains_streams(self):
        with tempfile.TemporaryDirectory() as tmp:
            out=Path(tmp)
            with patch.object(collect,'capture',return_value=({'exit_code':0,'timeout':False,'elapsed_seconds':.1},b'Z3 version 4.12.1\n',b'')) as run:
                self.assertEqual(collect.capture_version('/p/z3','-version',out,'solver'),'Z3 version 4.12.1')
            self.assertEqual(run.call_args.args[0],['/p/z3','-version'])
            self.assertEqual((out/'solver-version.stderr').read_bytes(),b'')
            self.assertEqual(json.loads((out/'solver-version.json').read_bytes())['exit_code'],0)

    def test_error_and_timeout_preserved_before_rejection(self):
        for code,timed in [(1,False),(0,True)]:
            with self.subTest(code=code,timed=timed), tempfile.TemporaryDirectory() as tmp:
                out=Path(tmp)
                with patch.object(collect,'capture',return_value=({'exit_code':code,'timeout':timed,'elapsed_seconds':.1},b'partial',b'bad option')):
                    with self.assertRaises(AssertionError):collect.capture_version('/p/z3','-version',out,'solver')
                self.assertEqual((out/'solver-version.stdout').read_bytes(),b'partial')
                self.assertEqual((out/'solver-version.stderr').read_bytes(),b'bad option')
                self.assertEqual(json.loads((out/'solver-version.json').read_bytes())['timeout'],timed)

if __name__=='__main__':unittest.main()
