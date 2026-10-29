"""Offline scope checks; no provider or verifier invocation."""
import collections
import tempfile
import unittest
from pathlib import Path
import prepare_scope as prep

ROOT=prep.ROOT/'frozen-001'


class ScopeTests(unittest.TestCase):
    def test_frozen_inputs_and_reproducibility(self):
        prep.validate_bundle(prep.PARENT);prep.validate_bundle(ROOT)
        with tempfile.TemporaryDirectory() as temp:
            other=prep.prepare(Path(temp)/'bundle')
            self.assertEqual(prep.load(other/'freeze.json'),prep.load(ROOT/'freeze.json'))
            (other/'system.txt').write_text('drift')
            with self.assertRaises(ValueError):prep.validate_bundle(other)

    def test_exact_eight_balanced_structural_selections(self):
        trials=prep.load(ROOT/'trials.json');tasks=prep.load(ROOT/'tasks.json')
        self.assertEqual([t['task_id'] for t in trials],prep.ORDER)
        self.assertEqual(len(set(t['task_id'] for t in trials)),8)
        self.assertEqual(len(set(t['trial_id'] for t in trials)),8)
        self.assertEqual(set(t['depth'] for t in tasks),{'deep'})
        groups=collections.defaultdict(list)
        for i,t in enumerate(tasks):groups[t['family']].append((i,t['sharing']))
        self.assertEqual(len(groups),4)
        first=[]
        for pair in groups.values():
            self.assertEqual({x[1] for x in pair},{'shared','separate'})
            self.assertEqual(pair[1][0]-pair[0][0],4)
            first.append(pair[0][1])
        self.assertEqual(collections.Counter(first),{'shared':2,'separate':2})

    def test_unchanged_prompts_guards_sources_and_settings(self):
        for task in prep.load(ROOT/'tasks.json'):
            source=prep.PARENT/'tasks'/task['task_id'];dest=ROOT/'tasks'/task['task_id']
            self.assertEqual({p.name:p.read_bytes() for p in source.iterdir()},
                             {p.name:p.read_bytes() for p in dest.iterdir()})
        for name in ['system.txt','guard/grammar.py','guard/body_protocol.py']:
            self.assertEqual((ROOT/name).read_bytes(),(prep.PARENT/name).read_bytes())
        a=prep.load(ROOT/'settings.json');b=prep.load(prep.PARENT/'settings.json')
        for key in ['max_calls','independent_samples_per_variant','status']:
            a.pop(key);b.pop(key)
        self.assertEqual(a,b)
        parent_gate=prep.load(prep.PARENT/'preflight-gate.json')
        self.assertEqual(prep.load(ROOT/'preflight-gate.json'),[g for g in parent_gate if g['task_id'] in prep.ORDER])

    def test_trial_bindings_and_no_budget_inference(self):
        scope=prep.load(ROOT/'scope.json');settings=prep.load(ROOT/'settings.json')
        self.assertEqual(scope['proposed_max_new_calls'],8)
        self.assertEqual(settings['max_calls'],8)
        self.assertEqual(scope['status'],'PROPOSED_NOT_AUTHORIZED')
        self.assertEqual(scope['model_calls_made'],0)
        self.assertEqual(scope['maximum_output_tokens'],32768)
        self.assertFalse(scope['automatic_retries']);self.assertFalse(scope['reassign_unused'])
        self.assertEqual(scope['sdk_total_max_attempts'],1)
        for t in prep.load(ROOT/'trials.json'):
            self.assertEqual(t['prompt_sha256'],prep.sha(ROOT/t['prompt_path']))
            self.assertEqual(t['system_sha256'],prep.sha(ROOT/t['system_path']))
            self.assertEqual(t['sample'],1);self.assertTrue(t['fresh_context']);self.assertFalse(t['feedback'])
        for absent in ['authorization.json','model-001','submission.json']:
            self.assertFalse((prep.ROOT/absent).exists())


if __name__=='__main__':unittest.main(verbosity=2)
