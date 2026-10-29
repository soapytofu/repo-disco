"""Offline prompt/parser regression. Never invokes a provider or Dafny."""
import collections
import importlib.util
import json
import sys
import tempfile
import unittest
from pathlib import Path

import prepare_prompts as prep

ROOT = prep.ROOT
BUNDLE = ROOT / 'frozen-001'
PILOT = ROOT.parent / 'monorepo-calibration-v2-pilot-001'


def module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    obj = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(obj)
    return obj


def parser(root):
    grammar = module('syntax_test_grammar', root / 'guard/grammar.py')
    previous = sys.modules.get('grammar')
    sys.modules['grammar'] = grammar
    try:
        body = module('syntax_test_body', root / 'guard/body_protocol.py')
    finally:
        if previous is None:
            del sys.modules['grammar']
        else:
            sys.modules['grammar'] = previous
    return grammar, body


def sources(task, root=BUNDLE):
    return {p.name:p.read_text() for p in (root/'tasks'/task['task_id']).glob('*.dfy')}


class SyntaxTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tasks = prep.load(BUNDLE/'tasks.json')
        cls.grammar, cls.body = parser(BUNDLE)
        cls.old_grammar, cls.old_body = parser(prep.PARENT)
        cls.evidence = dict(model_calls=0, new_dafny_runs=0, parser_changed=False,
                            frozen_sha256=prep.sha(BUNDLE/'freeze.json'))

    def payload(self, task, body):
        return json.dumps({name:body for name in task['editable_files']})

    def test_bundle_and_reproducible_preparation(self):
        prep.check_bundle(prep.PARENT)
        prep.check_bundle(BUNDLE)
        with tempfile.TemporaryDirectory() as temp:
            duplicate = prep.prepare(Path(temp)/'bundle')
            self.assertEqual(prep.load(duplicate/'freeze.json'), prep.load(BUNDLE/'freeze.json'))
        for name in ['grammar.py','body_protocol.py']:
            self.assertEqual((BUNDLE/'guard'/name).read_bytes(), (prep.PARENT/'guard'/name).read_bytes())

    def test_only_instruction_and_hash_changes(self):
        old = prep.load(prep.PARENT/'tasks.json')
        self.assertEqual(len(self.tasks),16)
        for task, parent in zip(self.tasks,old):
            self.assertEqual({k:v for k,v in task.items() if k not in ['prompt_sha256','prompt_utf8_bytes']},
                             {k:v for k,v in parent.items() if k not in ['prompt_sha256','prompt_utf8_bytes']})
            self.assertEqual(sources(task),sources(parent,prep.PARENT))
            p=(BUNDLE/'tasks'/task['task_id']/'prompt.txt').read_text()
            before=(prep.PARENT/'tasks'/task['task_id']/'prompt.txt').read_text()
            self.assertEqual(p,prep.revised_prompt(before,task))
            self.assertEqual(p.split('Declared file map:',1)[1],before.split('Declared file map:',1)[1])
            self.assertIn('Do NOT put `then`',p)
            self.assertIn('not a solution',p)
            self.assertEqual(prep.digest(p),task['prompt_sha256'])
        a=prep.load(BUNDLE/'settings.json');b=prep.load(prep.PARENT/'settings.json')
        self.assertEqual(a.pop('prompt_revision'),prep.VERSION)
        self.assertEqual(a,b)
        self.assertEqual(a['model_calls_made'],0)
        self.assertEqual(a['status'],'FROZEN_PROPOSAL_NO_MODEL_AUTHORIZATION')
        for name in ['preflight-gate.json','order-design.json']:
            self.assertEqual((BUNDLE/name).read_bytes(),(prep.PARENT/name).read_bytes())

    def test_original_counterbalance_and_prompt_binding(self):
        trials=prep.load(BUNDLE/'trials.json');old=prep.load(prep.PARENT/'trials.json')
        self.assertEqual(len(trials),32)
        lookup={t['task_id']:t for t in self.tasks}
        for a,b in zip(trials,old):
            omit=['prompt_sha256','system_sha256']
            self.assertEqual({k:v for k,v in a.items() if k not in omit},{k:v for k,v in b.items() if k not in omit})
            self.assertEqual(a['prompt_sha256'],lookup[a['task_id']]['prompt_sha256'])
            self.assertEqual(a['system_sha256'],prep.sha(BUNDLE/'system.txt'))
        self.assertEqual(set(collections.Counter(t['task_id'] for t in trials).values()),{2})

    def test_neutral_examples_and_statement_forms(self):
        count=0
        for task in self.tasks:
            seed=sources(task)
            call,arity=next(iter(task['calls'].items()))
            statement=call+'('+', '.join(['0']*arity)+');'
            # Synthetic syntax exercises; not semantic proofs for these tasks.
            bodies=[prep.EXAMPLE_BODY, 'if true { '+statement+' } else { '+statement+' }',
                    'if true { assert true; } else if false { assert false; } else { assert true; }',
                    'if true { if false { assert false; } }',
                    'assert (if true then 1 else 0) == 1;', '', 'assert true;']
            for body in bodies:
                raw=self.payload(task,body)
                new,decision=self.body.parse_response(raw,seed,task)
                previous=self.old_body.parse_response(raw,seed,task)
                self.assertEqual((new,decision),previous)
                for n in seed:
                    if n not in task['editable_files']:self.assertEqual(new[n],seed[n])
                    else:
                        pre,suf=self.grammar.split_seed(seed[n]);self.assertEqual(new[n],pre+body+suf)
                count+=1
            fence='```json\n'+self.payload(task,prep.EXAMPLE_BODY)+'\n```'
            self.body.parse_response(fence,seed,task)
        self.evidence['positive_syntax_cases']=count
        self.evidence['fenced_examples']=16

    def test_reject_statement_expression_confusion(self):
        count=0
        for task in self.tasks:
            call,arity=next(iter(task['calls'].items()))
            c=call+'('+', '.join(['0']*arity)+')'
            bodies=['if true then '+c+'; else '+c+';',
                    'if true '+c+'; else '+c+';', 'if true { '+c+' }',
                    'if true { assert true }', 'if true { assert true; } else assert true;',
                    '{ assert true; }', 'assert true; trailing',
                    'assert (if true then '+c+' else 0) == 0;']
            for bad in bodies:
                with self.subTest(task=task['task_id'],body=bad):
                    with self.assertRaises(ValueError):self.body.parse_response(self.payload(task,bad),sources(task),task)
                count+=1
        self.evidence['negative_statement_syntax_cases']=count

    def test_schema_encoding_and_bypasses(self):
        count=0
        for task in self.tasks:
            seed=sources(task);payload=self.payload(task,'assert true;');key=task['editable_files'][0]
            bad_bodies=['assume false;','reveal K.Safe();','assert {:axiom} false;',
                        '} lemma Bad() ensures false {} {','var x := 0;',
                        'H.Prove();','while true {}','assert true; // comment',
                        'assert true;\\nassert true;','assert true; /* comment */']
            invalid=[self.payload(task,b) for b in bad_bodies]
            invalid += ['Prose\n'+payload,payload+'\nProse',json.dumps({'files':json.loads(payload)}),
                        json.dumps(payload),json.dumps([]),json.dumps({key:None}),
                        json.dumps({**json.loads(payload),'extra.dfy':''}),
                        '{'+json.dumps(key)+':"",'+json.dumps(key)+':""}',
                        '```dafny\n'+payload+'\n```','```json\n'+payload+'\n```\n```']
            for raw in invalid:
                with self.subTest(task=task['task_id'],raw=raw):
                    with self.assertRaises(ValueError):self.body.parse_response(raw,seed,task)
                count+=1
        self.evidence['negative_schema_or_bypass_cases']=count

    def test_resource_bounds_and_seed_integrity(self):
        task=self.tasks[0];seed=sources(task)
        bodies=[' '*65537,'assert true;'*257,'if true {'*26+'}'*26,
                'assert '+'('*40+'true'+')'*40+';']
        for body in bodies:
            with self.assertRaises(ValueError):self.body.parse_response(self.payload(task,body),seed,task)
        with self.assertRaises(ValueError):self.body.parse_response(' '*262145,seed,task)
        changed=dict(seed);changed['All.dfy']+='\n'
        with self.assertRaisesRegex(ValueError,'Seed hash'):self.body.parse_response(self.payload(task,''),changed,task)

    def test_exact_replay_of_verified_references(self):
        rows=[]
        for task in self.tasks:
            seed=sources(task)
            folder=prep.PARENT.parent/task['fixture_root']/'fixtures'/task['task_id']/'reference'
            reference={p.name:p.read_text() for p in folder.glob('*.dfy')}
            self.assertEqual(set(seed),set(reference))
            bodies={}
            for name in task['editable_files']:
                pre,suf=self.grammar.split_seed(seed[name])
                self.assertTrue(reference[name].startswith(pre) and reference[name].endswith(suf))
                bodies[name]=reference[name][len(pre):-len(suf)]
            candidate,_=self.body.parse_response(json.dumps(bodies),seed,task)
            self.assertEqual(candidate,reference)
            gate=next(g for g in prep.load(BUNDLE/'preflight-gate.json') if g['task_id']==task['task_id'])
            evidence=next(e for e in gate['evidence'] if e['variant']=='reference')
            self.assertEqual({n:prep.digest(s) for n,s in reference.items()},evidence['source_sha256'])
            log=ROOT.parent.parent/evidence['log_path']
            self.assertEqual(prep.sha(log),evidence['log_sha256'])
            verification=prep.load(log)
            self.assertEqual(verification['exit_code'],0)
            self.assertEqual(verification['source_sha256'],evidence['source_sha256'])
            rows.append(dict(task_id=task['task_id'],reference_hashes=evidence['source_sha256'],
                             prior_verifier_log=evidence['log_path'],prior_verifier_sha256=evidence['log_sha256']))
        self.evidence['previously_verified_reference_replays']=rows

    def test_historical_responses_unchanged(self):
        inventory=prep.load(PILOT/'model-001-sha256.json')
        self.assertEqual(set(inventory),{str(p.relative_to(PILOT/'model-001')) for p in (PILOT/'model-001').rglob('*') if p.is_file()})
        for name,expected in inventory.items():self.assertEqual(prep.sha(PILOT/'model-001'/name),expected)
        rows=[];accepted=0
        for trial in prep.load(PILOT/'results-review.json')['trials']:
            path=PILOT/'model-001'/trial['trial_id'];task=prep.load(path/'task.json')
            raw=prep.load(path/'response.json')['text'];seed=sources(task)
            outcomes=[]
            for parser_ in [self.old_body,self.body]:
                try:
                    candidate,decision=parser_.parse_response(raw,seed,task)
                    outcomes.append(('accepted',candidate,decision))
                except ValueError as error:outcomes.append(('rejected',str(error)))
            self.assertEqual(outcomes[0],outcomes[1])
            if trial['outcome']=='VERIFIED':
                accepted+=1;self.assertEqual(outcomes[0][0],'accepted')
                saved={p.name:p.read_text() for p in (path/'candidate').glob('*.dfy')}
                self.assertEqual(outcomes[0][1],saved)
            else:self.assertEqual(outcomes[0],('rejected','Unexpected proof token'))
            rows.append(dict(trial_id=trial['trial_id'],response_sha256=prep.sha(path/'response.json'),
                             unchanged_outcome=outcomes[0][0]))
        self.assertEqual(accepted,1)
        self.evidence['historical_response_replays']=rows
        self.evidence['historical_strict_score']='1/32 unchanged; no new verification or repair'


if __name__=='__main__':
    result=unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(SyntaxTests))
    if result.wasSuccessful():
        prep.save(ROOT/'validation.json',dict(SyntaxTests.evidence,test_methods=result.testsRun,all_passed=True))
    sys.exit(not result.wasSuccessful())
