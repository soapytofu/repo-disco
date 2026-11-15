"""Construction, grammar and finite mathematics checks; no Dafny or live calls."""
from pathlib import Path
import base64
import importlib.util
import itertools
import json
import shutil
import socket
import subprocess
import tempfile
import types
import unittest
from unittest.mock import patch
import build as b

ROOT=Path(__file__).resolve().parent
GRAMMAR=ROOT/'inputs/experiments/repair-diversity-expansion-001/protocol/body_guard.py'


def exchange(m,p,q):
    result=dict(m);result[p]=m[q];result[q]=m[p];return result


def inverse(m,n):
    return (all(v in n and n[v]==x for x,v in m.items()) and
            all(v in m and m[v]==x for x,v in n.items()))


def override(a,z):return {**a,**z}
def restrict(m,keep):return {x:v for x,v in m.items() if x in keep}
def compose(f,g):return {x:g[y] for x,y in f.items() if y in g}
def maps(keys,values):
    return [{x:v for x,v in zip(keys,selected) if v is not None}
            for selected in itertools.product([None,*values],repeat=len(keys))]


class ConstructionTests(unittest.TestCase):
    def test_deterministic_complete_case_matrix(self):
        with tempfile.TemporaryDirectory() as folder:
            status=b.generate(folder)
            self.assertEqual(status['tasks'],2)
            self.assertEqual(status['planned_checks'],21)
            self.assertEqual(status['source_files'],183)
            self.assertEqual(status['logical_evidence_aliases'],4)
            self.assertEqual(status['expected_counts'],dict(success=4,proof_failure=15,resolution_failure=2))
            self.assertEqual((Path(folder)/'fixture-manifest.json').read_bytes(),(ROOT/'fixture-manifest.json').read_bytes())
            for name in ('tasks.json','cases.json','file_rules.json','control-aliases.json'):
                self.assertEqual((Path(folder)/name).read_bytes(),(ROOT/name).read_bytes())

    def test_only_two_selected_proof_bodies_can_differ(self):
        for task,variants in zip(b.TASKS,[b.INVERSE_VARIANTS,b.COMPOSE_VARIANTS]):
            template=b.sources(task,'empty')
            for variant in variants:
                source=b.sources(task,variant)
                for name,text in source.items():
                    if name not in ('HelperA.dfy','HelperB.dfy'):
                        self.assertEqual(text,template[name],(task,variant,name))
                    else:
                        boundary=b.body_boundary(text);base=b.body_boundary(template[name])
                        self.assertEqual(boundary['protected_sha256'],base['protected_sha256'])
                        self.assertEqual(text.encode()[:boundary['start']],template[name].encode()[:base['start']])
                        self.assertEqual(text.encode()[boundary['end']:],template[name].encode()[base['end']:])
                self.assertNotRegex('\n'.join(source.values()),r'\b(?:assume|axiom)\b|\{:verify\s+false\}')

    def test_pipeline_and_single_fault_selection_controls(self):
        tasks=json.loads((ROOT/'tasks.json').read_text())
        for task in tasks:
            tid=task['task_id'];seed=b.sources(tid,'faulty');reference=b.sources(tid,'reference')
            changed=[name for name in seed if seed[name]!=reference[name]]
            self.assertEqual(changed,[task['faulty_file']])
            for name in task['editable_files']:
                boundary=b.body_boundary(seed[name]);self.assertGreater(boundary['end'],boundary['start'])
            for name in ('ClientA.dfy','ClientB.dfy'):
                self.assertIn('import H = HelperB',seed[name]);self.assertIn('H.Prove(',seed[name])
            self.assertIn('import H = HelperA',seed['HelperB.dfy'])
            self.assertIn('H.Prove(',seed['HelperB.dfy'])
            self.assertNotIn('HelperB',seed['HelperA.dfy'])
            self.assertEqual(task['sharing'],'pipeline')
            self.assertEqual(task['file_rules']['HelperB.dfy']['call_types']['H.Prove'],
                             list(task['file_rules']['HelperA.dfy']['parameter_types'].values()))
            for text in seed.values():
                self.assertNotRegex(text.lower(),r'todo|deliberately|counterexample|bug|faulty|wrong')
        cases={case['case_id']:case for case in json.loads((ROOT/'cases.json').read_text())}
        aliases=json.loads((ROOT/'control-aliases.json').read_text())
        self.assertEqual(len(aliases),4)
        for alias in aliases:
            canonical=cases[alias['evidence_alias_of']]
            self.assertEqual(alias['source_sha256'],canonical['source_sha256'])
            self.assertEqual(alias['source_sha256'],b.hashes(b.sources(alias['task_id'],alias['variant'])))
            self.assertNotIn(alias['logical_case_id'],cases)
            self.assertFalse(alias['new_verifier_call']);self.assertFalse(alias['independent_observation'])

    def test_opaque_operation_views_and_hidden_elementary_calls(self):
        self.assertIn('export Public provides Put, Exchange reveals Inverse',b.INVERSE_KERNEL)
        self.assertIn('export Public provides Override, Restrict, Compose',b.COMPOSE_KERNEL)
        for name,source in [('HiddenPutAt',b.INVERSE_OPS),('HiddenRestrictAt',b.COMPOSE_VALUES)]:
            public=source.split('export Public provides ',1)[1].split('\n',1)[0]
            self.assertNotIn(name,public)
            self.assertIn('export Hidden provides K, '+name,source)
        self.assertNotIn('Exchange(',b.INVERSE_OPS.split('lemma PutAt',1)[1].split('lemma ExchangeShape',1)[0])
        self.assertNotIn('Compose(',b.COMPOSE_API)

    def test_existing_bounded_grammar_admits_math_failures_without_favoritism(self):
        spec=importlib.util.spec_from_file_location('existing_map_grammar',GRAMMAR)
        guard=importlib.util.module_from_spec(spec);spec.loader.exec_module(guard)
        admitted,rejected=0,0
        for tid,variants in zip(b.TASKS,[b.INVERSE_VARIANTS,b.COMPOSE_VARIANTS]):
            for variant,(a,z,_,_) in variants.items():
                for filename,body in [('HelperA.dfy',a),('HelperB.dfy',z)]:
                    rules=b.rules()[tid][filename]
                    with patch.object(guard,'policy',return_value=rules):
                        if variant=='hidden_call' and filename=='HelperA.dfy':
                            with self.assertRaises(ValueError):guard.Grammar(body,{}).sequence()
                            rejected+=1
                        else:
                            parser=guard.Grammar(body,{});parser.sequence();self.assertIsNone(parser.peek())
                            admitted+=1
        self.assertEqual((admitted,rejected),(48,2))

    def test_finite_inverse_exchange_both_directions_and_wrong_key_counterexample(self):
        checks=0
        for size in (2,3):
            for keys in itertools.combinations(range(3),size):
                for values in itertools.permutations((10,20,30),size):
                    m=dict(zip(keys,values));n={v:k for k,v in m.items()}
                    self.assertTrue(inverse(m,n))
                    for p,q in itertools.permutations(keys,2):
                        forward=exchange(m,p,q);backward=exchange(n,m[p],m[q])
                        self.assertEqual(set(forward),set(m));self.assertEqual(set(backward),set(n))
                        self.assertTrue(inverse(forward,backward))
                        self.assertTrue(inverse(backward,forward))
                        checks+=1
        self.assertEqual(checks,72)
        m={0:10,1:20};n={10:0,20:1}
        self.assertFalse(0 in n and 1 in n)
        self.assertEqual(exchange(m,0,1),{0:20,1:10})
        self.assertEqual(exchange(n,m[0],m[1]),{10:1,20:0})

    def test_finite_masked_composition_identity_and_overwritten_domain_counterexample(self):
        fs=maps([0,1],[0,1,2]);gs=maps([0,1,2],[-1,0]);checks=0
        for f1,f2,g in itertools.product(fs,fs,gs):
            left=compose(override(f1,f2),g)
            trimmed=restrict(f1,set(f1)-set(f2))
            right=override(compose(trimmed,g),compose(f2,g))
            self.assertEqual(set(left),set(right))
            self.assertEqual(left,right)
            checks+=1
        self.assertEqual(checks,6912)
        f1={0:10};f2={0:20};g={10:1}
        self.assertEqual(compose(override(f1,f2),g),{})
        self.assertEqual(override(compose(restrict(f1,set(f1)-set(f2)),g),compose(f2,g)),{})
        self.assertEqual(override(compose(f1,g),compose(f2,g)),{0:1})
        self.assertIn(f1[0],g);self.assertNotIn(f2[0],g)

    def test_runtime_pins_and_unchanged_legacy_verifier_functions(self):
        import verify as verifier
        pins=verifier.validate_pins(ROOT)
        self.assertIn('verify.sbatch',pins)
        self.assertEqual(verifier.sha((ROOT/verifier.UPSTREAM).read_bytes()),verifier.UPSTREAM_SHA256)
        for name in ('run','verify','matches','classify','diagnostic_details'):
            self.assertIs(getattr(verifier,name),getattr(verifier.upstream,name))
        self.assertEqual(verifier.upstream.ROOT,ROOT)

    def test_fake_verifier_stages_exact_bytes_and_keeps_csv_raw_output(self):
        import verify as verifier
        cases=json.loads((ROOT/'cases.json').read_text())
        selected=[next(c for c in cases if c['task_id']==tid and c['variant']=='reference') for tid in b.TASKS]
        for case in selected:
            files={p.name:p.read_bytes() for p in (ROOT/case['path']).glob('*.dfy')}
            stdout=b'Dafny program verifier finished with 12 verified, 0 errors\r\n'
            stderr=b'offline fake \xff\r\n';raw_csv=b'Name,Outcome\r\nHelperA.Prove,FakeOnly\r\n'
            def fake(command,cwd,capture_output,timeout):
                self.assertEqual(command,verifier.COMMAND);self.assertEqual(timeout,75)
                self.assertEqual({p.name:p.read_bytes() for p in Path(cwd).glob('*.dfy')},files)
                (Path(cwd)/'result.csv').write_bytes(raw_csv)
                return types.SimpleNamespace(returncode=0,stdout=stdout,stderr=stderr)
            with patch.object(verifier.upstream.subprocess,'run',side_effect=fake) as process:
                result=verifier.verify(files)
            self.assertEqual(process.call_count,1)
            self.assertEqual((result['attempts'],result['model_calls']),(1,0))
            self.assertEqual(result['source_sha256'],case['source_sha256'])
            self.assertEqual(base64.b64decode(result['stdout_base64']),stdout)
            self.assertEqual(base64.b64decode(result['stderr_base64']),stderr)
            self.assertEqual(base64.b64decode(result['csv_base64']['result.csv']),raw_csv)
            self.assertTrue(verifier.matches(case,result))

    def test_manifest_only_staging_includes_all_nested_inputs(self):
        import verify as verifier
        pins=verifier.validate_pins(ROOT)
        with tempfile.TemporaryDirectory() as folder:
            isolated=Path(folder).resolve()
            for name in sorted(set(pins)|{'runtime-manifest.json'}):
                destination=isolated/name;destination.parent.mkdir(parents=True,exist_ok=True)
                shutil.copy2(ROOT/name,destination)
            copied={p.relative_to(isolated).as_posix() for p in isolated.rglob('*') if p.is_file()}
            self.assertEqual(copied,set(pins)|{'runtime-manifest.json'})
            spec=importlib.util.spec_from_file_location('isolated_map_pipeline_adapter',isolated/'verify.py')
            obj=importlib.util.module_from_spec(spec)
            with patch.object(subprocess,'run',side_effect=AssertionError('No process in import/pin review')), \
                 patch.object(subprocess,'Popen',side_effect=AssertionError('No child process')), \
                 patch.object(socket,'socket',side_effect=AssertionError('No network')):
                spec.loader.exec_module(obj)
                self.assertEqual(obj.validate_pins(isolated),pins)
            self.assertEqual((isolated/'inputs/docs/corpus-family-split-plan.md').read_bytes(),
                             (ROOT/'inputs/docs/corpus-family-split-plan.md').read_bytes())


if __name__=='__main__':
    unittest.main(verbosity=2)
