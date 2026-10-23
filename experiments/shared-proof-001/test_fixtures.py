"""Check ablation isolation and independently fixed expected outcomes."""
from pathlib import Path
import json
import unittest

ROOT = Path(__file__).resolve().parent


class FixtureTests(unittest.TestCase):
    def test_only_intended_bytes_change(self):
        ref = {p.name:p.read_text() for p in (ROOT/'fixtures/reference').glob('*.dfy')}
        for variant in ['missing_a','missing_b','missing_both','weakened_shared_contract']:
            expected = dict(ref)
            for client,variants in [('ClientA.dfy',['missing_a','missing_both']),('ClientB.dfy',['missing_b','missing_both'])]:
                if variant in variants:
                    expected[client] = expected[client].replace('    S.LengthConcat(s, t);\n','')
            if variant == 'weakened_shared_contract':
                expected['SequenceFacts.dfy'] = expected['SequenceFacts.dfy'].replace('ensures Size(s + t) == Size(s) + Size(t)','ensures true')
            actual = {p.name:p.read_text() for p in (ROOT/'fixtures'/variant).glob('*.dfy')}
            self.assertEqual(actual,expected)

    def test_check_matrix_and_no_model_budget(self):
        checks = json.loads((ROOT/'checks.json').read_text())
        self.assertEqual(len(checks),16)
        matrix = {(r['variant'],r['entry']):r['expected_exit'] for r in checks}
        self.assertEqual(len(matrix),16)
        self.assertEqual([matrix[('missing_a',e)] for e in ['ClientA.dfy','ClientB.dfy','All.dfy']],[4,0,4])
        self.assertEqual([matrix[('missing_b',e)] for e in ['ClientA.dfy','ClientB.dfy','All.dfy']],[0,4,4])
        self.assertEqual(matrix[('weakened_shared_contract','SequenceFacts.dfy')],0)
        self.assertEqual(json.loads((ROOT/'task.json').read_text())['model_calls'],0)


if __name__ == '__main__':
    unittest.main()
