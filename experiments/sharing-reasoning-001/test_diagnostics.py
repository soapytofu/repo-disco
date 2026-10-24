import json
from pathlib import Path
import unittest
from run_verification import matches_expected
P=Path(__file__).resolve().parent
class DiagnosticTests(unittest.TestCase):
    def test_all_archived_checks(self):
        rows=json.loads((P/'verification-001/results.json').read_text())
        self.assertEqual(len(rows),46)
        for row in rows:
            with self.subTest(variant=row['variant'],entry=row['entry']):
                stdout=(P/'verification-001/logs'/row['variant']/Path(row['entry']).stem/'stdout.txt').read_text()
                self.assertTrue(matches_expected(row['exit_code'],row['expected_exit'],stdout))
    def test_unrelated_errors_are_not_boundary_successes(self):
        for code,text in [(2,'syntax error'),(2,'unresolved identifier: SomethingElse'),(4,'unresolved identifier: ConcatA')]:
            self.assertFalse(matches_expected(code,2,text))
    def test_proof_errors_and_success_are_separate(self):
        self.assertTrue(matches_expected(4,4,'2 verified, 1 error'))
        self.assertFalse(matches_expected(2,4,'2 verified, 1 error'))
        self.assertFalse(matches_expected(0,0,'2 verified, 1 error'))
if __name__=='__main__':unittest.main()
