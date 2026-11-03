"""Unchanged grammar regressions plus old interval-witness compatibility."""
import ast
import importlib.util
import json
from pathlib import Path
import unittest

import body_guard as guard

ROOT = Path(__file__).resolve().parent
EXPERIMENTS = ROOT.parent
V2 = EXPERIMENTS / 'reasoning-output-policy-002'
V3 = EXPERIMENTS / 'conditional-monotonicity-001/protocol'
BALANCED = EXPERIMENTS / 'monorepo-balanced-calibration-pilot-001'
WITNESS = EXPERIMENTS / 'monorepo-calibration-v2-001/remaining-families-001/revision-003'


def module(name, path):
    spec = importlib.util.spec_from_file_location(name,path)
    result = importlib.util.module_from_spec(spec);spec.loader.exec_module(result)
    return result


old_tests = module('v2_grammar_regressions', V2 / 'test_body_guard.py')
LegacyGuardTests = old_tests.LegacyGuardTests
VersionTwoTests = old_tests.VersionTwoTests
TASKS = [t for t in json.loads((BALANCED / 'frozen-001/tasks.json').read_text()) if t['task_id'].startswith('witness-')]


def files(path): return {p.name:p.read_text() for p in path.glob('*.dfy')}
def seed(task): return files(BALANCED / 'frozen-001/tasks' / task['task_id'])
def payload(task, target):
    seeds = seed(task); bodies = {}
    for name in task['editable_files']:
        prefix,suffix = guard.split_seed(seeds[name])
        if not target[name].startswith(prefix) or not target[name].endswith(suffix):
            raise ValueError('Protected boundary changed')
        bodies[name] = target[name][len(prefix):-len(suffix)]
    return json.dumps(bodies), seeds


class IntegrationTests(unittest.TestCase):
    def test_old_seven_registries_are_identical(self):
        previous = module('prior_v3_guard', V3 / 'body_guard.py')
        tasks = old_tests.legacy.TASKS + json.loads((V3.parent / 'tasks.json').read_text())
        for task in tasks:self.assertEqual(guard.policy(task),previous.policy(task))
        # Preserve legal old-task locals; protection is per task, not global renaming.
        guard.Grammar('var S1 := 0;',old_tests.legacy.TASKS[0]).sequence()

    def test_surface_grammar_and_protected_insertion_are_unchanged(self):
        def tree(path):
            t=ast.parse(path.read_text());t.body=t.body[1:]
            t.body=[n for n in t.body if not (isinstance(n,ast.FunctionDef) and n.name=='policy')
                    and not (isinstance(n,ast.Assign) and isinstance(n.targets[0],ast.Name) and n.targets[0].id=='VERSION')]
            for n in t.body:
                if isinstance(n,ast.ClassDef) and n.name=='Grammar':
                    n.body=[method for method in n.body if not (isinstance(method,ast.FunctionDef) and method.name=='declare')]
            return ast.dump(t,include_attributes=False)
        self.assertEqual(tree(ROOT/'body_guard.py'),tree(V3/'body_guard.py'))

    def test_witness_references_and_proof_negative_bodies_replay_exactly(self):
        tasks={t['task_id']:t for t in TASKS};count=0
        for check in json.loads((WITNESS/'checks.json').read_text()):
            if check['task_id'] not in tasks or check['variant'] in ('hidden_shortcut','weakened_helper_contract'):continue
            task=tasks[check['task_id']];target=files(WITNESS/check['path'])
            raw,seeds=payload(task,target)
            self.assertEqual(guard.parse_response(raw,seeds,task)[0],target);count+=1
        self.assertEqual(count,24)

    def test_eight_old_responses_retain_exact_candidate_bytes(self):
        tasks={t['task_id']:t for t in TASKS};count=0
        for trial in json.loads((BALANCED/'frozen-001/trials.json').read_text()):
            if trial['task_id'] not in tasks:continue
            task=tasks[trial['task_id']];folder=BALANCED/'model-001'/trial['trial_id']
            raw=json.loads((folder/'response.json').read_text())['text']
            self.assertEqual(guard.parse_response(raw,seed(task),task)[0],files(folder/'candidate'));count+=1
        self.assertEqual(count,8)

    def test_witness_calls_arities_and_namespaces_are_bound(self):
        for task in TASKS:
            self.assertEqual(guard.policy(task)['calls'],task['calls'])
            aliases={'End'} if task['depth']=='shallow' else {'End','S1','S2'}
            for alias in aliases:
                with self.assertRaises(ValueError):guard.Grammar('var '+alias+' := 0;',task).sequence()
                with self.assertRaises(ValueError):guard.Grammar('forall '+alias+' | true ensures true {}',task).sequence()
            for body in ['K.Witness(a,b,c,d,a);','assert K.Witness(a,b,c,d,a);',
                         'H.Prove(a,b,c,d);','Prove(a,b,c,d);', 'End.Direct(a,b,c,d);',
                         'assume false;', 'assert {:axiom} false;', 'reveal K.Overlap();']:
                with self.assertRaises(ValueError):guard.Grammar(body,task).sequence()

    def test_contract_edits_and_hidden_views_remain_rejected(self):
        tasks={t['task_id']:t for t in TASKS};counts={'hidden_shortcut':0,'weakened_helper_contract':0}
        for check in json.loads((WITNESS/'checks.json').read_text()):
            if check['task_id'] not in tasks or check['variant'] not in counts:continue
            task=tasks[check['task_id']];target=files(WITNESS/check['path'])
            if check['variant']=='weakened_helper_contract':
                with self.assertRaises(ValueError):payload(task,target)
            else:
                raw,seeds=payload(task,target)
                with self.assertRaises(ValueError):guard.parse_response(raw,seeds,task)
            counts[check['variant']]+=1
        self.assertEqual(counts,{'hidden_shortcut':2,'weakened_helper_contract':4})

    def test_monotonicity_stays_byte_exact(self):
        tasks={t['task_id']:t for t in json.loads((V3.parent/'tasks.json').read_text())};count=0
        for check in json.loads((V3.parent/'checks.json').read_text()):
            if check['variant']=='hidden_shortcut':continue
            task=tasks[check['task_id']];seeds=files(V3.parent/'fixtures'/task['task_id']/'empty');target=files(V3.parent/check['path']);bodies={}
            for name in task['editable_files']:
                prefix,suffix=guard.split_seed(seeds[name]);bodies[name]=target[name][len(prefix):-len(suffix)]
            self.assertEqual(guard.parse_response(json.dumps(bodies),seeds,task)[0],target);count+=1
        self.assertEqual(count,28)


if __name__=='__main__':unittest.main(verbosity=2)
