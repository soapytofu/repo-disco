"""Saved-evidence and adversarial metric checks; no verifier/model execution."""
import copy
import csv
import io
import json
from pathlib import Path
import unittest
from review_targets import scores,HEADER,RESTRICTION_EXPECTED

ROOT=Path(__file__).resolve().parent
CASES=json.loads((ROOT/'cases.json').read_text())


def rows(case):
    result=json.loads((ROOT/'verification-001'/(case['case_id']+'.json')).read_text())
    return list(csv.DictReader(io.StringIO(next(iter(result['csv'].values())))))


def encode(rs):
    f=io.StringIO();w=csv.DictWriter(f,fieldnames=HEADER);w.writeheader();w.writerows(rs)
    return {'sample.csv':f.getvalue()}


class Tests(unittest.TestCase):
    def test_restriction_reference_uses_its_exact_declaration_inventory(self):
        case=json.loads((ROOT/'restriction-001/cases.json').read_text())[0]
        r=json.loads((ROOT/'restriction-001/verification-001/restriction_reference.json').read_text())
        result=scores(r['csv'],case,RESTRICTION_EXPECTED)
        self.assertEqual(result['logger_rows'],20)
        self.assertEqual(result['supplied_clients_closed']['passed'],2)
        with self.assertRaises(ValueError):scores(r['csv'],case)

    def test_all_four_observed_local_and_dependency_closed_outcomes(self):
        for case in CASES:
            s=scores(encode(rows(case)),case)
            self.assertEqual(s['local_targets'],case['expected_local'])
            self.assertEqual(s['supplied_clients_local'],dict(passed=2,total=2))
            expected=2 if case['case_id']=='shared_reference' else 0 if case['case_id']=='shared_empty' else 1
            self.assertEqual(s['supplied_clients_closed']['passed'],expected)

    def test_missing_duplicate_unknown_and_unresolved_rows_rejected(self):
        case=CASES[0];rs=rows(case)
        for bad in (rs[1:],rs+[rs[0]],[]):
            with self.assertRaises(ValueError):scores(encode(bad),case)
        for field,value in [(HEADER[0],'Impostor.Prove (correctness)'),(HEADER[1],'Inconclusive'),('RandomSeed','1')]:
            bad=copy.deepcopy(rs);bad[0][field]=value
            with self.assertRaises(ValueError):scores(encode(bad),case)

    def test_batches_do_not_inflate_target_count_and_failure_is_preserved(self):
        case=CASES[0];rs=rows(case);i=next(i for i,r in enumerate(rs) if r[HEADER[0]]=='HelperA.Prove (correctness)')
        row=rs.pop(i)
        rs.extend([dict(row,**{HEADER[0]:row[HEADER[0]]+' (assertion batch 1)'}),
                   dict(row,**{HEADER[0]:row[HEADER[0]]+' (assertion batch 2)',HEADER[1]:'Failed'})])
        s=scores(encode(rs),case)
        self.assertEqual(s['editable_local'],dict(passed=0,total=1))
        self.assertEqual(s['supplied_clients_closed']['passed'],0)
        rs[-1][HEADER[0]]=row[HEADER[0]]+' (assertion batch 3)'
        with self.assertRaises(ValueError):scores(encode(rs),case)

    def test_unknown_dependency_and_cycle_rejected(self):
        for graph in ({'HelperA.Prove':['Missing.Prove']},{'HelperA.Prove':['HelperB.Prove']}):
            case=copy.deepcopy(CASES[0]);case['target_dependencies'].update(graph)
            with self.assertRaises(ValueError):scores(encode(rows(CASES[0])),case)

    def test_failed_supplied_provider_blocks_closed_credit(self):
        case=CASES[0];rs=rows(case)
        next(r for r in rs if r[HEADER[0]]=='Ops1.Certify (correctness)')[HEADER[1]]='Failed'
        s=scores(encode(rs),case)
        self.assertEqual(s['supplied_clients_local']['passed'],2)
        self.assertEqual(s['supplied_clients_closed']['passed'],0)
        self.assertFalse(s['supplied_providers_verified'])


if __name__=='__main__':unittest.main(verbosity=2)
