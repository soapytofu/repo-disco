"""Offline construction/finite mathematics checks; these do not run Dafny."""
import importlib.util
import itertools
import json
from pathlib import Path
import re
import tempfile
import unittest

ROOT = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location('gap_fixture_build', ROOT / 'build.py')
build = importlib.util.module_from_spec(spec)
spec.loader.exec_module(build)


def feasible(a, b, c, d, gap):
    return gap > 0 and a <= b and c <= d and a + gap <= d and c <= b + gap


def candidate(a, b, c, d, gap, u, v):
    return a <= u <= b and c <= v <= d and gap > 0 and v == u + gap


class Design(unittest.TestCase):
    def test_exact_feasibility_and_both_constructions(self):
        valid, invalid = 0, 0
        for a, b, c, d, gap in itertools.product(range(-2, 3), range(-2, 3), range(-2, 3), range(-2, 3), range(-1, 4)):
            actual = any(candidate(a, b, c, d, gap, u, v)
                         for u in range(a, b + 1) for v in range(c, d + 1))
            self.assertEqual(feasible(a, b, c, d, gap), actual)
            if actual:
                valid += 1
                u = c-gap if a+gap < c else a
                self.assertTrue(candidate(a, b, c, d, gap, u, u+gap))
                v = b+gap if b+gap <= d else d
                self.assertTrue(candidate(a, b, c, d, gap, v-gap, v))
            else:
                invalid += 1
        self.assertGreater(valid, 100)
        self.assertGreater(invalid, 100)

    def test_counterexamples_and_distinct_feasible_shapes(self):
        examples = [(0,5,4,8,2,0,2), (0,5,1,4,2,5,7), (0,5,1,4,2,0,1)]
        for a,b,c,d,gap,u,v in examples:
            self.assertTrue(feasible(a,b,c,d,gap))
            self.assertFalse(candidate(a,b,c,d,gap,u,v))
        # Feasibility includes disjoint original intervals and a single exact pair.
        self.assertTrue(feasible(0,1,5,6,5))
        self.assertTrue(candidate(0,0,3,3,3,0,3))
        # Positive distance cannot be replaced by mere overlap or by gap-1.
        self.assertFalse(feasible(0,0,0,0,1))

    def test_guarded_bodies_and_identical_client_contracts(self):
        shared = build.sources('shared', 'reference')
        separate = build.sources('separate', 'reference')
        for n in ('Kernel.dfy','Ops.dfy','Api.dfy','ClientA.dfy','ClientB.dfy','All.dfy'):
            self.assertEqual(shared[n], separate[n])
        self.assertIn('H.Prove(a,b,c,d,gap);', shared['HelperB.dfy'])
        self.assertNotIn('import H', separate['HelperB.dfy'])
        for sharing in ('shared', 'separate'):
            template = build.sources(sharing, 'empty')
            editable = ['HelperA.dfy'] + (['HelperB.dfy'] if sharing == 'separate' else [])
            for variant in build.VARIANTS:
                files = build.sources(sharing, variant)
                for n, source in files.items():
                    self.assertEqual(source.count('{'), source.count('}'))
                    self.assertNotRegex(source, r'\b(assume|axiom)\b|verify\s+false')
                    if n in editable:
                        self.assertEqual(build.body_boundary(template[n])['protected_sha256'],
                                         build.body_boundary(source)['protected_sha256'])
                        span = build.body_boundary(source)
                        self.assertEqual(source.encode()[span['start']:span['end']].decode(), build.VARIANTS[variant])
                    else:
                        self.assertEqual(source, template[n])

    def test_named_exports_and_no_final_gold_shortcut(self):
        helper = build.sources('shared','reference')['HelperA.dfy']
        self.assertIn('import K = Kernel`Public', helper)
        self.assertIn('import O = Ops`Public', helper)
        self.assertNotIn('HiddenBounds', build.OPS.split('export Public provides')[1].split('\n')[0])
        self.assertIn('O.HiddenBounds', build.VARIANTS['hidden_shortcut'])
        # Only Finish packages already-proved certificates; no provider solves witness choice.
        self.assertIn('requires K.Left(a,b,u) && K.Right(c,d,v) && K.Offset(gap,u,v)', build.API)
        self.assertNotIn('lemma Prove', build.API + build.OPS)

    def test_generation_manifest_and_diagnostics(self):
        with tempfile.TemporaryDirectory() as temp:
            out = Path(temp)
            summary = build.generate(out)
            self.assertEqual((summary['tasks'],summary['checks'],summary['source_files']), (2,20,176))
            self.assertEqual((summary['expected_success'],summary['expected_proof_failure'],summary['expected_resolution_failure']), (4,14,2))
            manifest = json.loads((out/'manifest.json').read_text())
            for path, expected in manifest['source_files'].items():
                self.assertEqual(build.sha((out/path).read_bytes()), expected)
            cases = json.loads((out/'cases.json').read_text())
            self.assertTrue(all(c['expected']=='resolution_failure' for c in cases if c['variant']=='hidden_shortcut'))
            self.assertTrue(all(c['expected']=='proof_failure' for c in cases if c['variant'] in ('faulty','empty')))
            first = (out/'manifest.json').read_bytes()
            build.generate(out)
            self.assertEqual(first, (out/'manifest.json').read_bytes())
            for task in json.loads((out/'tasks.json').read_text()):
                self.assertTrue(task['development_only'])
                self.assertFalse(task['held_out'])
                self.assertNotEqual(task['plan_id'], 'D3-M1')


if __name__ == '__main__':
    unittest.main()
