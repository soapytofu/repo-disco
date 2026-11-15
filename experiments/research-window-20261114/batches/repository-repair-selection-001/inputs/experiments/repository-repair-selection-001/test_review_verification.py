"""Offline tests for study-specific closure, unit aggregation and alias routing."""
from pathlib import Path
import json
import tempfile
import unittest
import review_verification as review


class ReviewTests(unittest.TestCase):
    def test_declared_closure_distinguishes_local_and_dependency_closed_success(self):
        graph=review.scope()['declared_target_dependencies']
        all_good={name:True for name in review.TARGETS}
        self.assertEqual(review.dependency_closed(all_good,graph),all_good)
        a_failed=dict(all_good,**{'HelperA.Prove':False})
        self.assertTrue(a_failed['ClientA.Target'])
        self.assertEqual(review.dependency_closed(a_failed,graph),{name:False for name in review.TARGETS})
        b_failed=dict(all_good,**{'HelperB.Prove':False})
        self.assertEqual(review.dependency_closed(b_failed,graph),{
            'HelperA.Prove':True,'HelperB.Prove':False,'ClientA.Target':False,'ClientB.Target':False})
        unknown=dict(all_good,**{'HelperA.Prove':None})
        self.assertEqual(review.dependency_closed(unknown,graph),{name:None for name in review.TARGETS})
        cycle={name:list(parents) for name,parents in graph.items()};cycle['HelperA.Prove']=['HelperB.Prove']
        with self.assertRaisesRegex(AssertionError,'Cyclic'):
            review.dependency_closed(all_good,cycle)

    def test_all_named_units_count_and_missing_units_remain_unknown(self):
        text=('TestResult.DisplayName,TestResult.Outcome\n'
              'HelperA.Prove (correctness),Passed\n'
              'HelperA.Prove (well-formedness),Failed\n'
              'HelperB.Prove (correctness),Passed\n'
              'ClientA.Target (correctness),Passed\n')
        units=review.csv_units({'csv':{'results.csv':text}})
        self.assertEqual(review.local_targets(units),{
          'HelperA.Prove':False,'HelperB.Prove':True,'ClientA.Target':True,'ClientB.Target':None})
        with self.assertRaisesRegex(AssertionError,'Duplicate'):
            review.csv_units({'csv':{'a.csv':text,'b.csv':text}})
        with self.assertRaisesRegex(AssertionError,'Unrecognized'):
            review.csv_units({'csv':{'a.csv':text.replace('Failed','Skipped')}})

    def test_frozen_control_expectations_bind_graph_without_reading_results(self):
        config=review.scope()
        counts={}
        for group in ('witness','maps'):
            root=review.ROOT/group
            self.assertEqual(review.sha((root/'runtime-manifest.json').read_bytes()),config['groups'][group]['runtime_manifest_sha256'])
            cases=review.load(root/'cases.json');counts[group]=len(cases)
            for case in cases:
                expected=review.expected_targets(group,case,config)
                if case['expected']=='resolution_failure':
                    self.assertIsNone(expected['expected_local_targets'])
                elif case['expected']=='success':
                    self.assertTrue(all(expected['expected_dependency_closed_targets'].values()))
                elif case['variant']=='faulty':
                    self.assertEqual(len(expected['expected_failed_targets']),1)
                    self.assertFalse(expected['expected_dependency_closed_targets']['ClientA.Target'])
                    self.assertFalse(expected['expected_dependency_closed_targets']['ClientB.Target'])
        self.assertEqual(counts,dict(witness=24,maps=21))

    def test_aliases_bind_exact_canonical_sources_and_evidence_not_new_trials(self):
        root=review.ROOT/'maps';cases=review.load(root/'cases.json')
        rows=[dict(case_id=case['case_id'],evidence_sha256=str(i).zfill(64),strict_actual=case['expected'],
                   local_targets=None,dependency_closed_targets=None,matched=True) for i,case in enumerate(cases)]
        aliases=review.evidence_aliases(root/'control-aliases.json',cases,rows)
        self.assertEqual(len(aliases),4);self.assertEqual(len(rows),21)
        for alias in aliases:
            self.assertFalse(alias['new_verifier_call']);self.assertFalse(alias['independent_observation'])
            row=next(row for row in rows if row['case_id']==alias['evidence_alias_of'])
            self.assertEqual(alias['canonical_evidence_sha256'],row['evidence_sha256'])
        bad=review.load(root/'control-aliases.json')
        bad[0]['source_sha256']['HelperA.dfy']='0'*64
        with tempfile.TemporaryDirectory() as folder:
            path=Path(folder)/'bad-alias.json';path.write_text(json.dumps(bad))
            with self.assertRaises(AssertionError):review.evidence_aliases(path,cases,rows)

    def test_only_new_reports_are_routed_outside_group(self):
        original=Path('/immutable/group');destination=Path('/new/reports')
        paths=review.ReportPaths(original,destination)
        for name in ('results-review.json','verification-001-sha256.json'):
            self.assertEqual(paths/name,destination/name)
        for name in ('templates','fixtures','tasks.json','verification-001'):
            self.assertEqual(paths/name,original/name)


if __name__=='__main__':
    unittest.main(verbosity=2)
