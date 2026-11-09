"""Source and scope regression checks; no live verifier or model."""
import importlib.util,json,unittest
from pathlib import Path
import build
ROOT=Path(__file__).resolve().parent

class RevisionTests(unittest.TestCase):
    def test_unchanged_other_instances(self):
        # Parent generator is copied into this runtime for exact, standalone comparison.
        spec=importlib.util.spec_from_file_location('original_build',ROOT/'original-build.py')
        old=importlib.util.module_from_spec(spec);spec.loader.exec_module(old)
        for ins,d in old.DEFS.items():
            for depth in ['shallow','deep']:
                for sharing in ['shared','separate']:
                    for variant in d['variants']:
                        a=old.sources(ins,depth,sharing,variant);b=build.sources(ins,depth,sharing,variant)
                        if ins!='map_swap':self.assertEqual(a,b)
                        else:
                            for n in ['ClientA.dfy','ClientB.dfy','All.dfy','Api.dfy']:self.assertEqual(a[n],b[n])
                            self.assertEqual(old.MS,build.MS)
                            if depth=='shallow' and variant!='hidden_shortcut':
                                self.assertEqual(a['HelperA.dfy'],b['HelperA.dfy'])
                                self.assertEqual(a['HelperB.dfy'],b['HelperB.dfy'])
    def test_certificate_is_required_and_negated(self):
        self.assertIn('requires K.Domain(m,k,j)',build.MO2)
        self.assertIn('export Public provides Swap, Domain',build.MK)
        self.assertNotIn('export Public reveals',build.MK)
        ref=build.swap('deep','reference');bad=build.swap('deep','missing_certificate')
        self.assertEqual(bad,ref.replace('O1.Certify(once,k,j);',''))
        for statement in ['O1.Certify(m,k,j);','O2.SwapKeys(m,k,j);','O1.Certify(once,k,j);','O2.SwapKeys(once,k,j);','A.Equal(m,twice);']:
            self.assertIn(statement,ref)
        self.assertLess(ref.index('O2.SwapKeys(m,k,j);'),ref.index('O1.Certify(once,k,j);'))
        checks=json.loads((ROOT/'checks.json').read_text())
        added=[c for c in checks if c['variant']=='missing_certificate']
        self.assertEqual(len(added),2)
        self.assertTrue(all('deep' in c['task_id'] and c['expected']=='proof_failure' for c in added))

if __name__=='__main__':unittest.main(verbosity=2)
