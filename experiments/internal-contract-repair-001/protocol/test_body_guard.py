"""Offline only: no verifier, subprocess, provider, credential or network access."""
from pathlib import Path
from unittest import mock
import copy
import hashlib
import importlib.util
import json
import shutil
import tempfile
import unittest

ROOT = Path(__file__).resolve().parent
INPUTS = ROOT.parent / 'fixtures-and-controls'
PARENT = ROOT.parents[1] / 'internal-contract-propagation-001'


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
    return module


guard = load('new_method_policy', ROOT / 'body_guard.py')
extractor = load('unchanged_method_envelope', ROOT / 'extract_response.py')
builder = load('new_method_registry_builder', ROOT / 'build_registry.py')


def read_sources(path):
    return {p.name: p.read_text() for p in sorted(Path(path).glob('*.dfy'))}


def bodies(sources, task):
    result = {}
    for name in guard.EDITABLE_FILES:
        seed = read_sources(INPUTS / task['template_path'])[name].encode()
        span = task['body_boundaries'][name]
        prefix, suffix = seed[:span['start']], seed[span['end']:]
        raw = sources[name].encode()
        if not raw.startswith(prefix) or not raw.endswith(suffix):
            raise ValueError('Source is not eligible for the fixed new method header')
        result[name] = raw[len(prefix):-len(suffix)].decode()
    return result


class MethodBodyPolicyTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tasks = json.loads((INPUTS / 'tasks.json').read_bytes())
        cls.tasks_by_id = {t['task_id']: t for t in cls.tasks}
        cls.parent_cases = {c['case_id']: c for c in json.loads((PARENT / 'cases.json').read_bytes())}

    def source(self, task):
        return read_sources(INPUTS / task['template_path'])

    def accept(self, task, body_dict):
        return guard.parse_response(json.dumps(body_dict), self.source(task), task)

    def reject_body(self, task, filename, bad):
        payload = bodies(self.source(task), task); payload[filename] = bad
        with self.assertRaises(ValueError, msg=bad[:100]):
            self.accept(task, payload)

    def test_registry_inheritance_and_exact_input_inventory(self):
        self.assertEqual((ROOT / 'registry.json').read_bytes(), builder.serialized())
        self.assertEqual(guard.sha((ROOT / 'registry.json').read_bytes()), guard.REGISTRY_SHA256)
        self.assertEqual(guard.sha((ROOT / 'inherited' / 'typed_guard.py').read_bytes()), guard.TYPED_SHA256)
        self.assertEqual(guard.sha((ROOT / 'inherited' / 'syntax_guard.py').read_bytes()), guard.inherited.SYNTAX_SHA256)
        self.assertEqual(guard.sha((ROOT / 'extract_response.py').read_bytes()),
                         '60446deb6d0ec4bcf9d788a3fd0ea7ba9e7275255769c61e61382513cb77e7de')
        for name, expected in json.loads((ROOT / 'test-inputs.json').read_bytes())['files'].items():
            self.assertEqual(guard.sha((ROOT / name).read_bytes()), expected, name)

    def test_all_fixed_header_controls_and_seeds_reconstruct_exactly(self):
        variants = ('paired_repair', 'alternative', 'helper_only', 'contract_only',
                    'unguarded_call', 'lost_result_transform', 'wrong_helper_implementation')
        count = 0
        for task in self.tasks:
            candidates = [('new_seed', self.source(task))]
            for variant in variants:
                candidate = read_sources(PARENT / 'fixtures' / task['semantic_instance'] / variant)
                case = self.parent_cases[task['semantic_instance'] + '-' + variant]
                self.assertEqual(guard.hashes(candidate), case['source_sha256'])
                candidates.append((variant, candidate))
            for label, expected in candidates:
                with self.subTest(task=task['task_id'], variant=label):
                    actual, receipt = self.accept(task, bodies(expected, task))
                    self.assertEqual(actual, expected)
                    self.assertEqual(receipt['candidate_sha256'], guard.hashes(expected))
                    self.assertEqual(receipt['parent_sha256'], task['source_sha256'])
                    self.assertEqual(receipt['policy_id'], guard.POLICY_ID)
                    self.assertEqual(receipt['policy_code_sha256'], guard.sha((ROOT / 'body_guard.py').read_bytes()))
                    self.assertFalse(receipt['helper_call_required'])
                    self.assertFalse(receipt['semantic_verification_performed'])
                    count += 1
        self.assertEqual(count, 16)

    def test_old_api_workspace_is_not_a_current_header_candidate(self):
        for task in self.tasks:
            for variant in ('reference', 'caller_only'):
                old = read_sources(PARENT / 'fixtures' / task['semantic_instance'] / variant)
                self.assertEqual(guard.hashes(old), self.parent_cases[task['semantic_instance'] + '-' + variant]['source_sha256'])
                with self.assertRaises(ValueError):
                    bodies(old, task)
                with self.assertRaises(ValueError):
                    guard.parse_response(json.dumps({'Helper.dfy': '', 'Client.dfy': ''}), old, task)

    def test_transparent_kernel_direct_implementation_is_admitted(self):
        arithmetic, maps = self.tasks
        ac = {'Helper.dfy': 'r := K.Endpoint(start,length,cap) - start;\n',
              'Client.dfy': 'result := K.Endpoint(start,length,cap);\n'}
        mc = {'Helper.dfy': 'r := K.Entry(m,key);\n',
              'Client.dfy': 'remaining := K.Erase(m,key); removed := K.Entry(m,key);\n'}
        for task, payload in ((arithmetic, ac), (maps, mc)):
            candidate, receipt = self.accept(task, payload)
            self.assertEqual(set(candidate), set(guard.FILES))
            self.assertEqual(receipt['bodies']['Client.dfy']['call_inventory']['method'], {})
            self.assertGreater(len(receipt['bodies']['Client.dfy']['call_inventory']['pure']), 0)

    def test_mathematical_failure_and_missing_assignments_are_not_policy_failures(self):
        for task in self.tasks:
            payload = {'Helper.dfy': '', 'Client.dfy': 'assert false;\n'}
            _, receipt = self.accept(task, payload)
            self.assertEqual(receipt['bodies']['Helper.dfy']['statements'], 0)
        arithmetic = self.tasks[0]
        payload = {'Helper.dfy': 'r := length + 9;\n',
                   'Client.dfy': 'result := H.Transfer(length,start,cap);\n'}
        _, receipt = self.accept(arithmetic, payload)
        self.assertEqual(receipt['bodies']['Client.dfy']['call_inventory']['method'], {'H.Transfer': 1})

    def test_fresh_locals_assignment_branching_and_map_displays(self):
        a, m = self.tasks
        self.accept(a, {'Helper.dfy': 'var delta := length; delta := delta - 1; r := delta;\n',
                        'Client.dfy': 'if cap < start { result := cap; } else if length == 0 { result := start; } else { var delta := H.Transfer(start,length,cap); result := start + delta; }\n'})
        _, receipt = self.accept(m, {'Helper.dfy': 'var patch := map[key := m[key], key + 1 := 9]; r := patch;\n',
                                    'Client.dfy': 'var patch := map[]; patch := patch[key := 1]; remaining := K.Exclude(m,patch); removed := map[key := map[key := 4][key]]; assert key in map[key := 1].Keys;\n'})
        self.assertEqual(receipt['bodies']['Client.dfy']['call_inventory']['pure'], {'K.Exclude': 1})

    def test_quantified_expressions_and_lexical_scope(self):
        task = self.tasks[1]
        self.accept(task, {'Helper.dfy': 'r := map x | x in m && x == key :: m[x];\n',
                           'Client.dfy': 'remaining := map x | x in m && x != key :: m[x]; removed := map[]; assert forall z | z in remaining :: z in m;\n'})
        for bad in ('var x := 1; assert forall x | x in m :: x == x;',
                    'var patch := map x | x in m :: m[x]; remaining := patch; removed := map[]; assert x == 0;',
                    'if true { var patch := map[]; } remaining := patch; removed := map[];',
                    'removed := map m | m == 0 :: 1;',
                    'assert forall remaining | true :: remaining == remaining;'):
            self.reject_body(task, 'Client.dfy', bad)

    def test_calls_have_role_arity_types_and_full_rhs_only(self):
        a, m = self.tasks
        for bad in ('r := H.Transfer(start,length,cap);', 'r := Helper.Transfer(start,length,cap);',
                    'r := Transfer(start,length,cap);', 'r := K.Unknown(start);'):
            self.reject_body(a, 'Helper.dfy', bad)
        for bad in ('H.Transfer(start,length,cap);', 'result := H.Transfer(start,length);',
                    'result := H.Transfer(start,true,cap);', 'result := H.Transfer(start,length,cap) + start;',
                    'result := K.Endpoint(H.Transfer(start,length,cap),length,cap);',
                    'result := if true then H.Transfer(start,length,cap) else 0;',
                    'result := Client.Target(start,length,cap);', 'result := H.Hidden(start,length,cap);',
                    'result := (H.Transfer(start,length,cap));'):
            self.reject_body(a, 'Client.dfy', bad)
        for bad in ('remaining := H.Transfer(key,m);', 'remaining := K.Exclude(m,key);',
                    'removed := map[true := key];', 'removed := map[key := true];',
                    'removed := [];', 'remaining := 0;', 'assert m == key;'):
            self.reject_body(m, 'Client.dfy', bad)

    def test_input_output_alias_and_keyword_shadowing(self):
        a, m = self.tasks
        for bad in ('start := 0;', 'var start := 0;', 'var r := 0;', 'var K := 0;',
                    'var int := 0;', 'var nat := 0;', "var x' := 0;", 'var _hidden := 0;',
                    'var delta := 1; var delta := 2;', 'var delta := 1; if true { var delta := 2; }',
                    'var delta := 1; delta := true;', 'var delta := delta + 1;'):
            self.reject_body(a, 'Helper.dfy', bad)
        for bad in ('var removed := map[];', 'var H := m;', 'm[key] := 2;',
                    'remaining.Keys := {};', 'remaining, removed := H.Transfer(m,key);',
                    'var x := 1; removed := map x | x in m :: m[x];'):
            self.reject_body(m, 'Client.dfy', bad)

    def test_bypasses_declarations_loops_and_early_returns_rejected(self):
        task = self.tasks[0]
        bads = ('assume false;', 'assert {:axiom} false;', 'reveal K.Endpoint();',
                'expect false;', 'return;', 'return 1;', 'while true { }',
                'forall x | true ensures true { }', 'calc { 0; }',
                'method Evil() { }', 'lemma Evil() { }', 'ghost var x := 1;',
                'import X = Kernel', 'r := new int;', 'assert true by { assume false; }',
                'assert true; // ignored', '/* text */ r := 0;', 'print "x";',
                '  }\n}\nmodule Escape {}\n', 'var x: int := 0;', 'r := 2 * length;',
                'r := 1000000000000;')
        for bad in bads:
            self.reject_body(task, 'Helper.dfy', bad)

    def test_exact_json_keys_and_separate_tolerant_envelope(self):
        task = self.tasks[0]; source = self.source(task); good = json.dumps(bodies(source, task))
        for raw in ('{}', '[]', '{"Helper.dfy":"","Client.dfy":"","Helper.dfy":""}',
                    '{"Helper.dfy":null,"Client.dfy":""}', '{"Helper.dfy":NaN,"Client.dfy":""}',
                    '{"files":{"Helper.dfy":"","Client.dfy":""}}',
                    '{"Helper.dfy":"","Client.dfy":"","Kernel.dfy":""}',
                    '```json\n' + good + '\n```', good + '\n' + good):
            with self.assertRaises(ValueError):
                guard.parse_response(raw, source, task)
        candidate, receipt = extractor.parse_response('A candidate follows.\n```json\n' + good + '\n```\n', source, task, guard)
        self.assertEqual(candidate, source)
        self.assertEqual(receipt['body_guard']['policy_id'], guard.POLICY_ID)
        for raw in ('```json\n' + good + '\n```\n```json\n' + good + '\n```',
                    '{"Helper.dfy":"","Client.dfy":"","Client.dfy":""}'):
            with self.assertRaises(ValueError):
                extractor.parse_response(raw, source, task, guard)

    def test_full_workspace_headers_and_boundaries_cannot_change(self):
        for task in self.tasks:
            good = json.dumps(bodies(self.source(task), task))
            for name in guard.FILES:
                altered = self.source(task); altered[name] += '\n'
                with self.assertRaises(ValueError):
                    guard.parse_response(good, altered, task)
            altered = self.source(task); altered['Extra.dfy'] = 'module Extra {}'
            with self.assertRaises(ValueError):
                guard.parse_response(good, altered, task)
            altered = self.source(task); del altered['Kernel.dfy']
            with self.assertRaises(ValueError):
                guard.parse_response(good, altered, task)
            for key in ('source_sha256', 'body_boundaries', 'file_rules', 'public_contract_prefix', 'fixed_helper_prefix'):
                altered_task = copy.deepcopy(task)
                if key == 'source_sha256': altered_task[key]['Helper.dfy'] = '0' * 64
                elif key == 'body_boundaries': altered_task[key]['Helper.dfy']['start'] += 1
                elif key == 'file_rules': altered_task[key]['Helper.dfy']['calls'] = {'H.Transfer': 3}
                else: altered_task[key] += '\n'
                with self.assertRaises(ValueError):
                    guard.parse_response(good, self.source(task), altered_task)

    def test_registry_tampering_rejected(self):
        original = Path.read_bytes
        def altered(path):
            raw = original(path)
            return raw + b'\n' if path == ROOT / 'registry.json' else raw
        with mock.patch.object(Path, 'read_bytes', altered):
            with self.assertRaisesRegex(ValueError, 'registry changed'):
                guard.registry()

    def test_isolated_runtime_import_requires_only_pinned_policy_files(self):
        names = ('body_guard.py', 'registry.json', 'extract_response.py',
                 'inherited/typed_guard.py', 'inherited/syntax_guard.py')
        with tempfile.TemporaryDirectory(prefix='method-policy-isolated-') as directory:
            target = Path(directory)
            for name in names:
                dest = target / name; dest.parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(ROOT / name, dest)
            isolated = load('isolated_method_policy', target / 'body_guard.py')
            for task in self.tasks:
                source = self.source(task)
                actual, receipt = isolated.parse_response(json.dumps(bodies(source, task)), source, task)
                self.assertEqual(actual, source)
                self.assertEqual(receipt['policy_id'], guard.POLICY_ID)

    def test_finite_limits_and_invalid_unicode(self):
        a, m = self.tasks
        for bad in (' ' * (guard.MAX_BODY + 1), 'assert true;\n' * (guard.MAX_STATEMENTS + 1),
                    'r := ' + '(' * 40 + '0' + ')' * 40 + ';',
                    'if true {' * 26 + 'r := 0;' + '}' * 26,
                    'r := ' + '+'.join(['0'] * 130) + ';',
                    'r := ' + '[' * (guard.MAX_TOKENS + 1), '\ud800'):
            self.reject_body(a, 'Helper.dfy', bad)
        entries = ','.join(str(i) + ' := 1' for i in range(guard.MAX_MAP_ENTRIES + 1))
        self.reject_body(m, 'Helper.dfy', 'r := map[' + entries + '];')
        with self.assertRaises(ValueError):
            guard.parse_response(' ' * (guard.MAX_RESPONSE + 1), self.source(a), a)


if __name__ == '__main__':
    unittest.main(verbosity=2)
