"""Exact fixture reconstruction and adversarial scope checks; no verifier calls."""
from pathlib import Path
from unittest.mock import patch
import copy
import hashlib
import json
import sys
import tempfile
import unittest

import body_guard as guard
import build_registry
import repair_protocol as adapter

ROOT = Path(__file__).resolve().parent
PARENT = ROOT.parent


def load(path):
    return json.loads(path.read_text())


def files(folder):
    return {path.name: path.read_text() for path in sorted(folder.glob('*.dfy'))}


def records():
    rows = []
    for family in ('witness', 'maps'):
        base = PARENT / family
        tasks = {task['task_id']: task for task in load(base / 'tasks.json')}
        cases = load(base / 'cases.json')
        for case in cases:
            task = tasks[case['task_id']]
            parent = next(c for c in cases if c['task_id'] == task['task_id'] and c['variant'] == 'faulty')
            rows.append(dict(family=family, task=task, case=case,
                template=files(base / task.get('template_path', 'templates/' + task['task_id'])),
                base=files(base / parent['path']), candidate=files(base / case['path'])))
    return rows


def payload(record):
    bodies = {}
    for name in guard.EDITABLE_FILES:
        before, after = guard.split_seed(record['template'][name])
        source = record['candidate'][name]
        if not source.startswith(before) or not source.endswith(after):
            raise ValueError('Fixture changes protected helper bytes')
        bodies[name] = source[len(before):len(source) - len(after)]
    return json.dumps(bodies)


class ProtocolTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.rows = records()

    def record(self, task_id=None, variant='reference'):
        return next(row for row in self.rows if row['case']['variant'] == variant and (task_id is None or row['task']['task_id'] == task_id))

    def parse(self, bodies, row=None):
        row = row or self.record()
        return guard.parse_response(json.dumps(bodies), row['template'], row['task'])

    def test_exact_reference_alternative_and_semantic_negative_bytes(self):
        admitted = rejected = body_count = 0
        inventories = [(row['task']['task_id'], json.dumps(row['case']['source_sha256'], sort_keys=True)) for row in self.rows]
        self.assertEqual(len(set(inventories)), len(inventories), 'Distinct case list contains duplicate source inventories')
        for row in self.rows:
            with self.subTest(case=row['case']['case_id']):
                self.assertEqual(guard.hashes(row['candidate']), row['case']['source_sha256'])
                if row['case']['expected'] == 'resolution_failure':
                    with self.assertRaises(ValueError):
                        guard.parse_response(payload(row), row['template'], row['task'])
                    rejected += 1
                    continue
                actual, decision = guard.parse_response(payload(row), row['template'], row['task'])
                self.assertEqual(actual, row['candidate'])
                self.assertEqual(decision['policy_id'], guard.POLICY_ID)
                self.assertFalse(decision['semantic_verification_performed'])
                admitted += 1
                body_count += len(decision['bodies'])
        self.assertEqual(rejected, 4)
        self.assertEqual(admitted, len(self.rows) - rejected)
        self.assertEqual(body_count, 2 * admitted)

    def test_exact_failing_base_repair_through_frozen_adapter(self):
        for row in self.rows:
            if row['case']['expected'] == 'resolution_failure':
                continue
            with self.subTest(case=row['case']['case_id']):
                candidate, decision = adapter.apply_response(payload(row), row['base'], row['template'], row['task'], guard.hashes(row['base']))
                self.assertEqual(candidate, row['candidate'])
                self.assertEqual(decision['model_calls'], 0)
                self.assertEqual(decision['original_guard_decision']['body_guard']['policy_id'], guard.POLICY_ID)

    def test_exact_declared_signatures_exports_and_dependency_direction(self):
        entries = guard.registry()
        self.assertEqual(len(entries), 4)
        for task_id, entry in entries.items():
            row = self.record(task_id)
            self.assertTrue(build_registry.review_sources(row['template'], row['task']))
            self.assertEqual(guard.validate_template(row['template'], row['task']), entry)
            self.assertNotIn('H.Prove', entry['file_rules']['HelperA.dfy']['calls'])
            self.assertIn('H.Prove', entry['file_rules']['HelperB.dfy']['calls'])
            self.assertEqual(entry['editable_files'], ['HelperA.dfy', 'HelperB.dfy'])

    def test_construction_review_rejects_graph_export_and_type_drift(self):
        row = self.record('inverse_exchange_pipeline')
        changes = [('HelperA.dfy', 'module HelperA {', 'module HelperA {\n  import H = HelperB'),
            ('HelperB.dfy', 'import H = HelperA', 'import H = HelperB'),
            ('ClientA.dfy', 'import H = HelperB', 'import H = HelperA'),
            ('HelperA.dfy', 'Ops`Public', 'Ops`Hidden'),
            ('HelperA.dfy', 'p: int', 'p: bool')]
        for filename, old, new in changes:
            changed = dict(row['template'])
            self.assertIn(old, changed[filename])
            changed[filename] = changed[filename].replace(old, new, 1)
            with self.subTest(filename=filename, new=new), self.assertRaises(ValueError):
                build_registry.review_sources(changed, row['task'])
        changed_task = copy.deepcopy(row['task'])
        rule = changed_task['file_rules']['HelperA.dfy']
        rule['calls']['O.HiddenPutAt'] = 4
        rule['call_types']['O.HiddenPutAt'] = ['map<int,int>', 'int', 'int', 'int']
        with self.assertRaises(ValueError):
            build_registry.review_sources(row['template'], changed_task)
        changed_task = copy.deepcopy(row['task'])
        changed_task['file_rules']['HelperA.dfy']['call_types']['O.PutKeys'][0] = 'int'
        with self.assertRaises(ValueError):
            build_registry.review_sources(row['template'], changed_task)

    def test_all_protected_source_files_and_contract_spans(self):
        for task_id in guard.registry():
            row = self.record(task_id)
            for name in row['template']:
                changed = dict(row['template'])
                changed[name] += '\n'
                with self.subTest(task=task_id, source=name), self.assertRaises(ValueError):
                    guard.parse_response(payload(row), changed, row['task'])
            changed = dict(row['template'], **{'Extra.dfy': ''})
            with self.assertRaises(ValueError):
                guard.parse_response(payload(row), changed, row['task'])
            for name in row['base']:
                changed = dict(row['base'])
                changed[name] = '// edited\n' + changed[name]
                with self.subTest(task=task_id, parent=name), self.assertRaises(ValueError):
                    adapter.apply_response(payload(row), changed, row['template'], row['task'], guard.hashes(changed))
            wrong_hashes = guard.hashes(row['base'])
            wrong_hashes['HelperA.dfy'] = '0' * 64
            with self.assertRaises(ValueError):
                adapter.apply_response(payload(row), row['base'], row['template'], row['task'], wrong_hashes)

    def test_task_rules_cannot_expand_file_environment(self):
        row = self.record()
        mutations = [('task_id', 'other'), ('sharing', 'shared'), ('entry', 'HelperA.dfy'),
            ('editable_files', ['HelperB.dfy']), ('source_sha256', {}), ('body_boundaries', {}),
            ('file_rules', {}), ('calls', {}), ('pure', {}), ('params', [])]
        for key, value in mutations:
            changed = copy.deepcopy(row['task'])
            changed[key] = value
            with self.subTest(key=key), self.assertRaises(ValueError):
                guard.parse_response(payload(row), row['template'], changed)
        changed = copy.deepcopy(row['task'])
        changed['file_rules']['HelperA.dfy'] = changed['file_rules']['HelperB.dfy']
        with self.assertRaises(ValueError):
            guard.parse_response(payload(row), row['template'], changed)
        changed = copy.deepcopy(row['task'])
        changed['file_rules']['HelperB.dfy']['parameter_types']['a'] = 'bool'
        with self.assertRaises(ValueError):
            guard.parse_response(payload(row), row['template'], changed)

    def test_exact_two_keys_duplicate_json_and_bypass_rejections(self):
        row = self.record()
        bodies = json.loads(payload(row))
        invalid = [{}, [], {'body': bodies}, {'HelperA.dfy': bodies['HelperA.dfy']},
            dict(bodies, **{'ClientA.dfy': ''}), dict(bodies, **{'../HelperA.dfy': ''}),
            {name: None for name in bodies}, {name: [] for name in bodies}, {name: 0 for name in bodies}]
        for value in invalid:
            with self.subTest(value=str(value)[:50]), self.assertRaises(ValueError):
                self.parse(value, row)
        raw = ['{"HelperA.dfy":"", "HelperA.dfy":"", "HelperB.dfy":""}',
            '{"HelperA.dfy":NaN,"HelperB.dfy":""}', payload(row) + '{}',
            '{"HelperA.dfy":"", "HelperB.dfy":"",}',
            json.dumps({'HelperA.dfy': '\ud800', 'HelperB.dfy': ''})]
        for value in raw:
            with self.subTest(value=repr(value[:60])), self.assertRaises(ValueError):
                guard.parse_response(value, row['template'], row['task'])
        for name in bodies:
            for body in ('assume false;', 'reveal K.Valid();', 'assert {:axiom} false;',
                         'assert {:verify false} false;', 'while true {}', 'expect false;',
                         'import B = HelperB', 'lemma Prove() {}', '}\n}\nmodule X {\n{'):
                changed = dict(bodies)
                changed[name] = body
                with self.subTest(name=name, body=body), self.assertRaises(ValueError):
                    self.parse(changed, row)

    def test_actual_roles_cannot_be_interchanged_or_call_hidden_shortcuts(self):
        for task_id in guard.registry():
            row = self.record(task_id)
            bodies = json.loads(payload(row))
            # This checks the call environment rather than assuming every body
            # permutation must fail (an empty body is legal in either role).
            a_rules = row['task']['file_rules']['HelperA.dfy']
            args = ','.join(a_rules['variables'])
            changed = dict(bodies, **{'HelperA.dfy': 'H.Prove(' + args + ');'})
            with self.subTest(task=task_id), self.assertRaises(ValueError):
                self.parse(changed, row)
        for row in self.rows:
            if row['case']['expected'] == 'resolution_failure':
                with self.subTest(hidden=row['case']['case_id']), self.assertRaises(ValueError):
                    adapter.apply_response(payload(row), row['base'], row['template'], row['task'], guard.hashes(row['base']))

    def test_frozen_envelope_remains_exact_and_preserves_body_strings(self):
        row = self.record()
        raw = 'Proof bodies follow.\n```json\n' + payload(row) + '\n```\n'
        with self.assertRaises(ValueError):
            guard.parse_response(raw, row['template'], row['task'])
        actual, decision = adapter.apply_response(raw, row['base'], row['template'], row['task'], guard.hashes(row['base']))
        self.assertEqual(actual, row['candidate'])
        self.assertEqual(decision['original_guard_decision']['envelope']['version'], 'repair-envelope-v2-explicit-json-001')
        for ambiguous in (raw + payload(row), raw + '\n```json\n' + payload(row) + '\n```', 'Explanation ' + payload(row)):
            with self.assertRaises(ValueError):
                adapter.apply_response(ambiguous, row['base'], row['template'], row['task'], guard.hashes(row['base']))

    def test_registry_hash_and_complete_source_inventory(self):
        inputs = load(ROOT / 'source-inputs.json')
        for rel, expected in inputs.items():
            self.assertEqual(hashlib.sha256((PARENT / rel).read_bytes()).hexdigest(), expected, rel)
        actual = {str(path.relative_to(PARENT)) for family in ('witness', 'maps') for top in ('templates', 'fixtures') for path in (PARENT / family / top).rglob('*.dfy')}
        self.assertEqual(actual, {rel for rel in inputs if rel.endswith('.dfy')})
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder)
            (path / 'registry.json').write_bytes((ROOT / 'registry.json').read_bytes() + b'\n')
            with patch.object(guard, 'ROOT', path), self.assertRaises(ValueError):
                guard.registry()


