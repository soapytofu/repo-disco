"""Offline mutation/guard/staging checks; no real verifier or model invocation."""
from collections import Counter
import ast
import json
from pathlib import Path
import types
import unittest
from unittest.mock import patch
import prepare as p
import preflight

class Tests(unittest.TestCase):
    def test_only_one_call_moved_per_editable_body(self):
        generated=p.candidates()
        self.assertEqual(p.load(p.ROOT/'cases.json'),[r for r,_ in generated])
        self.assertEqual(len(generated),4)
        edits=0
        for row,fs in generated:
            self.assertEqual(fs,p.files(p.ROOT/row['path']))
            self.assertEqual(p.hashes(fs),row['source_sha256'])
            tid=row['parent_trial'];task=p.load(p.ROOT/'parents'/tid/'task.json')
            parent=p.files(p.ROOT/'parents'/tid/'candidate');seed=p.files(p.ROOT/'seeds'/tid)
            for n,s in parent.items():
                if n not in task['editable_files']:self.assertEqual(fs[n],s);continue
                pre,suf=p.body_guard.split_seed(seed[n]);self.assertTrue(fs[n].startswith(pre) and fs[n].endswith(suf))
                before=s[len(pre):-len(suf)];after=fs[n][len(pre):-len(suf)]
                self.assertEqual(after,p.reorder(before));self.assertEqual(Counter(before.splitlines(keepends=True)),Counter(after.splitlines(keepends=True)))
                self.assertTrue(all(after.index(p.CERT)>after.index(f) for f in p.FACTS));edits+=1
        self.assertEqual(edits,6)
        self.assertEqual(len({tuple(sorted(row['source_sha256'].items())) for row,_ in generated}),2)

    def test_unchanged_guard_admits_all_reorders_and_rejects_bypasses(self):
        for row,fs in p.candidates():
            task=p.load(p.ROOT/'parents'/row['parent_trial']/'task.json')
            for n in task['editable_files']:
                pre,suf=p.body_guard.split_seed(p.files(p.ROOT/'seeds'/row['parent_trial'])[n]);body=fs[n][len(pre):-len(suf)]
                grammar=p.body_guard.Grammar(body,task);grammar.sequence();self.assertIsNone(grammar.peek())
                with self.assertRaises(ValueError):p.body_guard.Grammar(body+'\nassume false;',task).sequence()
                with self.assertRaises(AssertionError):p.reorder(body)
                original=p.files(p.ROOT/'parents'/row['parent_trial']/'candidate')[n][len(pre):-len(suf)]
                with self.assertRaises(AssertionError):p.reorder(original+'\n'+p.CERT+'\n')
                with self.assertRaises(AssertionError):p.reorder(original.replace(p.FACTS[0],''))

    def test_fake_verifier_preserves_source_and_csv_bytes(self):
        row,fs=p.candidates()[0];raw={n:s.encode() for n,s in fs.items()};csv=b'header\r\nvalue\r\n'
        def process(command,cwd,capture_output,text):
            self.assertEqual(command,['timeout','-k','5s','60s','dafny','verify','--verify-included-files','--log-format','csv','All.dfy'])
            self.assertEqual({x.name:x.read_bytes() for x in Path(cwd).glob('*.dfy')},raw)
            (Path(cwd)/'fake.csv').write_bytes(csv)
            return types.SimpleNamespace(returncode=0,stdout='FAKE',stderr='')
        with patch.object(preflight.subprocess,'run',side_effect=process) as call:result=preflight.verify(raw)
        self.assertEqual(call.call_count,1);self.assertEqual(result['csv'],{'fake.csv':csv.decode()})
        self.assertEqual(result['source_sha256'],row['source_sha256']);self.assertEqual(result['model_calls'],0)

    def test_pinned_sources_and_remote_scripts(self):
        for n,h in p.load(p.ROOT/'manifest.json').items():self.assertEqual(p.sha(p.ROOT/n),h,n)
        for node in ast.walk(ast.parse((p.ROOT/'ops.py').read_text())):
            if isinstance(node,ast.Constant) and isinstance(node.value,str) and node.value.startswith('import '):compile(node.value,'remote','exec')

if __name__=='__main__':unittest.main(verbosity=2)
