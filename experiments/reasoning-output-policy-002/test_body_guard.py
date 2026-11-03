"""Offline v2 regressions and adversarial syntax tests; no provider or Dafny."""
import importlib.util
import json
from pathlib import Path
import unittest

from body_guard import Grammar, parse_response, split_seed, digest

ROOT = Path(__file__).resolve().parent
EXPANSION = ROOT.parent / 'monorepo-reasoning-expansion-001'
PILOT = ROOT.parent / 'monorepo-reasoning-calibration-pilot-001'
DIAGNOSTIC = ROOT.parent / 'reasoning-response-diagnostic-001'

# Execute the unchanged nine v1 tests against this module and the current,
# verified revision-003 fixtures. The original test and guard files stay frozen.
spec = importlib.util.spec_from_file_location('legacy_guard_tests', EXPANSION / 'protocol/test_body_guard.py')
legacy = importlib.util.module_from_spec(spec)
spec.loader.exec_module(legacy)
legacy.ROOT = EXPANSION / 'revision-003'
legacy.TASKS = json.loads((legacy.ROOT / 'tasks.json').read_text())
legacy.CHECKS = json.loads((legacy.ROOT / 'checks.json').read_text())
LegacyGuardTests = legacy.BodyGuardTests


class VersionTwoTests(unittest.TestCase):
    def body(self, source, task=None):
        task = task or legacy.task_for()
        seeds = legacy.fixture(task, 'empty')
        raw = json.dumps({name: source for name in task['editable_files']})
        candidate, record = parse_response(raw, seeds, task)
        for name in task['editable_files']:
            prefix, suffix = split_seed(seeds[name])
            self.assertEqual(candidate[name], prefix + source + suffix)
        self.assertFalse(record['semantic_verification_performed'])
        return record

    def rejects(self, cases):
        for source in cases:
            with self.subTest(source=source), self.assertRaises(ValueError):
                self.body(source)

    def test_all_saved_responses_reconstruct_previously_checked_bytes(self):
        tasks = {t['task_id']: t for t in json.loads((PILOT / 'frozen-001/tasks.json').read_text())}
        trials = json.loads((PILOT / 'frozen-001/trials.json').read_text())
        counts = {'original': 0, 'diagnostic': 0}
        for trial in trials:
            with self.subTest(trial=trial['trial_id']):
                task = tasks[trial['task_id']]
                source_dir = PILOT / 'frozen-001/tasks' / task['task_id']
                seeds = {p.name: p.read_text() for p in source_dir.glob('*.dfy')}
                original = PILOT / 'model-001' / trial['trial_id']
                raw = json.loads((original / 'response.json').read_text())['text']
                candidate, _ = parse_response(raw, seeds, task)
                target = original / 'candidate'
                if target.is_dir():
                    counts['original'] += 1
                else:
                    target = DIAGNOSTIC / 'fixtures' / (trial['trial_id'] + '-unaltered-body')
                    counts['diagnostic'] += 1
                self.assertEqual(candidate, {p.name: p.read_text() for p in target.glob('*.dfy')})
        self.assertEqual(counts, {'original': 19, 'diagnostic': 5})

    def test_primed_identifier_alphabet_and_scope(self):
        self.body("var next' := k; var next'' := next'; assert next'' == k;")
        self.body("if true { var q' := k; } else { var q' := j; }")
        self.rejects(["var 'q := k;", "var q := 'x';", "var q' := q';",
                      "if true { var q' := k; } assert q' == k;",
                      "var q' := k; var q' := j;", 'var café := k;'])

    def test_set_displays_are_pure_expressions(self):
        self.body('var empty := {}; var keys := {k,j}; assert k in keys;')
        self.body('assert {k, k} == {k}; assert {k} + {} == {k};')
        self.rejects(['var keys := {q | q in m};', 'var keys := {k,};',
                      'var keys := {k; assume false;};', 'var keys := {K.Internal()};'])

    def test_functional_updates_do_not_allow_statement_mutation(self):
        self.body('var updated := m[k := x][j := y]; assert updated.Keys == m.Keys + {k,j};')
        self.rejects(['m[k] := x;', 'm := m[k := x];', 'var updated := m[k := x, j := y];',
                      'var updated := m[k := assume false];', 'var updated := m[k := K.Internal()];'])

    def test_map_comprehension_scope_and_fresh_binders(self):
        self.body('var removed := (map q | q in m && q != j :: m[q]); assert j !in removed;')
        self.body("var copy := (map q' | q' in m :: m[q']);")
        self.body('var nested := (map q | q in m :: (map r | r in m :: m[r]));')
        self.body('var first := (map q | q in m :: m[q]); var second := (map q | q in m :: m[q]);')
        self.rejects(['var removed := (map q | q in m :: m[q]); assert q == k;',
                      'var removed := (map k | k in m :: m[k]);',
                      'var removed := (map K | K in m :: m[K]);',
                      'var q := k; var removed := (map q | q in m :: m[q]);',
                      'var nested := (map q | q in m :: (map q | q in m :: m[q]));',
                      'forall q | q in m ensures q in m { var copy := (map q | q in m :: m[q]); }',
                      'var map := m;'])

    def test_unsupported_map_forms_are_rejected(self):
        self.rejects(['var copy := map[k := x];', 'var copy := (map q:int | q in m :: m[q]);',
                      'var copy := (map q,r | q in m :: m[q]);',
                      'var copy := (map q | q in m :: q := m[q]);',
                      'var copy := (imap q | q in m :: m[q]);',
                      'var copy := (map q | q in m :: unbound);'])

    def test_new_expression_positions_cannot_hide_bypasses(self):
        forbidden = ['assume false', 'reveal K.Put()', 'expect false', 'new Object()',
                     'K.Internal()', 'HelperB.Prove(m,k,j,x,y)', '{:axiom} false',
                     'true; } } module Escape {', '// ignored\nfalse', '"text"']
        for expression in forbidden:
            self.rejects(['var z := {' + expression + '};',
                          'var z := m[k := ' + expression + '];',
                          'var z := (map q | q in m :: ' + expression + ');'])

    def test_fresh_binders_do_not_escape_through_block_boundary(self):
        self.body('if k in {j} { assert k == j; } else { assert k != j; }')
        self.rejects(['if k in {j} { assert true; } } assume false;',
                      'var z := (map q | q in m :: m[q]); } lemma Escape() {}',
                      'assert true; } ensures true {'])

    def test_new_constructs_keep_complexity_bounds(self):
        self.rejects(['assert ' + '{' * 35 + 'k' + '}' * 35 + ' == {};',
                      'var z := ' + ''.join('(map b%d | b%d in m :: ' % (i, i) for i in range(35)) + '0' + ')' * 35 + ';',
                      'var z := m' + '[k := x]' * 33 + ';',
                      'var z := {' + ','.join('k' for _ in range(4100)) + '};'])

    def test_admission_does_not_claim_types_finiteness_or_truth(self):
        for source in ['assert false;', 'var z := (map q | true :: q);',
                       'var z := 0[k := x];', 'var z := {m,k};']:
            self.body(source)

    def test_old_guard_is_unchanged(self):
        expected = '5cb8995fe7108538e9d7debb561dc75c38c895d5dd739a7bcf4673aaeeec1102'
        for path in [EXPANSION / 'protocol/body_guard.py', PILOT / 'frozen-001/guard/body_guard.py']:
            self.assertEqual(digest(path.read_text()), expected)


if __name__ == '__main__':
    unittest.main(verbosity=2)
