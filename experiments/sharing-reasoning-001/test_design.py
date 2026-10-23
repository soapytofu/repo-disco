import json
from pathlib import Path
import unittest
P=Path(__file__).resolve().parent
class DesignTests(unittest.TestCase):
    def test_reference_matching_and_scope(self):
        a=P/'fixtures/shared_reference';b=P/'fixtures/separate_reference'
        for name in ['Facts.dfy','ClientA.dfy','All.dfy']:self.assertEqual((a/name).read_bytes(),(b/name).read_bytes())
        x=(a/'ClientB.dfy').read_text();y=(b/'ClientB.dfy').read_text()
        self.assertEqual(x.replace('ViewA','ViewB').replace('ConcatA','ConcatB'),y)
        self.assertEqual(len(x),len(y))
        for f in a.glob('Client*.dfy'):
            s=f.read_text();self.assertEqual(s.count('F.ConcatA('),2);self.assertEqual(s.count('F.Finish('),1)
    def test_mutations_protect_clients_contracts_and_providers(self):
        for condition in ['shared','separate']:
            root=P/'fixtures'/f'{condition}_reference'
            for d in (P/'fixtures').glob(condition+'_*'):
                for name in ['ClientA.dfy','ClientB.dfy']:
                    ref=(root/name).read_text();candidate=(d/name).read_text()
                    self.assertEqual(ref.split('  {\n')[0],candidate.split('  {\n')[0])
                if 'weaken_' not in d.name:self.assertEqual((root/'Facts.dfy').read_bytes(),(d/'Facts.dfy').read_bytes())
    def test_check_categories(self):
        rows=json.loads((P/'checks.json').read_text());self.assertEqual(len(rows),46)
        self.assertEqual(len({(r['variant'],r['entry']) for r in rows}),46)
        hidden=[r for r in rows if 'hidden_helper' in r['variant']]
        self.assertEqual(len(hidden),4);self.assertTrue(all(r['expected_exit']==2 for r in hidden))
        reasoning=[r for r in rows if any(s in r['variant'] for s in ['omit_','finish_first','wrong_arguments'])]
        self.assertEqual(len(reasoning),20);self.assertTrue(all(r['expected_exit']==4 for r in reasoning))
if __name__=='__main__':unittest.main()
