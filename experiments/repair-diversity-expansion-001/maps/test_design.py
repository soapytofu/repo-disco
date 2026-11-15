"""Offline structural and finite-map checks. No Dafny or model execution."""
import importlib.util
import itertools
import json
from pathlib import Path
import tempfile
import unittest

ROOT = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location('override_fixture_build', ROOT/'build.py')
build = importlib.util.module_from_spec(spec)
spec.loader.exec_module(build)


def override(m,n):
    return {**m, **n}


def restrict(m, keep):
    return {k:v for k,v in m.items() if k in keep}


class Design(unittest.TestCase):
    def test_algebra_on_overlapping_disjoint_and_empty_maps(self):
        maps = [{i:v for i,v in enumerate(values) if v is not None}
                for values in itertools.product((None,-1,2), repeat=3)]
        keeps = [set(i for i,on in enumerate(bits) if on)
                 for bits in itertools.product((False,True), repeat=3)]
        overlaps, conflicts, disjoint, empty = 0,0,0,0
        for m,n,keep in itertools.product(maps,maps,keeps):
            self.assertEqual(restrict(override(m,n),keep), override(restrict(m,keep),restrict(n,keep)))
            keys = set(m) & set(n)
            overlaps += bool(keys)
            conflicts += any(m[k] != n[k] for k in keys)
            disjoint += not bool(keys)
            empty += not bool(m) or not bool(n)
        self.assertTrue(min(overlaps,conflicts,disjoint,empty)>0)

    def test_fault_counterexample_and_priority_is_semantic(self):
        m,n,keep = {0:1},{0:2},{0}
        self.assertEqual(override(m,n)[0],2)
        self.assertNotEqual(override(m,n)[0],m[0])
        self.assertNotEqual(override(m,n), override(n,m))
        self.assertTrue(set(m) & set(n))
        self.assertEqual(restrict(override(m,n),keep),{0:2})
        # Keeping only keys exclusive to either map also remains in the theorem domain.
        self.assertEqual(restrict(override({0:4},{1:7}),{0,1}), {0:4,1:7})

    def test_shared_separate_clients_and_protected_sources(self):
        shared, separate = build.sources('shared','reference'),build.sources('separate','reference')
        for n in ('Kernel.dfy','Domains.dfy','Values.dfy','Api.dfy','ClientA.dfy','ClientB.dfy','All.dfy'):
            self.assertEqual(shared[n],separate[n])
        self.assertIn('H.Prove(n,m,keep);',shared['ClientB.dfy'])
        self.assertIn('K.Override(n,m)',shared['ClientB.dfy'])
        self.assertIn('K.Override(K.Restrict(n,keep),K.Restrict(m,keep))',shared['ClientB.dfy'])
        self.assertNotIn('requires',shared['HelperA.dfy'])
        for sharing in ('shared','separate'):
            template=build.sources(sharing,'empty')
            editable=['HelperA.dfy']+(['HelperB.dfy'] if sharing=='separate' else [])
            for variant in build.VARIANTS:
                for n, source in build.sources(sharing,variant).items():
                    self.assertEqual(source.count('{'),source.count('}'))
                    self.assertNotRegex(source,r'\b(assume|axiom)\b|verify\s+false')
                    if n in editable:
                        self.assertEqual(build.body_boundary(template[n])['protected_sha256'],build.body_boundary(source)['protected_sha256'])
                        span=build.body_boundary(source)
                        self.assertEqual(source.encode()[span['start']:span['end']].decode(),build.VARIANTS[variant])
                    else:
                        self.assertEqual(source,template[n])

    def test_value_prerequisites_and_hidden_export(self):
        self.assertIn('requires q in m || q in n',build.VALUES)
        self.assertIn('requires q in m && q in keep',build.VALUES)
        self.assertIn('if q in n then n[q] else m[q]',build.VALUES)
        self.assertIn('requires left.Keys == right.Keys',build.API)
        self.assertNotIn('ObserveOverride',build.API.split('export Public provides')[1].split('\n')[0])
        self.assertIn('import A = Api`Public',build.sources('shared','reference')['HelperA.dfy'])
        self.assertIn('A.ObserveOverride',build.VARIANTS['hidden_shortcut'])
        self.assertNotIn('lemma Prove',build.API+build.DOMAINS+build.VALUES)
        self.assertNotIn('Separate',build.KERNEL)

    def test_deterministic_generation_and_manifest(self):
        with tempfile.TemporaryDirectory() as temp:
            out=Path(temp)
            summary=build.generate(out)
            self.assertEqual((summary['tasks'],summary['checks'],summary['source_files']),(2,20,198))
            self.assertEqual((summary['expected_success'],summary['expected_proof_failure'],summary['expected_resolution_failure']),(4,14,2))
            manifest=json.loads((out/'manifest.json').read_text())
            for path,digest in manifest['source_files'].items():
                self.assertEqual(build.sha((out/path).read_bytes()),digest)
            before=(out/'manifest.json').read_bytes()
            build.generate(out)
            self.assertEqual(before,(out/'manifest.json').read_bytes())
            for task in json.loads((out/'tasks.json').read_text()):
                self.assertTrue(task['development_only'])
                self.assertFalse(task['held_out'])
                self.assertNotEqual(task['plan_id'],'D4-M2')


if __name__=='__main__':
    unittest.main()
