"""Offline acceptance, reconstruction and adversarial output-policy tests."""
import copy
import json
from pathlib import Path
import unittest
from body_guard import Grammar, parse_response, split_seed, digest, MAX_RESPONSE

ROOT=Path(__file__).resolve().parents[1]
TASKS=json.loads((ROOT/'tasks.json').read_text())
CHECKS=json.loads((ROOT/'checks.json').read_text())


def fixture(task,variant):
    return {p.name:p.read_text() for p in (ROOT/'fixtures'/task['task_id']/variant).glob('*.dfy')}


def payload(task,variant):
    seed=fixture(task,'empty'); target=fixture(task,variant); bodies={}
    for name in task['editable_files']:
        prefix,suffix=split_seed(seed[name]); source=target[name]
        assert source.startswith(prefix) and source.endswith(suffix)
        bodies[name]=source[len(prefix):-len(suffix)]
    return json.dumps(bodies),seed,target


def task_for(instance='commuting_updates',depth='deep',sharing='shared'):
    return next(t for t in TASKS if t['semantic_instance']==instance and t['depth']==depth and t['sharing']==sharing)


class BodyGuardTests(unittest.TestCase):
    def assert_rejects_body(self,body,task=None):
        task=task or task_for(); seeds=fixture(task,'empty')
        raw=json.dumps({n:body for n in task['editable_files']})
        with self.assertRaises(ValueError): parse_response(raw,seeds,task)

    def test_all_references_reconstruct_exact_bytes(self):
        for task in TASKS:
            with self.subTest(task=task['task_id']):
                raw,seed,target=payload(task,'reference')
                candidate,record=parse_response(raw,seed,task)
                self.assertEqual(candidate,target)
                self.assertEqual(record['candidate_sha256'],{n:digest(s) for n,s in target.items()})
                self.assertFalse(record['semantic_verification_performed'])
                self.assertEqual(seed,fixture(task,'empty'))

    def test_semantic_negative_bodies_are_admitted_not_silently_repaired(self):
        tasks={t['task_id']:t for t in TASKS}; count=0
        for check in CHECKS:
            if check['variant'] in ('reference','hidden_shortcut','weaken_contract'):continue
            task=tasks[check['task_id']]; raw,seed,target=payload(task,check['variant'])
            self.assertEqual(parse_response(raw,seed,task)[0],target);count+=1
        self.assertEqual(count,104)

    def test_hidden_views_and_cross_helper_delegation_are_rejected(self):
        for task in TASKS:
            if task['depth']=='deep':
                raw,seeds,_=payload(task,'hidden_shortcut')
                with self.assertRaises(ValueError):parse_response(raw,seeds,task)
            for call in ['H.Prove(m,k,j,x,y);','HelperA.Prove(m,k,j,x,y);',
                         'O1.K.Put(m,k,x);','K.Internal();','A.Equal(left);']:
                self.assert_rejects_body(call,task)

    def test_no_contract_import_provider_or_file_escape(self):
        task=task_for();raw,seeds,_=payload(task,'reference');bodies=json.loads(raw)
        for name in ['ClientA.dfy','Api.dfy','../HelperA.dfy','All.dfy']:
            altered=dict(bodies);altered[name]=''
            with self.assertRaises(ValueError):parse_response(json.dumps(altered),seeds,task)
        for body in ['}\n ensures true\n{','} }\nmodule Attack {}',
                     'include "x.dfy"','import K = Kernel`Internal',
                     'lemma L() ensures false {}','assert {:axiom} false;',
                     'assert {:verify false} false;','assume false;','reveal K.Put();',
                     'expect false;','while true {}','return;','calc { 0; == 1; }']:
            self.assert_rejects_body(body)
        changed=dict(seeds);changed['ClientA.dfy']+='\n'
        with self.assertRaises(ValueError):parse_response(raw,changed,task)

    def test_scope_and_initialization(self):
        for body in ['assert unbound == 0;', 'var v := v;', 'var k := 0;',
                     'var K := 0;', 'var if := 0;', 'var temporary := 0; temporary := 1;',
                     'if true { var z := 0; } assert z == 0;',
                     'forall q | q in m ensures q in m {} assert q == 0;',
                     'forall k | k in m ensures k in m {}',
                     'forall q | q in m ensures q in m { var q := 0; }']:
            self.assert_rejects_body(body)
        body='if true { var z := 0; assert z == 0; } else { var z := 1; assert z == 1; }'
        task=task_for();self.assertIsInstance(Grammar(body,task).sequence(),list)

    def test_equivalent_syntax_and_local_alpha_rename(self):
        task=task_for();raw,seeds,_=payload(task,'reference');bodies=json.loads(raw)
        # Rename local identifiers only. Exact output bytes must survive admission.
        import re
        body=bodies['HelperA.dfy']
        for old,new in [('u','first'),('v','second'),('left','lhs'),('right','rhs'),('q','key')]:
            body=re.sub(r'\b'+old+r'\b',new,body)
        raw=json.dumps({'HelperA.dfy':body})
        candidate,record=parse_response('```json\n'+raw+'\n```',seeds,task)
        pre,suf=split_seed(seeds['HelperA.dfy'])
        self.assertEqual(candidate['HelperA.dfy'],pre+body+suf)
        self.assertEqual(record['wrapper'],'whole-response JSON fence')
        self.assertFalse(record['semantic_verification_performed'])
        self.assertIsInstance(Grammar('var z := if k < j then k else j; assert z <= k || z <= j;',task).sequence(),list)

    def test_response_ambiguity_and_type_rejections(self):
        task=task_for();raw,seeds,_=payload(task,'reference')
        for bad in ['Here is the proof:\n'+raw,raw+'\n'+raw,
                    '{"HelperA.dfy":"","HelperA.dfy":""}',
                    '```dafny\n'+raw+'\n```','```json\n'+raw+'\n```\nextra',
                    json.dumps({'HelperA.dfy':{'body':''}}),json.dumps({'HelperA.dfy':None}),
                    json.dumps([{'HelperA.dfy':''}]),json.dumps(raw)]:
            with self.assertRaises(ValueError):parse_response(bad,seeds,task)
        for body in ['// hide\nassume false;','/* comment */','assert "text" == "text";',
                     r'assert true;\nassert false;','assert true; }',
                     'if true then {} else {}','assert if true { true } else { false };']:
            self.assert_rejects_body(body)

    def test_complexity_limits(self):
        task=task_for();seeds=fixture(task,'empty')
        with self.assertRaises(ValueError):parse_response(' '* (MAX_RESPONSE+1),seeds,task)
        for body in ['assert true; '*257,'assert '+'('*35+'true'+')'*35+';',
                     'if true {'*26+'assert true;'+'}'*26,
                     'assert 1234567890123 == 0;',' '*65537]:
            self.assert_rejects_body(body)

    def test_wrong_proofs_remain_verifier_responsibility(self):
        # No grammar success is reported as a valid proof, and no proof is repaired.
        task=task_for();seeds=fixture(task,'empty')
        for body in ['', 'assert false;', 'Prove(m,k,j,x,y);',
                     'forall q | q in m ensures false {}']:
            raw=json.dumps({'HelperA.dfy':body});candidate,record=parse_response(raw,seeds,task)
            pre,suf=split_seed(seeds['HelperA.dfy'])
            self.assertEqual(candidate['HelperA.dfy'],pre+body+suf)
            self.assertFalse(record['semantic_verification_performed'])


if __name__=='__main__':unittest.main(verbosity=2)
