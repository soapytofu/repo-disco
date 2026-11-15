"""Prospective policy through the unchanged fixed handler's decode/preparation.

Temporary input bundles only: no admission, provider, budget dispatch, verifier,
Slurm, credentials or promotion. This is not a full future-batch preflight.
"""
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
import copy
import hashlib
import importlib.util
import json
import re
import shutil
import sys
import tempfile
import unittest

import body_guard as guard
import test_protocol as fixtures

ROOT = Path(__file__).resolve().parent
REPO = ROOT.parents[2]
RUNTIME = REPO / 'experiments/research-window-20261114/execution-runtime'
POLICY_INPUTS = ('body_guard.py', 'syntax_guard.py', 'registry.json', 'extract_response.py', 'repair_protocol.py')


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def save(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2) + '\n')


def forbidden(*args, **kwargs):
    raise AssertionError('External action is outside this offline compatibility test')


class RuntimeCompatibilityTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        pins = json.loads((RUNTIME / 'runtime-freeze.json').read_text())['runtime_sha256']
        for name in ('run_batch.py', 'repair_protocol.py', 'bounded_requests.py'):
            if sha(RUNTIME / name) != pins[name]:
                raise ValueError('Pinned live runtime changed')
        if sha(RUNTIME / 'repair_protocol.py') != sha(ROOT / 'repair_protocol.py'):
            raise ValueError('Adapter ABI copy differs from fixed live runtime')
        sys.path.insert(0, str(RUNTIME))
        spec = importlib.util.spec_from_file_location('fixed_handler_policy_audit', RUNTIME / 'run_batch.py')
        cls.batch = importlib.util.module_from_spec(spec)
        previous_adapter = sys.modules.pop('repair_protocol', None)
        try:
            spec.loader.exec_module(cls.batch)
        finally:
            if previous_adapter is not None:
                sys.modules['repair_protocol'] = previous_adapter
            else:
                sys.modules.pop('repair_protocol', None)
        if Path(cls.batch.repair_protocol.__file__).resolve() != RUNTIME / 'repair_protocol.py':
            raise ValueError('Compatibility test did not import the fixed runtime adapter')
        cls.rows = fixtures.records()

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.bundle = Path(self.temp.name)
        self.frozen = self.bundle / 'frozen-001'
        (self.frozen / 'policy').mkdir(parents=True)
        for name in POLICY_INPUTS:
            shutil.copy2(ROOT / name, self.frozen / 'policy' / name)
        self.parents = {}
        for row in self.rows:
            task = row['task']
            task_id = task['task_id']
            if task_id in self.parents:
                continue
            base_path = f'parents/{task_id}/base'
            template_path = f'parents/{task_id}/template'
            for relative, sources in ((base_path, row['base']), (template_path, row['template'])):
                folder = self.frozen / relative
                folder.mkdir(parents=True)
                for name, source in sources.items():
                    (folder / name).write_bytes(source.encode())
            task_path = f'parents/{task_id}/task.json'
            save(self.frozen / task_path, task)
            self.parents[task_id] = dict(task_path=task_path, base_path=base_path,
                template_path=template_path, source_sha256=guard.hashes(row['base']))
        save(self.frozen / 'parents.json', self.parents)
        for name in ('bedrock_transport', 'consume_key', 'verify_logged', 'RequestGate'):
            patcher = patch.object(self.batch, name, side_effect=forbidden)
            patcher.start()
            self.addCleanup(patcher.stop)

    def test_all_four_tasks_decode_and_prepare_exact_controls(self):
        admitted = hidden = 0
        for row in self.rows:
            task = row['task']
            trial = {'parent_id': task['task_id']}
            with self.subTest(case=row['case']['case_id']):
                if row['case']['expected'] == 'resolution_failure':
                    with self.assertRaises(self.batch.OutputRejected) as raised:
                        self.batch.decode(fixtures.payload(row), self.bundle, trial)
                    self.assertEqual(raised.exception.stage, 'body_guard')
                    hidden += 1
                    continue
                candidate, decision = self.batch.decode(fixtures.payload(row), self.bundle, trial)
                expected = {name: source.encode() for name, source in row['candidate'].items()}
                base = {name: source.encode() for name, source in row['base'].items()}
                self.assertEqual(candidate, expected)
                prepared = self.batch.prepared(SimpleNamespace(files=base), candidate, task)
                self.assertEqual(dict(prepared.files), expected)
                self.assertEqual(dict(prepared.base_hashes), guard.hashes(row['base']))
                self.assertEqual(dict(prepared.candidate_hashes), guard.hashes(row['candidate']))
                self.assertLessEqual(set(prepared.changed_files), set(guard.EDITABLE_FILES))
                for name in base:
                    if name not in guard.EDITABLE_FILES:
                        self.assertEqual(candidate[name], base[name])
                self.assertEqual(decision['original_guard_decision']['body_guard']['policy_id'], guard.POLICY_ID)
                admitted += 1
        self.assertEqual((admitted, hidden), (41, 4))

    def test_fixed_handler_preserves_envelope_categories_and_parent_protection(self):
        row = next(row for row in self.rows if row['case']['variant'] == 'reference')
        trial = {'parent_id': row['task']['task_id']}
        raw = 'Here are the bodies.\n```json\n' + fixtures.payload(row) + '\n```\n'
        actual, _ = self.batch.decode(raw, self.bundle, trial)
        self.assertEqual(actual, {name: source.encode() for name, source in row['candidate'].items()})
        for invalid in ('Explanation ' + fixtures.payload(row), raw + fixtures.payload(row),
                        '{"HelperA.dfy":"", "HelperA.dfy":"", "HelperB.dfy":""}'):
            with self.assertRaises(self.batch.OutputRejected) as raised:
                self.batch.decode(invalid, self.bundle, trial)
            self.assertEqual(raised.exception.stage, 'envelope')
        modified = copy.deepcopy(self.parents)
        parent = modified[trial['parent_id']]
        source_path = self.frozen / parent['base_path'] / 'HelperA.dfy'
        source_path.write_bytes(source_path.read_bytes().replace(b'requires ', b'requires true || ', 1))
        parent['source_sha256']['HelperA.dfy'] = sha(source_path)
        save(self.frozen / 'parents.json', modified)
        with self.assertRaises(self.batch.OutputRejected) as raised:
            self.batch.decode(raw, self.bundle, trial)
        self.assertEqual(raised.exception.stage, 'body_guard')

    def test_policy_metadata_is_neutral_but_full_task_records_must_not_be_prompted(self):
        entries = guard.registry()
        disallowed = re.compile(r'\b(faulty|incorrect|broken|seeded_fault|wrong|negative_control)\b', re.I)
        seen = set()
        risky_metadata_present = False
        for row in self.rows:
            task = row['task']
            if task['task_id'] in seen:
                continue
            seen.add(task['task_id'])
            for name, source in row['base'].items():
                self.assertIsNone(disallowed.search(source), name)
            rules = entries[task['task_id']]['file_rules']
            self.assertIsNone(disallowed.search(json.dumps(rules)))
            risky_metadata_present |= any(key in task for key in ('faulty_file', 'primary_case_id', 'repair_seed'))
        self.assertTrue(risky_metadata_present)
        # This proves the current source/rule inputs have no such labels. A
        # future prompt builder still needs an explicit allowlist and pair test;
        # this test does not certify prompts that have not been constructed.


if __name__ == '__main__':
    unittest.main()
