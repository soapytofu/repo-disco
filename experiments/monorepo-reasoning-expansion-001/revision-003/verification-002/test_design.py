"""Non-paid construction invariants; these do not substitute for Dafny."""
import collections
import json
from pathlib import Path
import re
import tempfile
import unittest
import build

ROOT = Path(__file__).resolve().parent


def body_parts(source):
    start = source.index('  {\n', source.index('  lemma')) + 4
    end = source.rindex('  }\n}')
    return source[:start], source[start:end], source[end:]


class DesignTests(unittest.TestCase):
    def test_regeneration_and_balance(self):
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory)
            tasks, checks = build.build(target)
            self.assertEqual(tasks, json.loads((ROOT/'tasks.json').read_text()))
            self.assertEqual(checks, json.loads((ROOT/'checks.json').read_text()))
            self.assertEqual(len(tasks), 24)
            self.assertEqual(len(checks), 164)
            self.assertEqual(collections.Counter(t['family'] for t in tasks),
                             {'conditional': 8, 'sequence': 8, 'map': 8})
            for p in (target/'fixtures').rglob('*.dfy'):
                self.assertEqual(p.read_bytes(), (ROOT/p.relative_to(target)).read_bytes())

    def test_matched_providers_clients_and_contracts(self):
        immutable = ['Kernel.dfy','Ops1.dfy','Ops2.dfy','Api.dfy',
                     'ClientA.dfy','ClientB.dfy','All.dfy']
        for family in build.families():
            baseline = build.snapshot(family,'shallow','shared','reference')
            for depth in ['shallow','deep']:
                for sharing in ['shared','separate']:
                    files = build.snapshot(family,depth,sharing,'reference')
                    for name in immutable:
                        self.assertEqual(files[name], baseline[name])
                    for name in ['HelperA.dfy','HelperB.dfy']:
                        self.assertIn(build.declaration(family), files[name])
                        self.assertIn('{:induction false}', files[name])

    def test_controls_change_only_declared_bodies(self):
        for family in build.families():
            for depth in ['shallow','deep']:
                for sharing in ['shared','separate']:
                    reference = build.snapshot(family,depth,sharing,'reference')
                    for variant in ['empty', *family['mutations'], 'only_a','only_b','hidden_shortcut']:
                        candidate = build.snapshot(family,depth,sharing,variant)
                        for name, source in reference.items():
                            if name.startswith('Helper'):
                                a,b,c=body_parts(source); x,y,z=body_parts(candidate[name])
                                self.assertEqual((a,c),(x,z))
                                if sharing=='shared' and name=='HelperB.dfy':
                                    self.assertEqual(source,candidate[name])
                            else:
                                self.assertEqual(source,candidate[name])

    def test_reference_has_no_trust_bypass_and_only_self_recursion(self):
        for family in build.families():
            for depth in ['shallow','deep']:
                files=build.snapshot(family,depth,'separate','reference')
                a=body_parts(files['HelperA.dfy'])[1]
                b=body_parts(files['HelperB.dfy'])[1]
                self.assertEqual(a,b)
                self.assertFalse(re.search(r'\b(assume|reveal|axiom|expect)\b|\{:', a))
                self.assertNotIn('HelperB', files['HelperA.dfy'])
                self.assertNotIn('HelperA', files['HelperB.dfy'])
                if family['family']=='sequence':
                    self.assertIn('Prove(s[1..]',a)
                    self.assertIn('decreases |s|', files['HelperA.dfy'])

    def test_weakened_contract_is_explicit_negative_only(self):
        for family in build.families():
            ref=build.snapshot(family,'deep','shared','reference')
            weak=build.snapshot(family,'deep','shared','weaken_contract')
            self.assertEqual(weak['HelperA.dfy'],ref['HelperA.dfy'].replace(
                build.declaration(family),build.declaration(family,True)))
            for name in ref:
                if name!='HelperA.dfy': self.assertEqual(weak[name],ref[name])

    def test_expected_categories_and_exact_source_inventory(self):
        checks=json.loads((ROOT/'checks.json').read_text())
        self.assertEqual(collections.Counter(c['expected'] for c in checks),
            {'success':24,'proof_failure':120,'termination_failure':8,'resolution_failure':12})
        for check in checks:
            files={p.name:p.read_text() for p in (ROOT/check['path']).glob('*.dfy')}
            self.assertEqual(build.hashes(files),check['source_sha256'])
            self.assertEqual(len(files),9)


if __name__=='__main__': unittest.main(verbosity=2)
