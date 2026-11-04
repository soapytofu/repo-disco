"""Independent checks on the saved payloads, trial identities and reviewer boundary."""
from collections import Counter
import hashlib
import json
from pathlib import Path
import re
import unittest

HERE = Path(__file__).resolve().parent
FROZEN = HERE / 'frozen-001'
SOURCE = HERE.parent / 'conditional-monotonicity-001'


def read(path):
    return json.loads(path.read_bytes())


class FrozenPlanTests(unittest.TestCase):
    def test_trial_identity_and_replicates(self):
        trials = read(FROZEN / 'trials.json')
        self.assertEqual([r['trial_id'] for r in trials], [f'monotone-{n:02d}' for n in range(1, 9)])
        self.assertEqual([r['sample'] for r in trials], [1] * 4 + [2] * 4)
        self.assertEqual(sorted(Counter(r['request_sha256'] for r in trials).values()), [2] * 4)
        for t in trials:
            request_file = FROZEN / t['request_path']
            self.assertEqual(request_file.stem, t['task_id'].removeprefix('clamp_monotone-'))
            self.assertEqual(hashlib.sha256(request_file.read_bytes()).hexdigest(), t['request_sha256'])
        for first, second in zip(trials[:4], trials[4:]):
            _, depth, sharing = first['task_id'].split('-')
            _, other_depth, other_sharing = second['task_id'].split('-')
            self.assertNotEqual(depth, other_depth)
            self.assertNotEqual(sharing, other_sharing)

    def test_model_context_and_edit_boundary(self):
        settings = read(HERE / 'plan.json')
        for task in read(SOURCE / 'tasks.json'):
            with self.subTest(cell=task['task_id']):
                cell = task['depth'] + '-' + task['sharing']
                request = read(FROZEN / 'requests' / (cell + '.json'))
                self.assertEqual(set(request), {'modelId', 'inferenceConfig', 'system', 'messages'})
                self.assertEqual(request['modelId'], settings['model_id'])
                self.assertEqual(request['inferenceConfig'], settings['inference_config'])
                self.assertEqual(len(request['messages']), 1)
                message, = request['messages']
                self.assertEqual(message['role'], 'user')
                content, = message['content']
                self.assertEqual(set(content), {'text'})
                prompt = content['text']
                sources = re.findall(r'^FILE (\w+\.dfy)\n```dafny\n(.*?)^```$', prompt, re.M | re.S)
                self.assertEqual(len(sources), 9)
                self.assertEqual({n:hashlib.sha256(s.encode()).hexdigest() for n,s in sources}, task['source_sha256'])
                shape = re.search(r'^Required response keys and shape: (.+)$', prompt, re.M)
                self.assertEqual(json.loads(shape[1]), dict.fromkeys(task['editable_files'], ''))
                folder = SOURCE / 'fixtures' / task['task_id']
                for file in task['editable_files']:
                    target = (folder / 'reference' / file).read_text()
                    seed = (folder / 'empty' / file).read_text()
                    prefix, suffix = seed.rsplit('  {\n  }\n}\n', 1)
                    self.assertEqual(suffix, '')
                    proof = target.removeprefix(prefix + '  {').removesuffix('  }\n}\n').strip()
                    self.assertGreater(len(proof), 30)
                    self.assertNotIn(proof, prompt)
                for reviewer_text in ('57180678', 'two contract-application stages', 'wrong_region',
                                      'verification-001', 'monotone-01', '32/32'):
                    self.assertNotIn(reviewer_text, prompt)


if __name__ == '__main__':
    unittest.main(verbosity=2)
