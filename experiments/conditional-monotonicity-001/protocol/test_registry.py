"""Reuse the v2 grammar tests and test only the new trusted task/API registry."""
import ast
import importlib.util
import json
from pathlib import Path
import unittest

import body_guard as guard

ROOT = Path(__file__).resolve().parents[1]
V2 = ROOT.parent / 'reasoning-output-policy-002'
TASKS = json.loads((ROOT / 'tasks.json').read_text())
CHECKS = json.loads((ROOT / 'checks.json').read_text())


def module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    result = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(result)
    return result


v2_tests = module('v2_regressions', V2 / 'test_body_guard.py')
LegacyGuardTests = v2_tests.LegacyGuardTests
VersionTwoTests = v2_tests.VersionTwoTests


def sources(task, variant):
    return {p.name: p.read_text() for p in (ROOT / 'fixtures' / task['task_id'] / variant).glob('*.dfy')}


def payload(task, variant):
    seed = sources(task, 'empty'); target = sources(task, variant); bodies = {}
    for name in task['editable_files']:
        prefix, suffix = guard.split_seed(seed[name])
        assert target[name].startswith(prefix) and target[name].endswith(suffix)
        bodies[name] = target[name][len(prefix):-len(suffix)]
    return json.dumps(bodies), seed, target


class RegistryTests(unittest.TestCase):
    def test_only_version_and_registry_change_the_v2_parser(self):
        def syntax(path):
            tree = ast.parse(path.read_text())
            tree.body = tree.body[1:]  # The module docstring may describe the registry extension.
            tree.body = [node for node in tree.body
                         if not (isinstance(node, ast.FunctionDef) and node.name == 'policy')
                         and not (isinstance(node, ast.Assign) and isinstance(node.targets[0], ast.Name)
                                  and node.targets[0].id == 'VERSION')]
            return ast.dump(tree, include_attributes=False)
        self.assertEqual(syntax(V2 / 'body_guard.py'), syntax(ROOT / 'protocol/body_guard.py'))

    def test_all_new_reference_and_semantic_negative_bytes_replay(self):
        tasks = {t['task_id']:t for t in TASKS}; count = 0
        for check in CHECKS:
            if check['variant'] == 'hidden_shortcut': continue
            task = tasks[check['task_id']]
            raw, seed, target = payload(task, check['variant'])
            candidate, decision = guard.parse_response(raw, seed, task)
            self.assertEqual(candidate, target)
            self.assertEqual(decision['candidate_sha256'], check['source_sha256'])
            self.assertFalse(decision['semantic_verification_performed'])
            count += 1
        self.assertEqual(count, 28)

    def test_hidden_views_wrong_arities_and_cross_helper_calls_reject(self):
        for task in TASKS:
            raw, seed, _ = payload(task, 'hidden_shortcut')
            with self.assertRaises(ValueError): guard.parse_response(raw, seed, task)
            for body in ['H.Prove(x,y,l,h);', 'HelperB.Prove(x,y,l,h);',
                         'K.Internal();', 'A.Observe(x,l,h);',
                         'A.Assemble(x,l,h);', 'O2.Below(x,l,h);']:
                raw = json.dumps({name:body for name in task['editable_files']})
                with self.assertRaises(ValueError): guard.parse_response(raw, seed, task)

    def test_new_parameters_are_protected_and_files_cannot_escape(self):
        for task in TASKS:
            _, seed, _ = payload(task, 'reference')
            for body in ['var x := 0;', 'var y := 0;', 'var l := 0;', 'var h := 0;',
                         'assume false;', '} ensures true {', 'reveal K.Clamp();']:
                raw = json.dumps({name:body for name in task['editable_files']})
                with self.assertRaises(ValueError): guard.parse_response(raw, seed, task)
            raw, seed, _ = payload(task, 'reference')
            altered = dict(seed);altered['ClientA.dfy'] += '\n'
            with self.assertRaises(ValueError): guard.parse_response(raw, altered, task)

    def test_old_policy_remains_pinned_and_rejects_the_new_registry(self):
        self.assertEqual(guard.digest((V2 / 'body_guard.py').read_text()),
                         'e5b6abe07164aa7fe4136769f9469de1d15797b4495e3882ffb699be030ed06f')
        old = module('unchanged_v2_policy', V2 / 'body_guard.py')
        for task in v2_tests.legacy.TASKS:
            self.assertEqual(old.policy(task), guard.policy(task))
        for task in TASKS:
            raw, seed, _ = payload(task, 'reference')
            with self.assertRaisesRegex(ValueError, 'Unsupported semantic instance'):
                old.parse_response(raw, seed, task)


if __name__ == '__main__': unittest.main(verbosity=2)
