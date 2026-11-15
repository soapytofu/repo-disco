"""Offline construction, grammar and finite semantic checks; never invokes Dafny."""
from pathlib import Path
import importlib.util
import itertools
import json
import re
import tempfile
import unittest
from unittest.mock import patch
import build as b

ROOT = Path(__file__).resolve().parent


def load(name):
    return json.loads((ROOT/name).read_bytes())


def workspace(path):
    return {p.name: p.read_text() for p in sorted(path.glob('*.dfy'))}


class Design(unittest.TestCase):
    def test_reproducible_sources_counts_and_no_duplicate_workspace_submissions(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            summary = b.generate(root)
            self.assertEqual(summary['checks'], 24)
            self.assertEqual((summary['expected_success'], summary['expected_proof_failure'], summary['expected_resolution_failure']), (6, 16, 2))
            for name in ('tasks.json', 'cases.json', 'semantic-cases.json', 'fixture-manifest.json'):
                self.assertEqual((ROOT/name).read_bytes(), (root/name).read_bytes(), name)
            pins = json.loads((root/'fixture-manifest.json').read_bytes())
            for name, digest in pins.items():
                self.assertEqual(b.sha((ROOT/name).read_bytes()), digest, name)
        inventories = [tuple(sorted(c['source_sha256'].items())) for c in load('cases.json')]
        self.assertEqual(len(inventories), len(set(inventories)), 'Use an evidence alias instead of duplicate checks')

    def test_every_contract_provider_client_and_include_is_protected(self):
        tasks = {t['task_id']: t for t in load('tasks.json')}
        for case in load('cases.json'):
            task = tasks[case['task_id']]
            source = workspace(ROOT/case['path'])
            template = workspace(ROOT/'templates'/task['task_id'])
            self.assertEqual(set(source), set(template))
            self.assertEqual(b.hashes(source), case['source_sha256'])
            self.assertEqual(b.hashes(template), task['source_sha256'])
            for name, empty in template.items():
                if name not in b.EDITABLE:
                    self.assertEqual(source[name], empty)
                else:
                    span = b.body_boundary(empty)
                    raw = empty.encode()
                    prefix, suffix = raw[:span['start']], raw[span['end']:]
                    self.assertTrue(source[name].encode().startswith(prefix))
                    self.assertTrue(source[name].encode().endswith(suffix))
                    self.assertEqual(case['body_boundaries'][name]['protected_sha256'], span['protected_sha256'])
            for text in source.values():
                self.assertNotRegex(text, r'\bassume\b|\{:\s*(?:axiom|verify|extern)\b')
                self.assertNotIn('//', text)
                self.assertNotIn('/*', text)

    def test_pipeline_named_scope_file_rules_and_nonempty_unlabelled_bases(self):
        for task in load('tasks.json'):
            self.assertEqual(task['sharing'], 'pipeline')
            self.assertEqual(task['editable_files'], b.EDITABLE)
            self.assertEqual(task['target_dependencies'], b.DEPENDENCIES)
            self.assertFalse(task['held_out'])
            base = workspace(ROOT/'fixtures'/task['task_id']/'faulty')
            self.assertNotIn('include "HelperB.dfy"', base['HelperA.dfy'])
            self.assertIn('include "HelperA.dfy"', base['HelperB.dfy'])
            for name in ('ClientA.dfy', 'ClientB.dfy'):
                self.assertIn('import H = HelperB', base[name])
            for name in b.EDITABLE:
                rules = task['file_rules'][name]
                self.assertEqual(rules['variables'], task['file_parameters'][name])
                self.assertEqual(rules['parameter_types'], {v: 'int' for v in rules['variables']})
                self.assertEqual(rules['call_types'], {n: ['int']*a for n, a in rules['calls'].items()})
                self.assertEqual(rules['pure_types'], {n: dict(arguments=['int']*a, result='bool') for n, a in rules['pure'].items()})
                span = b.body_boundary(base[name])
                self.assertTrue(base[name].encode()[span['start']:span['end']].strip())
                self.assertNotRegex(base[name], r'(?i)fault|wrong|counterexample|TODO|repair|deliberate')
            self.assertNotIn('H.Prove', task['file_rules']['HelperA.dfy']['calls'])
            self.assertIn('H.Prove', task['file_rules']['HelperB.dfy']['calls'])

    def test_only_one_module_repaired_controls_preserve_the_other_exactly(self):
        cases = {c['case_id']: c for c in load('cases.json')}
        for task in load('tasks.json'):
            tid = task['task_id']
            base = workspace(ROOT/'fixtures'/tid/'faulty')
            for side, untouched in [('a', 'HelperB.dfy'), ('b', 'HelperA.dfy')]:
                case = cases[tid+'-only_'+side+'_repair']
                source = workspace(ROOT/case['path'])
                changed = sorted(n for n in source if source[n] != base[n])
                self.assertEqual(changed, ['Helper'+side.upper()+'.dfy'])
                self.assertEqual(source[untouched], base[untouched])
                is_repair = (side == 'b') == (task['semantic_instance'] == 'intersection_or_separation')
                self.assertEqual(case['expected'] == 'success', is_repair)
            fault = cases[tid+'-faulty']
            self.assertEqual(len(fault['expected_failed_targets']), 1)
            self.assertTrue(fault['expected_local_targets']['ClientA.Target'])
            self.assertTrue(fault['expected_local_targets']['ClientB.Target'])
            self.assertFalse(fault['expected_dependency_closed_targets']['ClientA.Target'])
            self.assertFalse(fault['expected_dependency_closed_targets']['ClientB.Target'])

    def test_existing_ast_grammar_admits_all_semantic_bodies_but_not_hidden_calls(self):
        spec = importlib.util.spec_from_file_location('selection_witness_grammar', ROOT/'inputs/grammar/body_guard.py')
        guard = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(guard)
        tasks = {t['task_id']: t for t in load('tasks.json')}
        admitted = rejected = 0
        for case in load('cases.json'):
            task = tasks[case['task_id']]
            source = workspace(ROOT/case['path'])
            for name in b.EDITABLE:
                span = b.body_boundary(source[name])
                body = source[name].encode()[span['start']:span['end']].decode()
                with patch.object(guard, 'policy', return_value=task['file_rules'][name]):
                    parser = guard.Grammar(body, task)
                    if case['variant'] == 'hidden_shortcut_b' and name == 'HelperB.dfy':
                        with self.assertRaises(ValueError):
                            parser.sequence()
                        rejected += 1
                    else:
                        parser.sequence()
                        self.assertIsNone(parser.peek())
                        admitted += 1
        self.assertEqual((admitted, rejected), (46, 2))

    def test_finite_intersection_decision_sound_exhaustive_and_touching_positive(self):
        count = 0
        for a, b_, c, d in itertools.product(range(-2, 3), repeat=4):
            if a > b_ or c > d:
                continue
            possible = [w for w in range(-2, 3) if a <= w <= b_ and c <= w <= d]
            kind = -1 if b_ < c else 1 if d < a else 0
            w = max(a, c) if kind == 0 else 0
            self.assertEqual(kind == 0, bool(possible))
            self.assertEqual(kind == -1, b_ < c)
            self.assertEqual(kind == 1, d < a)
            if kind == 0:
                self.assertIn(w, possible)
                self.assertIn(min(b_, d), possible)
            for shift in (-3, 0, 4):
                aa, bb, cc, dd = c+shift, d+shift, a+shift, b_+shift
                transformed_kind = -1 if bb < cc else 1 if dd < aa else 0
                self.assertEqual(transformed_kind, -kind)
                if transformed_kind == 0:
                    ww = max(aa, cc)
                    self.assertTrue(aa <= ww <= bb and cc <= ww <= dd)
            count += 1
        self.assertEqual(count, 225)
        example = load('semantic-cases.json')['intersection_or_separation']['touching_is_overlap']
        self.assertEqual(example['b'], example['c'])
        self.assertFalse(example['b'] < example['c'])

    def test_finite_sum_gap_precondition_is_necessary_sufficient_and_translation_stable(self):
        count = 0
        feasible_count = 0
        for a, b_, c, d in itertools.product(range(-2, 3), repeat=4):
            if a > b_ or c > d:
                continue
            for s, g in itertools.product(range(-5, 6), range(-1, 4)):
                requires = (a <= s-c and s-d <= b_ and g > 0 and a+a+g <= s and (s-d)+(s-d)+g <= s)
                pairs = [(u, v) for u in range(a, b_+1) for v in range(c, d+1) if u+v == s and g > 0 and u+g <= v]
                self.assertEqual(requires, bool(pairs), (a, b_, c, d, s, g))
                if requires:
                    u, v = max(a, s-d), s-max(a, s-d)
                    self.assertIn((u, v), pairs)
                    for shift in (-3, 0, 4):
                        aa, bb, cc, dd, ss = a+shift, b_+shift, c+shift, d+shift, s+shift+shift
                        uu, vv = max(aa, ss-dd), ss-max(aa, ss-dd)
                        self.assertEqual((uu, vv), (u+shift, v+shift))
                        self.assertTrue(aa <= uu <= bb and cc <= vv <= dd and uu+vv == ss and uu+g <= vv)
                    feasible_count += 1
                count += 1
        self.assertEqual(count, 12375)
        self.assertGreater(feasible_count, 0)
        example = load('semantic-cases.json')['conserved_sum_gap']['bad_endpoint']
        self.assertGreater(example['bad_v'], example['d'])
        self.assertEqual(example['correct_u']+example['correct_v'], example['s'])
        self.assertLessEqual(example['correct_u']+example['g'], example['correct_v'])


if __name__ == '__main__':
    unittest.main(verbosity=2)
