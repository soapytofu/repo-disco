"""Offline proposal acceptance tests: no transport, SDK or verifier process."""
from collections import Counter
import copy
import json
from pathlib import Path
import re
import shutil
import tempfile
import unittest

import prepare as p


class PlanTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp=tempfile.TemporaryDirectory(prefix='repodisco-reasoning-freeze-')
        cls.bundle=p.prepare(Path(cls.temp.name)/'bundle')
        cls.tasks=p.load(cls.bundle/'tasks.json')
        cls.trials=p.load(cls.bundle/'trials.json')
        cls.parser=p.guard(cls.bundle/'guard/body_guard.py')
        cls.lookup={t['task_id']:t for t in cls.tasks}

    @classmethod
    def tearDownClass(cls):
        print('Deterministic proposed freeze SHA-256: '+p.sha(cls.bundle/'freeze.json'))
        cls.temp.cleanup()

    def seed(self,task):return p.files(self.bundle/'tasks'/task['task_id'])

    def test_budget_and_inference_are_explicit_not_authorized(self):
        settings=p.load(self.bundle/'settings.json');scope=p.load(self.bundle/'scope.json')
        previous=p.load(p.PREVIOUS_SETTINGS)
        for k in ('model_id','region','inference_config'):self.assertEqual(settings[k],previous[k])
        self.assertEqual(settings['max_calls'],24)
        self.assertEqual(settings['max_output_tokens_total'],98304)
        self.assertEqual(settings['attempts_per_trial'],1)
        self.assertEqual(settings['sdk_total_max_attempts'],1)
        self.assertFalse(settings['automatic_retries'])
        self.assertFalse(settings['reassign_unused'])
        self.assertEqual(scope['status'],'FROZEN_PROPOSAL_NO_MODEL_AUTHORIZATION')
        self.assertEqual(scope['model_calls_made'],0)
        self.assertEqual(scope['new_dafny_runs'],0)
        self.assertEqual(scope['proposed_max_new_calls'],24)
        self.assertFalse(scope['pooling_prior_model_samples'])
        names=p.inventory(self.bundle)
        self.assertFalse(any(Path(n).name in ('authorization.json','run_pilot.py','model.sbatch') for n in names))

    def test_order_covers_every_variant_once(self):
        trials=self.trials
        self.assertEqual(len(trials),24)
        self.assertEqual({r['task_id'] for r in trials},set(self.lookup))
        self.assertEqual([r['position'] for r in trials],list(range(1,25)))
        self.assertEqual(len({r['trial_id'] for r in trials}),24)
        self.assertEqual(Counter(r['cell'] for r in trials),dict.fromkeys(p.CELLS,6))
        self.assertEqual(Counter(r['family'] for r in trials),dict(conditional=8,sequence=8,map=8))
        self.assertEqual(Counter(r['semantic_instance'] for r in trials),dict.fromkeys(p.INSTANCES,4))
        self.assertTrue(all(r['fresh_context'] and not r['feedback'] and r['sample']==1 for r in trials))
        for family in ('conditional','sequence','map'):
            for cell in p.CELLS:
                self.assertEqual(len({r['semantic_instance'] for r in trials if r['family']==family and r['cell']==cell}),2)

    def test_counterbalance_claims_match_actual_order(self):
        sequences={name:[r for r in self.trials if r['semantic_instance']==name] for name in p.INSTANCES}
        self.assertEqual(Counter(rows[0]['depth'] for rows in sequences.values()),dict(shallow=3,deep=3))
        self.assertEqual(Counter(rows[0]['sharing'] for rows in sequences.values()),dict(shared=3,separate=3))
        for depth in ('shallow','deep'):
            shared_first=0
            for rows in sequences.values():
                pair=[r['sharing'] for r in rows if r['depth']==depth]
                shared_first+=pair[0]=='shared'
            self.assertEqual(shared_first,3)
        for wave in range(1,5):
            rows=[r for r in self.trials if r['wave']==wave]
            self.assertEqual({r['semantic_instance'] for r in rows},set(p.INSTANCES))
            self.assertEqual(sorted(Counter(r['cell'] for r in rows).values()),[1,1,2,2])

    def test_pinned_evidence_covers_all_controls_without_new_runs(self):
        report=p.load(self.bundle/'evidence-review.json')
        self.assertEqual(report['selected_controls'],dict(success=24,proof_failure=120,termination_failure=8,resolution_failure=12))
        self.assertEqual(report['reference_replays'],24)
        self.assertEqual(report['new_model_calls'],0);self.assertEqual(report['new_dafny_runs'],0)
        self.assertEqual(len(report['controls']),164)
        self.assertEqual(len({(r['task_id'],r['variant']) for r in report['controls']}),164)
        self.assertEqual(sum(r['reused_identical_prior_result'] for r in report['controls']),44)
        for row in report['controls']:
            self.assertEqual(p.sha(p.REPO/row['log_path']),row['log_sha256'])
        self.assertEqual(p.sha(self.bundle/'guard/body_guard.py'),p.GUARD_SHA)
        self.assertEqual(p.inventory(self.bundle/'verifier'),p.inventory(p.SOURCE/'code'))

    def test_provider_client_matching_and_edit_counts(self):
        fixed={'Kernel.dfy','Ops1.dfy','Ops2.dfy','Api.dfy','ClientA.dfy','ClientB.dfy','All.dfy'}
        for instance in p.INSTANCES:
            group=[t for t in self.tasks if t['semantic_instance']==instance]
            self.assertEqual(len(group),4)
            baseline=self.seed(group[0])
            for task in group:
                seeds=self.seed(task)
                self.assertEqual(len(seeds),9)
                self.assertEqual({n:p.digest(s) for n,s in seeds.items()},task['source_sha256'])
                self.assertEqual({n:seeds[n] for n in fixed},{n:baseline[n] for n in fixed})
                self.assertEqual(task['editable_files'],['HelperA.dfy'] if task['sharing']=='shared' else ['HelperA.dfy','HelperB.dfy'])
                for name in task['editable_files']:
                    prefix,suffix=self.parser.split_seed(seeds[name])
                    self.assertEqual(seeds[name],prefix+'\n'+suffix)

    def test_all_current_reference_bodies_reconstruct_exactly(self):
        for task in self.tasks:
            seeds=self.seed(task);before=copy.deepcopy(seeds)
            reference=p.files(p.SOURCE/'fixtures'/task['task_id']/'reference')
            payload=p.body_payload(self.parser,task,seeds,reference)
            candidate,decision=self.parser.parse_response(json.dumps(payload),seeds,task)
            self.assertEqual(candidate,reference)
            self.assertEqual(seeds,before)
            self.assertFalse(decision['semantic_verification_performed'])
            self.assertEqual(decision['candidate_sha256'],{n:p.digest(s) for n,s in reference.items()})

    def test_semantic_negatives_are_not_repaired_by_extraction(self):
        count=0
        for check in p.load(p.SOURCE/'checks.json'):
            if check['variant'] in ('reference','hidden_shortcut','weaken_contract'):continue
            task=self.lookup[check['task_id']];seeds=self.seed(task)
            target=p.files(p.SOURCE/check['path'])
            payload=p.body_payload(self.parser,task,seeds,target)
            candidate,decision=self.parser.parse_response(json.dumps(payload),seeds,task)
            self.assertEqual(candidate,target)
            self.assertFalse(decision['semantic_verification_performed']);count+=1
        self.assertEqual(count,104)

    def test_prompt_inputs_are_exact_empty_seeds_and_public_maps(self):
        settings=p.load(self.bundle/'settings.json')
        for trial in self.trials:
            task=self.lookup[trial['task_id']];seeds=self.seed(task)
            folder=self.bundle/'tasks'/task['task_id']
            user=(folder/'prompt.txt').read_text();request=p.load(self.bundle/trial['request_path'])
            self.assertEqual(user,p.prompt(task,seeds,self.parser))
            self.assertEqual(request,dict(modelId=settings['model_id'],system=[dict(text=p.SYSTEM)],
                messages=[dict(role='user',content=[dict(text=user)])],inferenceConfig=settings['inference_config']))
            self.assertEqual(p.sha(self.bundle/trial['request_path']),trial['request_sha256'])
            blocks=dict(re.findall(r'FILE ([A-Za-z0-9]+\.dfy)\n```dafny\n(.*?)```',user,re.S))
            self.assertEqual(blocks,seeds)
            self.assertEqual(p.load(folder/'declared-map.json'),p.source_map(seeds))
            for private in ('reference_operation_fact_depth','completion-review.json','verification-001',
                            'expected_diagnostic','reviewer_only_workloads','reasoning-cal-'):
                self.assertNotIn(private,json.dumps(request))
            self.assertNotIn('reference',p.inventory(folder))

    def test_explained_syntax_admits_and_common_mistakes_reject(self):
        for task in self.tasks:
            seeds=self.seed(task)
            for example in p.SYNTAX_EXAMPLES:
                raw=json.dumps({n:example for n in task['editable_files']})
                candidate,decision=self.parser.parse_response(raw,seeds,task)
                self.assertFalse(decision['semantic_verification_performed'])
                for name in task['editable_files']:
                    pre,suf=self.parser.split_seed(seeds[name])
                    self.assertEqual(candidate[name],pre+example+suf)
            for body in ['if true then assert true; else assert true;',
                         'var tmp: int := 0;', 'assume false;',
                         'forall key | key == 0 ensures key == 0 {} assert key == 0;',
                         'assert true; // comment',r'assert true;\nassert true;']:
                with self.assertRaises(ValueError):
                    self.parser.parse_response(json.dumps({n:body for n in task['editable_files']}),seeds,task)

    def test_schema_scope_and_contract_edits_are_rejected(self):
        for task in self.tasks:
            seeds=self.seed(task);raw=json.dumps({n:'assert true;' for n in task['editable_files']})
            for bad in ['Explanation\n'+raw,raw+raw,'{"HelperA.dfy":"","HelperA.dfy":""}',
                        json.dumps({'ClientA.dfy':''}),json.dumps({n:{} for n in task['editable_files']})]:
                with self.assertRaises(ValueError):self.parser.parse_response(bad,seeds,task)
            altered=dict(seeds);altered['HelperA.dfy']=altered['HelperA.dfy'].replace('ensures','requires',1)
            with self.assertRaises(ValueError):self.parser.parse_response(raw,altered,task)
            altered=dict(seeds);altered['Kernel.dfy']+='\n'
            with self.assertRaises(ValueError):self.parser.parse_response(raw,altered,task)
            if task['depth']=='deep':
                target=p.files(p.SOURCE/'fixtures'/task['task_id']/'hidden_shortcut')
                payload=p.body_payload(self.parser,task,seeds,target)
                with self.assertRaises(ValueError):self.parser.parse_response(json.dumps(payload),seeds,task)

    def test_inventory_detects_extra_missing_modified_files(self):
        p.validate_bundle(self.bundle)
        with tempfile.TemporaryDirectory(prefix='repodisco-freeze-tamper-') as temp:
            clone=Path(temp)/'clone';shutil.copytree(self.bundle,clone)
            f=clone/'trials.json';original=f.read_bytes()
            f.write_bytes(original+b'\n')
            with self.assertRaises(ValueError):p.validate_bundle(clone)
            f.write_bytes(original);extra=clone/'unlisted.txt';extra.write_text('extra')
            with self.assertRaises(ValueError):p.validate_bundle(clone)
            extra.unlink();f.unlink()
            with self.assertRaises(ValueError):p.validate_bundle(clone)

    def test_deterministic_regeneration_and_no_overwrite(self):
        with tempfile.TemporaryDirectory(prefix='repodisco-freeze-replay-') as temp:
            reproduced=p.prepare(Path(temp)/'reproduced')
            self.assertEqual(p.inventory(reproduced),p.inventory(self.bundle))
            with self.assertRaises(ValueError):p.prepare(reproduced)
            self.assertEqual(p.inventory(reproduced),p.inventory(self.bundle))


if __name__=='__main__':unittest.main(verbosity=2)