def replay_audit():
    rows = []
    for record in records():
        case = record['case']
        row = dict(task_id=record['task']['task_id'], case_id=case['case_id'], variant=case['variant'],
            fixture_expected_category=case['expected'], source_sha256=case['source_sha256'],
            payload_sha256=guard.digest(payload(record)))
        try:
            candidate, decision = adapter.apply_response(payload(record), record['base'], record['template'], record['task'], guard.hashes(record['base']))
        except ValueError as error:
            if case['expected'] != 'resolution_failure':
                raise
            row.update(admitted=False, rejection=str(error))
        else:
            if case['expected'] == 'resolution_failure' or candidate != record['candidate']:
                raise ValueError('Unexpected fixture reconstruction')
            row.update(admitted=True, exact_source_bytes=True,
                candidate_sha256=decision['candidate_sha256'],
                body_checks=len(decision['original_guard_decision']['body_guard']['bodies']))
        rows.append(row)
    return dict(policy_id=guard.POLICY_ID, adapter_abi=guard.VERSION,
        registry_sha256=guard.REGISTRY_SHA256, checks=len(rows),
        admitted_workspaces=sum(row['admitted'] for row in rows),
        hidden_controls_rejected=sum(not row['admitted'] for row in rows),
        exact_helper_body_reconstructions=sum(row.get('body_checks', 0) for row in rows),
        model_calls=0, verifier_invocations=0, semantically_verified_by_this_replay=False,
        frozen=False, rows=rows)


if __name__ == '__main__':
    if sys.argv[1:] == ['--write-replay']:
        audit = replay_audit()
        (ROOT / 'fixture-replay.json').write_text(json.dumps(audit, indent=2) + '\n')
        print(json.dumps({key: value for key, value in audit.items() if key != 'rows'}, indent=2))
    else:
        unittest.main()
