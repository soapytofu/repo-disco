"""Offline, fake transport/process only; never launches Dafny or a provider."""
import copy
import importlib.util
import json
from pathlib import Path
import subprocess
import types
import unittest
import dafny_gate as gate

ROOT = Path(__file__).resolve().parent

def load_case(name='correct'):
    root = ROOT / 'controls' / name
    return ({p.name:p.read_bytes() for p in root.glob('*.dfy')}, json.loads((root/'profile.json').read_bytes()))

def csv_data(units):
    return (','.join(gate.HEADER)+'\n'+''.join(f'{n},{v},00:00:00.1,100,0\n' for n,v in units.items())).encode()

def evidence(profile, failed=()):
    units={n:'Failed' if n in failed else 'Passed' for n in profile['required_units']}
    out=(('Client.dfy(1,1): Error: a postcondition could not be proved\n' if failed else '')+
         f'Dafny program verifier finished with {len(units)-len(failed)} verified, {len(failed)} errors\n').encode()
    return gate.record_from_raw(profile,'fresh',4 if failed else 0,out,b'',{'results.csv':csv_data(units)},.1,100)

class GateTests(unittest.TestCase):
    def setUp(self): self.files,self.profile=load_case()
    def score(self, record): return gate.score(self.files,self.profile,record,'fresh')
    def test_complete_and_helper_failure(self):
        self.assertTrue(self.score(evidence(self.profile))['strict_success'])
        result=self.score(evidence(self.profile,['Helper.Transfer (correctness)']))
        self.assertFalse(result['strict_success']); self.assertEqual(result['units']['Client.Target (correctness)'],'Passed')
    def test_omitted_input_or_target_rejected(self):
        for field in ['verification_inputs','required_units']:
            p=copy.deepcopy(self.profile)
            if field=='verification_inputs': p[field]=['All.dfy']
            else: del p[field]['Helper.Transfer (correctness)']
            with self.assertRaises(gate.GateError): gate.validate_scope(self.files,p)
        r=evidence(self.profile);r['command']=['dafny','verify','--verify-included-files','--log-format','csv','All.dfy']
        with self.assertRaises(gate.GateError): self.score(r)
    def test_changed_contract_provider_and_bypass_rejected_by_pins(self):
        for name,bad in [('Client.dfy',b'ensures true'),('Helper.dfy',b'assume false;'),('Kernel.dfy',b'{:verify false}')]:
            files=dict(self.files);files[name]+=bad
            with self.assertRaises(gate.GateError): gate.validate_scope(files,self.profile)
    def test_actual_method_guard_rejects_bypasses_and_wrong_header(self):
        spec=importlib.util.spec_from_file_location('pinned_method_guard',ROOT/'policy/body_guard.py')
        policy=importlib.util.module_from_spec(spec);spec.loader.exec_module(policy)
        task=json.loads((ROOT/'policy/task.json').read_bytes())
        seed={p.name:p.read_text() for p in (ROOT/'policy/seed').glob('*.dfy')}
        valid={'Helper.dfy':'r := K.Entry(m,key);', 'Client.dfy':'remaining := K.Erase(m,key); removed := K.Entry(m,key);'}
        policy.parse_response(json.dumps(valid),seed,task)
        for bad in ['assume false;', '{:verify false}', 'assert {:axiom} false;', '} ensures true {']:
            payload=dict(valid);payload['Helper.dfy']=bad
            with self.assertRaises(ValueError): policy.parse_response(json.dumps(payload),seed,task)
        changed=dict(seed);changed['Helper.dfy']=changed['Helper.dfy'].replace('ensures','requires',1)
        with self.assertRaises(ValueError): policy.parse_response(json.dumps(valid),changed,task)
    def test_stale_missing_altered_evidence(self):
        for field,value in [('run_id','old'),('source_sha256',{}),('profile_sha256','x'),('toolchain',{}),
                            ('attempts',True),('model_calls',False),('raw_sha256',{})]:
            r=evidence(self.profile);r[field]=value
            with self.assertRaises(gate.GateError): self.score(r)
        r=evidence(self.profile);del r['raw_base64']['stdout.txt']
        with self.assertRaises(gate.GateError): self.score(r)
    def test_missing_duplicate_unknown_csv_units(self):
        full={n:'Passed' for n in self.profile['required_units']}
        for data in [b'',csv_data(dict(list(full.items())[1:])),csv_data(full)+csv_data(full).split(b'\n',1)[1],
                     csv_data({'Alien.X (correctness)':'Passed'}),csv_data(full).replace(b'Passed',b'Unknown',1)]:
            r=gate.record_from_raw(self.profile,'fresh',0,b'Dafny program verifier finished with 5 verified, 0 errors\n',b'',{'r.csv':data},.1)
            with self.assertRaises(gate.GateError): self.score(r)
    def test_warning_frontend_timeout_and_resource_categories(self):
        cases=[(2,b'4 warnings\nDafny program verifier finished with 5 verified, 0 errors\n','WARNING_ONLY'),
               (2,b'1 parse errors detected\n','PARSE_FAILURE'),(2,b'1 resolution/type errors detected\n','RESOLUTION_OR_TYPE_FAILURE'),
               (124,b'','TIMEOUT'),(137,b'','KILLED'),(4,b'Error: Verification timed out\n','VERIFIER_TIMEOUT'),
               (4,b'Error: Verification out of resource\n','RESOURCE_EXHAUSTED'),(9,b'','UNCLASSIFIED_ERROR')]
        for code,out,expected in cases:
            data={'r.csv':csv_data({n:'Passed' for n in self.profile['required_units']})} if expected=='WARNING_ONLY' else {}
            r=gate.record_from_raw(self.profile,'fresh',code,out,b'',data,.1)
            result=self.score(r);self.assertEqual(result['category'],expected);self.assertFalse(result['strict_success'])
    def test_inconsistent_summary_and_exit(self):
        for code,out in [(0,b'Dafny program verifier finished with 4 verified, 0 errors\n'),
                         (2,b'Dafny program verifier finished with 5 verified, 0 errors\n')]:
            r=gate.record_from_raw(self.profile,'fresh',code,out,b'',{'r.csv':csv_data({n:'Passed' for n in self.profile['required_units']})},.1)
            with self.assertRaises(gate.GateError): self.score(r)
    def test_include_closure_comments_and_escape(self):
        self.assertEqual(gate.include_edges({'a.dfy':b'// include "outside"\n/* include "x" */ module X {}'}),{'a.dfy':[]})
        for data in [b'include "../external.dfy"', b'include "/outside.dfy"', b'include {:x} "a.dfy"', b'include "missing.dfy"',b'/* unclosed']:
            with self.assertRaises(gate.GateError): gate.include_edges({'a.dfy':data})
    def test_fake_process_exact_inputs_and_raw_metrics(self):
        def fake(args, cwd, **kwargs):
            self.assertEqual(args[-len(self.files):],sorted(self.files))
            self.assertEqual({p.name:p.read_bytes() for p in cwd.glob('*.dfy')},self.files)
            (cwd/'result.csv').write_bytes(csv_data({n:'Passed' for n in self.profile['required_units']}))
            (cwd/'maxrss.txt').write_text('12345\n')
            return types.SimpleNamespace(returncode=0,stdout=b'Dafny program verifier finished with 5 verified, 0 errors\n',stderr=b'')
        result=self.score(gate.verify(self.files,self.profile,'fresh',fake))
        self.assertTrue(result['strict_success']);self.assertEqual(result['peak_rss_kib'],12345)
    def test_fake_timeout_and_execution_failure(self):
        for exception,category in [(subprocess.TimeoutExpired('fake',75),'TIMEOUT'),(OSError('fake'),'EXECUTION_ERROR')]:
            def fake(*a,**k): raise exception
            self.assertEqual(self.score(gate.verify(self.files,self.profile,'fresh',fake))['category'],category)
    def test_unknown_verus_or_toolchain_closed(self):
        for field,value in [('language','verus'),('dafny_version','4.4.0')]:
            p=dict(self.profile);p[field]=value
            with self.assertRaises(gate.GateError): gate.validate_scope(self.files,p)
    def test_frozen_controls_and_immutable_inputs(self):
        for name,digest in json.loads((ROOT/'fixture-manifest.json').read_bytes()).items():
            self.assertEqual(gate.sha((ROOT/name).read_bytes()),digest,name)
        for case in json.loads((ROOT/'controls.json').read_bytes())['cases']:
            files,p=load_case(case['id']);gate.validate_scope(files,p)

if __name__=='__main__': unittest.main(verbosity=2)
