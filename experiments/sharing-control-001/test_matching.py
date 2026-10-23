from pathlib import Path
import json
import unittest
P=Path(__file__).resolve().parent

class MatchingTests(unittest.TestCase):
    def test_reference_conditions_differ_in_only_one_call_name(self):
        a=P/'fixtures/shared_reference';b=P/'fixtures/separate_reference'
        for name in ['SequenceFacts.dfy','ClientA.dfy','All.dfy']:
            self.assertEqual((a/name).read_bytes(),(b/name).read_bytes())
        x=(a/'ClientB.dfy').read_text();y=(b/'ClientB.dfy').read_text()
        self.assertEqual(len(x),len(y))
        self.assertEqual(x.replace('S.ConcatFactA(s, t);','S.ConcatFactB(s, t);'),y)

    def test_mutations_preserve_client_proofs_and_other_contract(self):
        for condition in ['shared','separate']:
            ref=P/'fixtures'/f'{condition}_reference'
            for mutation,lemma in [('weaken_a','ConcatFactA'),('weaken_b','ConcatFactB')]:
                folder=P/'fixtures'/f'{condition}_{mutation}'
                for name in ['ClientA.dfy','ClientB.dfy','All.dfy']:
                    self.assertEqual((ref/name).read_bytes(),(folder/name).read_bytes())
                old=f'lemma {lemma}(s: seq<int>, t: seq<int>)\n    ensures Size(s + t) == Size(s) + Size(t)'
                expected=(ref/'SequenceFacts.dfy').read_text().replace(old,f'lemma {lemma}(s: seq<int>, t: seq<int>)\n    ensures true')
                self.assertEqual((folder/'SequenceFacts.dfy').read_text(),expected)

    def test_matrix(self):
        checks=json.loads((P/'checks.json').read_text())
        self.assertEqual(len(checks),22)
        matrix={(x['variant'],x['entry']):x['expected_exit'] for x in checks}
        self.assertEqual(len(matrix),22)
        self.assertEqual([matrix[('shared_weaken_a',e)] for e in ['ClientA.dfy','ClientB.dfy']],[4,4])
        self.assertEqual([matrix[('separate_weaken_a',e)] for e in ['ClientA.dfy','ClientB.dfy']],[4,0])
        self.assertEqual([matrix[('separate_weaken_b',e)] for e in ['ClientA.dfy','ClientB.dfy']],[0,4])

if __name__=='__main__':unittest.main()
