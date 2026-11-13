"""Non-model construction, source-boundary and parser tests."""
from pathlib import Path
import ast,json,tempfile,unittest
from unittest.mock import patch
import build as b
import body_guard as guard
import extract_response as envelope
import repair_protocol as protocol
import preflight

ROOT=Path(__file__).resolve().parent
load=lambda p:json.loads(p.read_text())
files=lambda p:{x.name:x.read_text() for x in p.glob('*.dfy')}

class Tests(unittest.TestCase):
    def test_exact_regeneration_and_counts(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);b.generate(root)
            for p in root.rglob('*'):
                if p.is_file():self.assertEqual(p.read_bytes(),(ROOT/('all-cases.json' if p.name=='cases.json' else p.relative_to(root))).read_bytes())
        cases=load(ROOT/'all-cases.json');self.assertEqual(len(cases),36)
        self.assertEqual(sum(c['expected']=='success' for c in cases),12)
        self.assertEqual(sum(c['expected']=='termination' for c in cases),2)
        self.assertEqual(sum(c['variant']=='faulty' for c in cases),6)

    def test_all_body_replays_and_protected_sources(self):
        cases=load(ROOT/'all-cases.json')
        for task in load(ROOT/'tasks.json'):
            template=files(ROOT/'templates'/task['task_id']);base=files(ROOT/'fixtures'/task['task_id']/'faulty')
            for case in [c for c in cases if c['task_id']==task['task_id']]:
                original=files(ROOT/case['path']);payload={}
                for n in task['editable_files']:
                    pre,suf=guard.split_seed(template[n]);self.assertTrue(original[n].startswith(pre) and original[n].endswith(suf))
                    payload[n]=original[n][len(pre):-len(suf)]
                candidate,_=protocol.apply_response(json.dumps(payload),base,template,task,b.hashes(base),guard,envelope)
                self.assertEqual(candidate,original)
                for n in set(template)-set(task['editable_files']):self.assertEqual(original[n],template[n])

    def test_contract_bypass_ambiguity_and_alias_rejections(self):
        for task in load(ROOT/'tasks.json'):
            template=files(ROOT/'templates'/task['task_id']);base=files(ROOT/'fixtures'/task['task_id']/'faulty')
            for body in ['assume false;','reveal K.Cut();','lemma Other() {}','var K := 0;','HelperA.Prove(s,t);','assert {:axiom} false;']:
                with self.assertRaises(ValueError):protocol.apply_response(json.dumps(dict.fromkeys(task['editable_files'],body)),base,template,task,b.hashes(base),guard,envelope)
            for raw in ['{} {}','{"x":"a","x":"b"}',json.dumps({'Kernel.dfy':'replace'})]:
                with self.assertRaises(ValueError):protocol.apply_response(raw,base,template,task,b.hashes(base),guard,envelope)
            altered=dict(base);altered['Kernel.dfy']+='\n'
            with self.assertRaises(ValueError):protocol.apply_response('{}',altered,template,task,b.hashes(base),guard,envelope)

    def test_guard_grammar_unchanged_except_task_registry(self):
        # Pinned upstream grammar is copied unchanged below policy.
        upstream=Path(__file__).parent/'upstream-guard.py'
        here=(ROOT/'body_guard.py').read_text();original=upstream.read_text()
        self.assertEqual(here[here.index('class Grammar:'):],original[original.index('class Grammar:'):])

    def test_faults_have_concrete_witnesses_and_lineage(self):
        cut=lambda t,x:max(0,x-t)
        self.assertEqual(cut(2,cut(3,4)),cut(5,4));self.assertFalse(2<4-3)
        self.assertFalse(0!=0);self.assertTrue(0<=1<=1 and 1!=0)
        self.assertNotIn('Prove(s[1..],t[1..]);',b.DEFINITIONS['weave_unweave']['faulty'])
        self.assertIn('Prove(s[1..],t[1..]);',b.DEFINITIONS['weave_unweave']['reference'])
        for task in load(ROOT/'tasks.json'):
            self.assertFalse(task['held_out']);self.assertEqual(task['failure_origin'],'analyst_constructed')
            self.assertEqual(len(task['editable_files']),1 if task['sharing']=='shared' else 2)

    def test_verifier_exact_staging_with_fake_process(self):
        from types import SimpleNamespace
        task=load(ROOT/'tasks.json')[0];src={n:s.encode() for n,s in files(ROOT/'fixtures'/task['task_id']/'faulty').items()};calls=[]
        def fake(command,cwd,capture_output,text):
            calls.append(command);self.assertEqual({p.name:p.read_bytes() for p in Path(cwd).glob('*.dfy')},src)
            (Path(cwd)/'fake.csv').write_bytes(b'a,b\r\n1,2\r\n')
            return SimpleNamespace(returncode=4,stdout='FAKE',stderr='')
        with patch.object(preflight.subprocess,'run',side_effect=fake):e=preflight.verify(src)
        self.assertEqual(len(calls),1);self.assertEqual(e['source_sha256'],{n:b.sha(v) for n,v in src.items()})
        self.assertEqual(e['csv']['fake.csv'],'a,b\r\n1,2\r\n');self.assertEqual(e['model_calls'],0)

    def test_revision_only_changes_witness_provider_encoding(self):
        for case in load(ROOT/'all-cases.json'):
            revised=files(ROOT/case['path']);original=files(ROOT.parent/case['path'])
            # In staged runtime, original providers are available as a pinned baseline.
            if not original:original=files(ROOT/'original-fixtures'/case['case_id'])
            if not case['task_id'].startswith('excluded_witness'):
                self.assertEqual(revised,original)
            else:
                self.assertEqual(set(n for n in revised if revised[n]!=original[n]),{'Kernel.dfy','Api.dfy'})
                self.assertNotIn('Candidate',revised['HelperA.dfy'])
                self.assertIn('export Public provides InRange, Feasible',revised['Kernel.dfy'])

if __name__=='__main__':unittest.main(verbosity=2)
