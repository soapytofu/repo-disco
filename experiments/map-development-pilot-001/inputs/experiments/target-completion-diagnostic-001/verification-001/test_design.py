"""Offline logger-capture tests and exact source/guard checks; no real verifier."""
import ast
import hashlib
import json
from pathlib import Path
import types
import unittest
from unittest.mock import patch
import body_guard
import preflight

ROOT=Path(__file__).resolve().parent


class Tests(unittest.TestCase):
    def test_exact_guarded_partial_candidates_and_fixed_source(self):
        tasks={t['sharing']:t for t in json.loads((ROOT/'parent-tasks.json').read_text()) if t['depth']=='deep'}
        cases=json.loads((ROOT/'cases.json').read_text());self.assertEqual(len(cases),4)
        for case in cases:
            seed={p.name:p.read_text() for p in (ROOT/'seeds'/case['sharing']).glob('*.dfy')}
            fs={p.name:p.read_text() for p in (ROOT/case['path']).glob('*.dfy')};task=tasks[case['sharing']]
            bodies={}
            for name in task['editable_files']:
                prefix,suffix=body_guard.split_seed(seed[name]);self.assertTrue(fs[name].startswith(prefix));self.assertTrue(fs[name].endswith(suffix))
                bodies[name]=fs[name][len(prefix):-len(suffix)]
            actual,_=body_guard.parse_response(json.dumps(bodies),seed,task)
            self.assertEqual(actual,fs)
            self.assertEqual({n:hashlib.sha256(s.encode()).hexdigest() for n,s in fs.items()},case['source_sha256'])
            self.assertIn('H.Prove(m,a,b,c);',fs['ClientA.dfy'])
            self.assertIn('H.Prove(m,a,b,c);',fs['ClientB.dfy'])
            if case['sharing']=='shared':self.assertIn('H.Prove(m,a,b,c);',fs['HelperB.dfy'])

    def test_single_invocation_captures_csv_before_temp_cleanup(self):
        case=json.loads((ROOT/'cases.json').read_text())[0]
        fs={p.name:p.read_bytes() for p in (ROOT/case['path']).glob('*.dfy')}
        sample='TestResult.DisplayName,TestResult.Outcome\nHelperA.Prove (correctness),Passed\n'
        def fake(command,cwd,capture_output,text):
            self.assertIn('--verify-included-files',command);self.assertIn('--log-format',command)
            self.assertEqual({p.name:p.read_bytes() for p in Path(cwd).glob('*.dfy')},fs)
            d=Path(cwd)/'TestResults';d.mkdir();(d/'run.csv').write_text(sample)
            return types.SimpleNamespace(returncode=0,stdout='14 verified, 0 errors',stderr='')
        with patch.object(preflight.subprocess,'run',side_effect=fake) as call:
            result=preflight.verify(fs)
        self.assertEqual(call.call_count,1);self.assertEqual(result['csv'],{'TestResults/run.csv':sample})
        self.assertEqual(result['attempts'],1);self.assertEqual(result['model_calls'],0)
        self.assertEqual(result['csv_sha256']['TestResults/run.csv'],hashlib.sha256(sample.encode()).hexdigest())

    def test_named_dependencies_and_model_targets_are_explicit(self):
        for c in json.loads((ROOT/'cases.json').read_text()):
            self.assertEqual(set(c['target_dependencies']),{'HelperA.Prove','HelperB.Prove','ClientA.Target','ClientB.Target'})
            self.assertEqual(c['target_dependencies']['ClientA.Target'],['HelperA.Prove'])
            self.assertEqual(c['target_dependencies']['ClientB.Target'],['HelperB.Prove'])
            self.assertEqual(c['expected_local']['ClientA.Target'],True)
            self.assertEqual(c['expected_local']['ClientB.Target'],True)
            self.assertNotIn('ClientA.Target',c['editable_targets'])
            self.assertEqual(len(c['editable_targets']),1 if c['sharing']=='shared' else 2)

    def test_remote_scripts_and_pinned_bytes(self):
        for node in ast.walk(ast.parse((ROOT/'ops.py').read_text())):
            if isinstance(node,ast.Constant) and isinstance(node.value,str) and node.value.startswith('import '):
                compile(node.value.replace('REMOTE_ROOT',repr('formal-disco/outputs/target-completion-diagnostic-001')),'remote','exec')
        for name,h in json.loads((ROOT/'manifest.json').read_text()).items():
            self.assertEqual(hashlib.sha256((ROOT/name).read_bytes()).hexdigest(),h,name)


if __name__=='__main__':unittest.main(verbosity=2)
