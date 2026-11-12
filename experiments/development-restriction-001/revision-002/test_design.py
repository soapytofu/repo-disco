"""Offline design, scoped syntax and fake-process checks. No live dispatch."""
import ast
import importlib.util
import itertools
import json
from pathlib import Path
import sys
import types
import unittest
from unittest.mock import patch

from build import ROOT, hashes, proof, sources


def module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    obj = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(obj)
    return obj


guard = module('move_guard', ROOT/'policy/body_guard.py')
envelope = module('move_envelope', ROOT/'policy/extract_response.py')
TASKS = json.loads((ROOT/'tasks.json').read_text())
CHECKS = json.loads((ROOT/'checks.json').read_text())


def files(path):
    return {p.name:p.read_text() for p in path.glob('*.dfy')}


def parse(task, bodies, seeds=None):
    seeds = seeds if seeds is not None else sources(task['depth'],task['sharing'],'empty')
    return envelope.parse_response(json.dumps(bodies), seeds, task, guard)


def restrict(m,keep):
    return {k:v for k,v in m.items() if k in keep}


def merge(m,n):
    return {**m,**n} if not set(m)&set(n) else {}


class Tests(unittest.TestCase):
    def test_finite_semantic_oracle_and_nonvacuous_clients(self):
        # Independent executable meaning; no Dafny or model execution.
        maps=[{k:v for k,v in enumerate(values) if v is not None}
              for values in itertools.product((None,-3,0,5),repeat=3)]
        filters=[{k for k in range(3) if mask & (1<<k)} for mask in range(8)]
        valid=empty_left=empty_filter=both_nonempty=0
        for m in maps:
            for n in maps:
                if set(m)&set(n):continue
                for keep in filters:
                    left=restrict(merge(m,n),keep)
                    right=merge(restrict(m,keep),restrict(n,keep))
                    self.assertEqual(left,right)
                    self.assertEqual(set(left),(set(m)|set(n))&keep)
                    for q in left:
                        self.assertIn(q,right); self.assertEqual(left[q],right[q])
                        self.assertEqual(left[q],m[q] if q in m else n[q])
                    valid+=1;empty_left+=not m;empty_filter+=not keep;both_nonempty+=bool(m and n)
        self.assertEqual((valid,empty_left,empty_filter,both_nonempty),(2744,512,343,1728))
        m={};n={1:5};keep={1};right=merge(restrict(m,keep),restrict(n,keep))
        self.assertIn(1,right);self.assertNotIn(1,m)
        self.assertNotEqual(set(right),set(restrict(m,keep)))
        # Merge is totalized to empty outside disjoint domains. The restriction
        # identity can then fail, so its disjointness assumption is substantive.
        m={0:2,1:3};n={0:9};keep={1}
        self.assertNotEqual(restrict(merge(m,n),keep),merge(restrict(m,keep),restrict(n,keep)))

    def test_exact_fixture_inventory_and_body_only_variants(self):
        self.assertEqual(len(TASKS),4); self.assertEqual(len(CHECKS),38)
        self.assertEqual(sum(c['phase']=='core' for c in CHECKS),8)
        self.assertEqual(sum(c['expected']=='success' for c in CHECKS),4)
        self.assertEqual(sum(c['expected']=='proof_failure' for c in CHECKS),30)
        self.assertEqual(sum(c['expected']=='resolution_failure' for c in CHECKS),4)
        for task in TASKS:
            self.assertIsNone(task['minimum_proof_depth']); self.assertFalse(task['held_out'])
            seed=sources(task['depth'],task['sharing'],'empty')
            self.assertEqual(hashes(seed),task['source_sha256'])
            for check in (c for c in CHECKS if c['task_id']==task['task_id']):
                fs=files(ROOT/check['path'])
                self.assertEqual(fs,sources(task['depth'],task['sharing'],check['variant']))
                self.assertEqual(hashes(fs),check['source_sha256'])
                for name,text in fs.items():
                    if name in task['editable_files']:
                        prefix,suffix=guard.split_seed(seed[name])
                        self.assertTrue(text.startswith(prefix)); self.assertTrue(text.endswith(suffix))
                    else:
                        self.assertEqual(text,seed[name])

    def test_shared_separate_matching_and_named_export_views(self):
        for depth in ('shallow','deep'):
            shared=sources(depth,'shared','reference'); separate=sources(depth,'separate','reference')
            self.assertEqual([n for n in shared if shared[n]!=separate[n]],['HelperB.dfy'])
            self.assertIn('H.Prove(m,n,keep);',shared['HelperB.dfy'])
            self.assertNotIn('import H = HelperA',separate['HelperB.dfy'])
            self.assertEqual(separate['HelperA.dfy'].replace('module HelperA','module HelperB'),separate['HelperB.dfy'])
        a=sources('shallow','shared','empty'); b=sources('deep','shared','empty')
        for name in ('Kernel.dfy','Api.dfy','Ops1.dfy','Ops2.dfy','ClientA.dfy','ClientB.dfy','All.dfy'):
            self.assertEqual(a[name],b[name])
        self.assertEqual(a['HelperA.dfy'].replace('Api`Shallow','Api`Deep').replace('Ops1`Hidden','Ops1`Public').replace('Ops2`Hidden','Ops2`Public'),b['HelperA.dfy'])

    def test_scoped_policy_exact_reconstruction_and_hidden_rejections(self):
        accepted=rejected=0
        for task in TASKS:
            for check in (c for c in CHECKS if c['task_id']==task['task_id']):
                bodies={name:'\n'+proof(task['depth'],check['variant']) for name in task['editable_files']}
                if check['variant']=='hidden_shortcut':
                    with self.assertRaises(ValueError): parse(task,bodies)
                    rejected+=1
                else:
                    candidate,decision=parse(task,bodies)
                    self.assertEqual(candidate,files(ROOT/check['path']))
                    self.assertEqual(hashes(candidate),check['source_sha256'])
                    self.assertFalse(decision['body_guard']['semantic_verification_performed'])
                    accepted+=1
        self.assertEqual((accepted,rejected),(34,4))

    def test_contract_scope_bypass_and_ambiguous_output_rejections(self):
        task=TASKS[0]; seed=sources(task['depth'],task['sharing'],'empty')
        attacks=['assume false;','reveal K.Merge();','assert {:axiom} false;',
                 'import K = Kernel`Internal;', 'HelperB.Prove(m,n,keep);',
                 'lemma Added() {}','while true {}','return;',
                 'assert forall m :: true;', 'var K := 0;',
                 'assert forall q :: true; assert q == 0;']
        for body in attacks:
            with self.assertRaises(ValueError,msg=body): parse(task,{'HelperA.dfy':body})
        for name in seed:
            with self.assertRaises(ValueError):
                parse(task,{'HelperA.dfy':''},{**seed,name:seed[name]+'\n'})
        for bodies in ({'ClientA.dfy':''},{'HelperA.dfy':'','HelperB.dfy':''},{'answer':{'HelperA.dfy':''}}):
            with self.assertRaises(ValueError):parse(task,bodies)
        raw=json.dumps({'HelperA.dfy':'assert true;'})
        for bad in (raw+'\n'+raw,'{"HelperA.dfy":"", "HelperA.dfy":"assert true;"}'):
            with self.assertRaises(ValueError):envelope.parse_response(bad,seed,task,guard)
        # A mathematically false assertion stays syntax-admissible, for the verifier.
        parse(task,{'HelperA.dfy':'assert forall badKey0 :: badKey0 == 0;'})

    def test_negative_mutations_have_declared_scope(self):
        for depth in ('shallow','deep'):
            ref=proof(depth,'reference')
            for side,label in [('m','left'),('n','right')]:
                text=f'O2.RestrictAt({side},keep,q);' if depth=='deep' else f'    A.ObserveRestrict({side},keep);\n'
                self.assertEqual(proof(depth,'missing_'+label+'_value'),ref.replace(text,''))
            self.assertEqual(proof(depth,'lost_domain'),ref+'    assert right.Keys == rm.Keys;\n')
        self.assertEqual(proof('deep','missing_certificate'),proof('deep','reference').replace('O1.Certify(rm,rn);',''))

    def test_isolated_verifier_fake_staging_and_diagnostic_boundaries(self):
        sys.path.insert(0,str(ROOT/'code'))
        from language.dafny import repository
        self.assertTrue(Path(repository.__file__).is_relative_to(ROOT/'code'))
        seed={n:s.encode() for n,s in sources('deep','shared','reference').items()}
        def process(command,cwd,capture_output,text):
            self.assertEqual({p.name:p.read_bytes() for p in Path(cwd).glob('*.dfy')},seed)
            self.assertIn('--verify-included-files',command)
            return types.SimpleNamespace(returncode=0,stdout='Dafny program verifier finished with 12 verified, 0 errors\n',stderr='')
        with patch.object(repository.subprocess,'run',side_effect=process) as p:
            evidence=repository.verify_repository(seed,'All.dfy',timeout=60).evidence
        self.assertEqual(p.call_count,1); self.assertEqual(evidence['model_calls'],0)
        from preflight import diagnostic, selected
        self.assertEqual(diagnostic(evidence),'success')
        for code,log,wanted in [
            (0,'','unexpected_diagnostic'),(0,'12 verified, 0 errors\nWarning: X','unexpected_diagnostic'),
            (4,'assertion might not hold','proof_failure'),(4,'postcondition could not be proved','proof_failure'),
            (2,'member ObserveMerge does not exist','resolution_failure'),(2,'1 parse errors','parse_error'),
            (4,'decreases expression might not decrease','termination_failure'),(124,'timeout','unexpected_diagnostic')]:
            self.assertEqual(diagnostic(dict(evidence,exit_code=code,stdout=log)),wanted)
        self.assertEqual((len(selected(CHECKS,'core')),len(selected(CHECKS,'negatives'))),(8,30))

    def test_only_explicit_finite_domain_changed_from_failed_parent(self):
        import hashlib
        correction=json.loads((ROOT/'source-correction.json').read_text())
        parents=json.loads((ROOT/'parent-checks.json').read_text())
        before=correction['before_kernel'];after=correction['after_kernel']
        self.assertEqual(after,before.replace('q in m || q in n','q in m.Keys + n.Keys'))
        self.assertEqual(len(parents),len(CHECKS))
        for parent,current in zip(parents,CHECKS):
            self.assertEqual({k:v for k,v in parent.items() if k!='source_sha256'},
                             {k:v for k,v in current.items() if k!='source_sha256'})
            self.assertEqual(parent['source_sha256']['Kernel.dfy'],hashlib.sha256(before.encode()).hexdigest())
            self.assertEqual(current['source_sha256']['Kernel.dfy'],hashlib.sha256(after.encode()).hexdigest())
            for n,h in current['source_sha256'].items():
                if n!='Kernel.dfy':self.assertEqual(h,parent['source_sha256'][n])
        self.assertEqual(correction['reusable_prior_verifier_outcomes'],0)

    def test_remote_code_syntax_and_optional_frozen_hashes(self):
        import hashlib
        provenance=json.loads((ROOT/'provenance.json').read_text())
        text=(ROOT/'policy/body_guard.py').read_text(); parsed=ast.parse(text)
        excluded=set()
        for node in parsed.body:
            if (isinstance(node,ast.FunctionDef) and node.name=='policy') or (
                isinstance(node,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='VERSION' for t in node.targets)):
                excluded.update(range(node.lineno,node.end_lineno+1))
        normalized=''.join(s for n,s in enumerate(text.splitlines(keepends=True),1) if n not in excluded)
        self.assertEqual(hashlib.sha256(normalized.encode()).hexdigest(),provenance['grammar_excluding_registry_and_version_sha256'])
        for name,h in provenance['unchanged_copies'].items():
            self.assertEqual(hashlib.sha256((ROOT/name).read_bytes()).hexdigest(),h,name)
        tree=ast.parse((ROOT/'ops.py').read_text())
        for node in ast.walk(tree):
            if isinstance(node,ast.Constant) and isinstance(node.value,str) and node.value.startswith('import '):
                compile(node.value.replace('REMOTE_ROOT',repr('formal-disco/outputs/development-restriction-001')),'remote-snippet','exec')
        for phase in ('core','negatives'):
            s=(ROOT/f'verify-{phase}.sbatch').read_text()
            self.assertIn('--no-requeue',s); self.assertIn('--partition=test',s)
            self.assertIn('--phase '+phase,s)
        if (ROOT/'manifest.json').exists():
            for name,h in json.loads((ROOT/'manifest.json').read_text()).items():
                self.assertEqual(hashlib.sha256((ROOT/name).read_bytes()).hexdigest(),h,name)


if __name__=='__main__': unittest.main(verbosity=2)
