"""Construction plus complete isolated standard-library verifier packaging."""
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
sys.path.insert(0,str(ROOT))
from test_design import Construction
import verify as v


class Runtime(unittest.TestCase):
    def test_complete_pins_and_reused_verifier(self):
        pins = v.validate_pins(ROOT)
        self.assertEqual((ROOT/'verify.py').read_bytes(),(ROOT/'inputs/verify.py').read_bytes())
        self.assertIn('design.json',pins)
        self.assertIn('inputs/verify.py',pins)

    def test_fake_process_preserves_exact_workspace_and_csv_bytes(self):
        for task_id in ('capped_endpoint_return_migration','extracted_entry_return_migration'):
            files = {p.name:p.read_bytes() for p in (ROOT/'fixtures'/task_id/'paired_repair').glob('*.dfy')}
            csv = b'Name,Outcome\r\nClient.Target,FakeOnly\r\n'
            stdout = b'Dafny program verifier finished with 2 verified, 0 errors\r\n'
            def fake(command,*,cwd,capture_output,timeout):
                self.assertEqual(command,v.COMMAND)
                self.assertEqual(timeout,75)
                self.assertEqual({p.name:p.read_bytes() for p in Path(cwd).glob('*.dfy')},files)
                (Path(cwd)/'proof.csv').write_bytes(csv)
                return types.SimpleNamespace(returncode=0,stdout=stdout,stderr=b'')
            with patch.object(v.subprocess,'run',side_effect=fake) as process:
                result = v.verify(files)
            self.assertEqual(process.call_count,1)
            self.assertEqual(base64.b64decode(result['stdout_base64']),stdout)
            self.assertEqual(base64.b64decode(result['csv_base64']['proof.csv']),csv)
            self.assertEqual(result['model_calls'],0)
            self.assertEqual(v.classify(result),'success')

    def test_manifest_only_isolated_import_and_validation(self):
        pins = v.validate_pins(ROOT)
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            for name in sorted(set(pins)|{'runtime-manifest.json'}):
                target = root/name
                target.parent.mkdir(parents=True,exist_ok=True)
                shutil.copyfile(ROOT/name,target)
            script = '''from pathlib import Path
import importlib.util,json
root=Path.cwd()
spec=importlib.util.spec_from_file_location("isolated_internal_verifier",root/"verify.py")
v=importlib.util.module_from_spec(spec);spec.loader.exec_module(v)
pins=v.validate_pins(root)
assert len(json.loads((root/"cases.json").read_bytes()))==18
print(json.dumps({"validated_pins":len(pins),"stdlib_only":True,"real_verifier_calls":0,"model_calls":0}))
'''
            result = subprocess.run([sys.executable,'-B','-I','-c',script],cwd=root,capture_output=True,text=True,timeout=20)
            self.assertEqual(result.returncode,0,result.stdout+result.stderr)
            self.assertEqual(json.loads(result.stdout)['validated_pins'],len(pins))


if __name__=='__main__':
    unittest.main(verbosity=2)
