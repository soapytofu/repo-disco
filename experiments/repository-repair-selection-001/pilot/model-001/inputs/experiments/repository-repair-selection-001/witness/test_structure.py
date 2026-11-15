"""Offline entry: construction, byte-exact staging and conservative diagnostics."""
from pathlib import Path
import base64
import importlib.util
import json
import shutil
import subprocess
import sys
import tempfile
import types
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))
from test_design import Design
import verify as verifier


class Adapter(unittest.TestCase):
    def test_conservative_status_and_case_specific_diagnostics(self):
        def row(code, text):
            return dict(exit_code=code, stdout=text, stderr='')
        valid = row(0, 'Dafny program verifier finished with 12 verified, 0 errors\n')
        self.assertEqual(verifier.classify(valid), 'success')
        self.assertEqual(verifier.classify(row(0, 'Dafny program verifier finished with 0 verified, 0 errors\n')), 'other')
        self.assertEqual(verifier.classify(row(0, 'All.dfy(1,1): Warning: example\n'+valid['stdout'])), 'warning_only')
        proof = row(4, 'HelperB.dfy(12,2): Error: a precondition for this call could not be proved\nDafny program verifier finished with 11 verified, 1 error\n')
        self.assertEqual(verifier.classify(proof), 'proof_failure')
        self.assertTrue(verifier.matches(dict(expected='proof_failure', expected_exit=4, expected_diagnostic='precondition'), proof))
        self.assertFalse(verifier.matches(dict(expected='proof_failure', expected_exit=4, expected_diagnostic='postcondition'), proof))
        self.assertEqual(verifier.classify(row(4, 'Dafny program verifier finished with 11 verified, 1 error\n')), 'other')
        termination = row(4, 'HelperB.dfy(12,2): Error: decreases expression might not decrease\nDafny program verifier finished with 11 verified, 1 error\n')
        self.assertEqual(verifier.classify(termination), 'termination_failure')
        resolution = row(2, "HelperB.dfy(12,2): Error: member DirectFinish does not exist in module Api\n1 resolution/type errors detected in All.dfy\n")
        self.assertEqual(verifier.classify(resolution), 'resolution_failure')
        self.assertFalse(verifier.matches(dict(expected='proof_failure', expected_exit=4, expected_diagnostic='precondition'), resolution))
        self.assertEqual(verifier.classify(row(2, 'All.dfy(1,1): Error: this symbol not expected\n1 parse errors detected\n')), 'frontend_failure')

    def test_one_fake_process_preserves_all_source_and_csv_bytes(self):
        case = json.loads((ROOT/'cases.json').read_bytes())[0]
        files = {p.name:p.read_bytes() for p in (ROOT/case['path']).glob('*.dfy')}
        stdout = b'Dafny program verifier finished with 12 verified, 0 errors\r\n'
        stderr = b'offline fake byte capture \xff\r\n'
        csv = b'Name,Outcome\r\nHelperA.Prove,FakeOnly\r\n'
        def fake(command, *, cwd, capture_output, timeout):
            self.assertEqual(command, verifier.COMMAND)
            self.assertEqual(timeout, 75)
            self.assertTrue(capture_output)
            self.assertEqual({p.name:p.read_bytes() for p in Path(cwd).glob('*.dfy')}, files)
            (Path(cwd)/'results').mkdir()
            (Path(cwd)/'results/verification.csv').write_bytes(csv)
            return types.SimpleNamespace(returncode=0, stdout=stdout, stderr=stderr)
        with patch.object(verifier.subprocess, 'run', side_effect=fake) as process:
            result = verifier.verify(files)
        self.assertEqual(process.call_count, 1)
        self.assertEqual((result['attempts'], result['model_calls']), (1, 0))
        self.assertEqual(result['source_sha256'], case['source_sha256'])
        self.assertEqual(base64.b64decode(result['stdout_base64']), stdout)
        self.assertEqual(base64.b64decode(result['stderr_base64']), stderr)
        self.assertEqual(base64.b64decode(result['csv_base64']['results/verification.csv']), csv)

    def test_all_runtime_fixture_and_preservation_pins(self):
        pins = verifier.validate_pins(ROOT)
        self.assertEqual((ROOT/'verify.py').read_bytes(), (ROOT/'inputs/verifier/verify.py').read_bytes())
        self.assertIn('inputs/intersection-ancestor/README.md', pins)
        self.assertIn('inputs/gap-ancestor/README.md', pins)
        cases = json.loads((ROOT/'cases.json').read_bytes())
        self.assertTrue(all(case['expected']=='success' for case in cases[:6]))
        self.assertTrue(all(case['expected']!='success' for case in cases[6:]))

    def test_manifest_only_isolated_import_and_fake_stage(self):
        # Include every exact nested pin, including README names; no basename filtering.
        pins = verifier.validate_pins(ROOT)
        with tempfile.TemporaryDirectory() as directory:
            staged = Path(directory)
            for name in sorted(set(pins) | {'runtime-manifest.json'}):
                destination = staged/name
                destination.parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(ROOT/name, destination)
            script = '''from pathlib import Path
import importlib.util, json, types
from unittest.mock import patch
root = Path.cwd()
spec = importlib.util.spec_from_file_location("isolated_verifier", root/"verify.py")
v = importlib.util.module_from_spec(spec); spec.loader.exec_module(v)
pins = v.validate_pins(root)
case = json.loads((root/"cases.json").read_bytes())[0]
files = {p.name:p.read_bytes() for p in (root/case["path"]).glob("*.dfy")}
def fake(command, *, cwd, capture_output, timeout):
    assert {p.name:p.read_bytes() for p in Path(cwd).glob("*.dfy")} == files
    assert command == v.COMMAND and timeout == 75
    return types.SimpleNamespace(returncode=0, stdout=b"Dafny program verifier finished with 12 verified, 0 errors\\n", stderr=b"")
with patch.object(v.subprocess, "run", side_effect=fake) as process:
    result = v.verify(files)
assert process.call_count == 1 and result["model_calls"] == 0
assert v.classify(result) == "success"
print(json.dumps({"isolated_import":True,"exact_nested_pins":len(pins),"fake_processes":1,"actual_dafny_calls":0,"model_calls":0}))
'''
            result = subprocess.run([sys.executable, '-B', '-I', '-c', script], cwd=staged, capture_output=True, text=True, timeout=20)
            self.assertEqual(result.returncode, 0, result.stdout+result.stderr)
            record = json.loads(result.stdout)
            self.assertEqual(record['exact_nested_pins'], len(pins))
            self.assertEqual(record['actual_dafny_calls'], 0)


if __name__ == '__main__':
    unittest.main(verbosity=2)
