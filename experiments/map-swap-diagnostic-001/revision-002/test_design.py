"""Check the single corrected negative control without real processes."""
import ast
import hashlib
import importlib.util
import json
from pathlib import Path
import sys
import types
import unittest
from unittest.mock import patch

ROOT=Path(__file__).resolve().parent
def load(p):return json.loads(p.read_text())
def files(p):return {f.name:f.read_text() for f in p.glob('*.dfy')}
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def module(name,p):
    s=importlib.util.spec_from_file_location(name,p);m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m

class Tests(unittest.TestCase):
    def test_only_false_control_binder_changes(self):
        before=files(ROOT/'previous');after=files(ROOT/'fixture')
        self.assertEqual(set(before),set(after))
        for name,text in before.items():
            expected=text.replace('assert forall fresh :: fresh == 0;','assert forall badKey0 :: badKey0 == 0;') if name=='HelperA.dfy' else text
            self.assertEqual(after[name],expected)
        self.assertEqual(before['HelperA.dfy'].count('assert forall fresh :: fresh == 0;'),1)
        for name,h in load(ROOT/'revision.json')['unchanged_policy_sha256'].items():self.assertEqual(sha(ROOT/'policy'/name),h)
        checks=load(ROOT/'checks.json');self.assertEqual(len(checks),1)
        self.assertEqual(checks[0]['source_sha256'],{p.name:sha(p) for p in (ROOT/'fixture').glob('*.dfy')})

    def test_exact_guard_reconstruction_and_false_truth_admission(self):
        guard=module('corrected_control_guard',ROOT/'policy/body_guard.py')
        envelope=module('corrected_control_envelope',ROOT/'policy/extract_response.py')
        seed=files(ROOT/'seed');candidate,_=envelope.parse_response((ROOT/'body.json').read_text(),seed,load(ROOT/'task.json'),guard)
        self.assertEqual(candidate,files(ROOT/'fixture'))
        self.assertIn('assert forall badKey0 :: badKey0 == 0;',candidate['HelperA.dfy'])
        for name,source in seed.items():
            if name.startswith('Helper'):
                a,b=guard.split_seed(source);self.assertTrue(candidate[name].startswith(a) and candidate[name].endswith(b))
            else:self.assertEqual(source,candidate[name])

    def test_isolated_fake_verifier_and_submission_scope(self):
        sys.path.insert(0,str(ROOT/'code'))
        from language.dafny import repository
        seed={n:s.encode() for n,s in files(ROOT/'fixture').items()}
        def fake(command,cwd,capture_output,text):
            self.assertEqual({p.name:p.read_bytes() for p in Path(cwd).glob('*.dfy')},seed)
            return types.SimpleNamespace(returncode=4,stdout='Error: assertion might not hold',stderr='')
        with patch.object(repository.subprocess,'run',side_effect=fake):
            evidence=repository.verify_repository(seed,'All.dfy',timeout=60).evidence
        from preflight import diagnostic
        self.assertEqual(diagnostic(evidence),'proof_failure')
        self.assertEqual(evidence['attempts'],1)
        ops=(ROOT/'ops.py').read_text();self.assertIn("REMOTE='formal-disco/outputs/map-swap-diagnostic-001/revision-002'",ops)
        self.assertIn('--job-name=map-swap-diag2',(ROOT/'verify.sbatch').read_text())
        for node in ast.walk(ast.parse(ops)):
            if isinstance(node,ast.Constant) and isinstance(node.value,str) and node.value.startswith('import '):compile(node.value.replace('REMOTE_ROOT',repr('formal-disco/outputs/map-swap-diagnostic-001/revision-002')),'remote','exec')

if __name__=='__main__':unittest.main(verbosity=2)
