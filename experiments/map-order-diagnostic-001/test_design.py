"""Offline diagnostic checks; actual proofs run only on a compute node."""
from collections import Counter
import ast
import hashlib
import json
from pathlib import Path
import types
import unittest
from unittest.mock import patch
import prepare as p
import preflight

class Tests(unittest.TestCase):
    def test_exact_sources_and_only_call_order_changed(self):
        declared=p.load(p.ROOT/'cases.json');generated=p.candidates()
        self.assertEqual(declared,[x for x,_ in generated])
        self.assertEqual(len(declared),4)
        for row,fs in generated:
            self.assertEqual(fs,p.files(p.ROOT/row['path']))
            self.assertEqual(p.hashes(fs),row['source_sha256'])
            tid=row['parent_trial'];task=p.load(p.ROOT/'parents'/tid/'task.json')
            bodies=json.loads(p.load(p.ROOT/'parents'/tid/'response.json')['text'])
            seed=p.files(p.ROOT/'seeds'/tid)
            for n,s in seed.items():
                if n not in bodies:self.assertEqual(s,fs[n]);continue
                prefix,suffix=p.body_guard.split_seed(s)
                self.assertTrue(fs[n].startswith(prefix) and fs[n].endswith(suffix))
                current=fs[n][len(prefix):-len(suffix)]
                self.assertEqual(Counter(current.splitlines()),Counter(bodies[n].splitlines()))
                if row['expected_exit']==0:self.assertGreater(current.index(p.CERT),current.index(p.FACT))
                else:self.assertEqual(current,bodies[n])

    def test_unadmitted_source_stays_unadmitted_with_two_clauses(self):
        for row,fs in p.candidates():
            task=p.load(p.ROOT/'parents'/row['parent_trial']/'task.json')
            for n in task['editable_files']:
                prefix,suffix=p.body_guard.split_seed(p.files(p.ROOT/'seeds'/row['parent_trial'])[n])
                body=fs[n][len(prefix):-len(suffix)]
                if row['parent_trial']=='map-dev-04':
                    self.assertIn(p.TWO,body)
                    with self.assertRaises(ValueError):p.body_guard.Grammar(body,task).sequence()
                else:p.body_guard.Grammar(body,task).sequence()
                with self.assertRaises(ValueError):p.review_syntax(body+'\nassume false;',task,row['parent_trial']=='map-dev-04')

    def test_fake_verifier_stages_exact_bytes_and_captures_csv(self):
        row,fs=p.candidates()[0];raw={n:s.encode() for n,s in fs.items()}
        def process(command,cwd,capture_output,text):
            self.assertEqual({x.name:x.read_bytes() for x in Path(cwd).glob('*.dfy')},raw)
            self.assertIn('--verify-included-files',command)
            (Path(cwd)/'fake.csv').write_text('EXACT CSV')
            return types.SimpleNamespace(returncode=4,stdout='FAKE',stderr='')
        with patch.object(preflight.subprocess,'run',side_effect=process) as call:result=preflight.verify(raw)
        self.assertEqual(call.call_count,1);self.assertEqual(result['csv'],{'fake.csv':'EXACT CSV'})
        self.assertEqual(result['source_sha256'],row['source_sha256'])
        self.assertEqual(result['model_calls'],0)

    def test_manifest_and_remote_scripts(self):
        for n,h in p.load(p.ROOT/'manifest.json').items():self.assertEqual(p.sha(p.ROOT/n),h,n)
        for node in ast.walk(ast.parse((p.ROOT/'ops.py').read_text())):
            if isinstance(node,ast.Constant) and isinstance(node.value,str) and node.value.startswith('import '):
                compile(node.value,'remote','exec')

if __name__=='__main__':unittest.main(verbosity=2)
