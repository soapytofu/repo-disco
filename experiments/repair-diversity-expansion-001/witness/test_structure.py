"""Compute-ops entry: original five design tests plus fake-process adapter tests."""
from pathlib import Path
import base64
import importlib.util
import types
import unittest
from unittest.mock import patch

ROOT=Path(__file__).resolve().parent


def local_module(name, filename):
    spec=importlib.util.spec_from_file_location(name,ROOT/filename)
    module=importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


design=local_module('frozen_local_design','test_design.py')
OriginalDesign=design.Design
v=local_module('fixed_fixture_compute_adapter','verify.py')


class AdapterTests(unittest.TestCase):
    def record(self, text, code=4):
        return {'stdout':text,'stderr':'','exit_code':code}

    def test_categories_and_strict_success(self):
        good='Dafny program verifier finished with 12 verified, 0 errors\n'
        self.assertEqual(v.classify(self.record(good,0)),'success')
        self.assertEqual(v.classify(self.record(good+'HelperA.dfy(2,1): Warning: no trigger\n',0)),'warning_only')
        self.assertNotEqual(v.classify(self.record(good,2)),'success')
        self.assertNotEqual(v.classify(self.record('Dafny program verifier finished with 0 verified, 0 errors\n',0)),'success')
        proof='HelperA.dfy(3,1): Error: assertion might not hold\nDafny program verifier finished with 8 verified, 1 error\n'
        self.assertEqual(v.classify(self.record(proof)),'proof_failure')
        termination=proof.replace('assertion might not hold','decreases expression might not decrease')
        self.assertEqual(v.classify(self.record(termination)),'termination_failure')
        self.assertEqual(v.classify(self.record(termination.replace('decreases expression','decreases clause'))),'termination_failure')
        hidden='HelperA.dfy(2,1): Error: member HiddenBounds does not exist in module Ops\n1 resolution/type errors detected\n'
        self.assertEqual(v.classify(self.record(hidden,2)),'resolution_failure')
        self.assertEqual(v.classify(self.record('HelperA.dfy(2,1): Error: this symbol not expected in Dafny\n1 parse errors detected\n',2)),'frontend_failure')
        self.assertEqual(v.classify(self.record(proof+'1 parse errors detected\n')),'frontend_failure')
        self.assertNotEqual(v.classify(self.record('Error: assertion might not hold\n')),'proof_failure')
        self.assertEqual(v.classify(self.record('',124)),'timeout')

    def test_case_specific_diagnostic_matching(self):
        summary='\nDafny program verifier finished with 9 verified, 1 error\n'
        kinds={'precondition':'a precondition for this call could not be proved',
               'postcondition':'possible violation of postcondition of forall statement',
               'assertion':'assertion might not hold'}
        for name,text in kinds.items():
            case={'expected':'proof_failure','expected_exit':4,'expected_diagnostic':name}
            record=self.record('HelperA.dfy(3,1): Error: '+text+summary)
            self.assertTrue(v.matches(case,record))
            wrong=dict(case,expected_diagnostic='assertion' if name!='assertion' else 'precondition')
            self.assertFalse(v.matches(wrong,record))
        # A word in source context is not a diagnostic for a different error.
        record=self.record('  requires precondition\nHelperA.dfy(3,1): Error: assertion might not hold'+summary)
        self.assertNotIn('precondition',v.diagnostic_details(record)['diagnostic_categories'])

    def test_exact_fixture_bytes_and_raw_csv_with_one_fake_process(self):
        case=next(c for c in v.load(ROOT/'cases.json') if c['variant']=='reference')
        files={p.name:p.read_bytes() for p in sorted((ROOT/case['path']).glob('*.dfy'))}
        seen=[]
        raw_csv=b'Name,Outcome\r\nHelperA.Prove,Valid\r\n'
        stdout=b'Dafny program verifier finished with 12 verified, 0 errors\r\n'
        def fake(command,cwd,capture_output,timeout):
            seen.append(command)
            self.assertEqual({p.name:p.read_bytes() for p in Path(cwd).glob('*.dfy')},files)
            self.assertEqual(command,v.COMMAND)
            self.assertEqual(timeout,75)
            (Path(cwd)/'results.csv').write_bytes(raw_csv)
            return types.SimpleNamespace(returncode=0,stdout=stdout,stderr=b'')
        with patch.object(v.subprocess,'run',side_effect=fake):
            record=v.verify(files)
        self.assertEqual(len(seen),1)
        self.assertEqual(record['attempts'],1)
        self.assertEqual(record['model_calls'],0)
        self.assertEqual(record['source_sha256'],case['source_sha256'])
        self.assertEqual(record['csv']['results.csv'],raw_csv.decode())
        self.assertEqual(base64.b64decode(record['csv_base64']['results.csv']),raw_csv)
        self.assertEqual(base64.b64decode(record['stdout_base64']),stdout)
        self.assertEqual(record['csv_sha256']['results.csv'],v.sha(raw_csv))

    def test_manifests_pin_runtime_fixtures_and_original_bytes(self):
        pins=v.validate_pins(ROOT)
        self.assertIn('verify.py',pins)
        self.assertIn('cases.json',pins)
        self.assertIn('fixture-manifest.json',pins)
        preservation=v.load(ROOT/'adapter-preservation-001.json')['files']
        for name,digest in preservation.items():
            self.assertEqual(v.sha((ROOT/name).read_bytes()),digest)


if __name__=='__main__':
    unittest.main(verbosity=2)
