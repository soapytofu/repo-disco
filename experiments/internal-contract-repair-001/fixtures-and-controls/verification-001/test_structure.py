"""Offline tests for two fresh seeds and their isolated standard-library adapter."""
from pathlib import Path
import base64
import copy
import csv
import io
import json
import shutil
import subprocess
import sys
import tempfile
import types
import unittest
from unittest.mock import patch

ROOT=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT))
from test_design import Construction
import verify as v


def cases():return json.loads((ROOT/'cases.json').read_bytes())
def fake_csv(case,helper='Failed',client='Failed'):
    units={'Helper.Transfer (correctness)':helper,'Client.Target (correctness)':client}
    units.update({name:'Passed' for name in case['expected_logged_provider_units']})
    output=io.StringIO(newline='')
    writer=csv.writer(output,lineterminator='\r\n')
    writer.writerow(['TestResult.DisplayName','TestResult.Outcome','TestResult.Duration','TestResult.ResourceCount','RandomSeed'])
    for name,outcome in units.items():writer.writerow([name,outcome,'00:00:00.001','1','0'])
    return output.getvalue().encode()


def synthetic_record(case,helper='Failed',client='Failed'):
    raw=fake_csv(case,helper,client)
    stdout=('Helper.dfy(10,2): Error: a postcondition could not be proved on this return path\n'
            'Client.dfy(10,18): Error: a precondition for this call could not be proved\n'
            'Dafny program verifier finished with 0 verified, 2 errors\n')
    return {'exit_code':4,'stdout':stdout,'stderr':'','source_sha256':case['source_sha256'],
            'csv':{'TestResults/fake.csv':raw.decode()},
            'csv_base64':{'TestResults/fake.csv':base64.b64encode(raw).decode()},
            'csv_sha256':{'TestResults/fake.csv':v.sha(raw)}}


class Runtime(unittest.TestCase):
    def test_complete_manifests_and_only_two_pending_checks(self):
        pins=v.validate_pins(ROOT)
        self.assertEqual(len(cases()),2)
        self.assertIn('inputs/parent/verify.py',pins)
        self.assertIn('inputs/parent/reviews/review-002/results-review.json',pins)
        self.assertIn('reused-controls.json',pins)
        self.assertNotEqual((ROOT/'verify.py').read_bytes(),(ROOT/'inputs/parent/verify.py').read_bytes())
        self.assertEqual(v.DAFNY_VERSION,'4.11.0+fcb2042d6d043a2634f0854338c08feeaaaf4ae2')
        self.assertEqual(v.Z3_VERSION,'Z3 version 4.12.1 - 64 bit')

    def test_fake_process_exact_sources_and_raw_csv_for_both_seeds(self):
        for case in cases():
            files={p.name:p.read_bytes() for p in (ROOT/case['path']).glob('*.dfy')}
            expected=synthetic_record(case);raw_csv=fake_csv(case)
            def fake(command,*,cwd,capture_output,timeout):
                self.assertEqual(command,v.COMMAND);self.assertEqual(timeout,75)
                self.assertEqual({p.name:p.read_bytes() for p in Path(cwd).glob('*.dfy')},files)
                dest=Path(cwd)/'TestResults';dest.mkdir();(dest/'fake.csv').write_bytes(raw_csv)
                return types.SimpleNamespace(returncode=4,stdout=expected['stdout'].encode(),stderr=b'')
            with patch.object(v.subprocess,'run',side_effect=fake) as process:
                actual=v.verify(files)
            self.assertEqual(process.call_count,1)
            self.assertEqual(base64.b64decode(actual['csv_base64']['TestResults/fake.csv']),raw_csv)
            self.assertEqual(actual['source_sha256'],case['source_sha256'])
            self.assertEqual(actual['attempts'],1);self.assertEqual(actual['model_calls'],0)
            self.assertEqual(v.classify(actual),'proof_failure');self.assertTrue(v.matches(case,actual))
            self.assertEqual(v.named_details(case,actual)['local_targets'],{'Helper.Transfer':False,'Client.Target':False})

    def test_named_failure_gate_rejects_coarse_missing_and_conflicting_evidence(self):
        for case in cases():
            record=synthetic_record(case);self.assertTrue(v.matches(case,record))
            self.assertFalse(v.matches(case,synthetic_record(case,helper='Passed')))
            self.assertFalse(v.matches(case,synthetic_record(case,client='Passed')))
            bad=copy.deepcopy(record);bad['csv']={};self.assertFalse(v.matches(case,bad))
            bad=copy.deepcopy(record);bad['stdout']=bad['stdout'].replace('Helper.dfy','Client.dfy')
            self.assertFalse(v.matches(case,bad))
            bad=copy.deepcopy(record);bad['stdout']+='All.dfy(1,1): Error: this symbol not expected\n'
            self.assertFalse(v.matches(case,bad));self.assertEqual(v.classify(bad),'frontend_failure')
            bad=copy.deepcopy(record);bad['stdout']+='Helper.dfy(1,1): Warning: no trigger\n'
            self.assertFalse(v.matches(case,bad))
            bad=copy.deepcopy(record);name='TestResults/fake.csv';dup=base64.b64decode(bad['csv_base64'][name])+b'Helper.Transfer (correctness),Failed,0,0,0\r\n'
            bad['csv'][name]=dup.decode();bad['csv_base64'][name]=base64.b64encode(dup).decode();bad['csv_sha256'][name]=v.sha(dup)
            self.assertFalse(v.matches(case,bad))
            if case['expected_logged_provider_units']:
                bad=copy.deepcopy(record);old=base64.b64decode(bad['csv_base64'][name])
                removed=b'\r\n'.join(line for line in old.split(b'\r\n') if not line.startswith(b'Kernel.Entry '))
                bad['csv'][name]=removed.decode();bad['csv_base64'][name]=base64.b64encode(removed).decode();bad['csv_sha256'][name]=v.sha(removed)
                self.assertFalse(v.matches(case,bad))
            else:
                bad=copy.deepcopy(record);bad['source_sha256']['Kernel.dfy']='0'*64
                self.assertFalse(v.matches(case,bad))

    def test_manifest_only_isolated_import_and_compute_guard(self):
        pins=v.validate_pins(ROOT)
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory)
            for name in sorted(set(pins)|{'runtime-manifest.json'}):
                target=root/name;target.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(ROOT/name,target)
            script='''from pathlib import Path
import importlib.util,json
spec=importlib.util.spec_from_file_location("isolated_dual_seed",Path.cwd()/"verify.py")
v=importlib.util.module_from_spec(spec);spec.loader.exec_module(v)
pins=v.validate_pins(Path.cwd())
assert len(json.loads(Path("cases.json").read_bytes()))==2
print(json.dumps({"pins":len(pins),"stdlib_only":True,"verifier_calls":0,"model_calls":0}))
'''
            result=subprocess.run([sys.executable,'-B','-I','-c',script],cwd=root,capture_output=True,text=True,timeout=20)
            self.assertEqual(result.returncode,0,result.stdout+result.stderr)
            self.assertEqual(json.loads(result.stdout)['pins'],len(pins))
        with patch.dict(v.os.environ,{},clear=True),patch.object(v.subprocess,'run') as process:
            with self.assertRaisesRegex(AssertionError,'Compute allocation required'):v.run('verification-001')
            process.assert_not_called()


if __name__=='__main__':unittest.main(verbosity=2)
