import importlib.util
from pathlib import Path
import unittest

spec = importlib.util.spec_from_file_location('usage_metrics', Path(__file__).resolve().parents[1] / 'scripts/proof_usage_metrics.py')
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


def row(sequence, task='task', calls=None, outcome='SUCCESS'):
    return dict(sequence=sequence, task=task, condition='full_context', outcome=outcome,
                called_symbols=calls if calls is not None else ['A.Lemma', 'B.Finish'])


class ProofUsageTests(unittest.TestCase):
    def test_repetitions_do_not_inflate_client_or_reuse_count(self):
        mapping = {'imports': {'Client': {'A': 'ProviderA', 'B': 'ProviderB'}}}
        result = module.measure([row(1), row(2), row(3, outcome='PROOF_FAILURE')], {'task': mapping})
        self.assertEqual(result['successful_trials'], 2)
        self.assertEqual(result['distinct_client_targets'], 1)
        self.assertEqual(result['lemmas_shared_by_multiple_targets'], 0)
        self.assertEqual([x['client_target_count'] for x in result['lemma_usage']], [1, 1])
        self.assertEqual(result['trial_calls'][0]['distinct_provider_count'], 2)

    def test_symbols_are_scoped_to_repository(self):
        mapping = {'imports': {'Client': {'A': 'ProviderA', 'B': 'ProviderB'}}}
        result = module.measure([row(1, 'one'), row(2, 'two')], {'one': mapping, 'two': mapping})
        self.assertEqual(len(result['lemma_usage']), 4)
        self.assertEqual(result['lemmas_shared_by_multiple_targets'], 0)

    def test_duplicate_trials_and_unknown_aliases_rejected(self):
        maps = {'task': {'imports': {'Client': {'A': 'ProviderA', 'B': 'ProviderB'}}}}
        for rows in ([row(1), row(1)], [row(1, calls=['X.Guess'])], [row(1, 'unknown')]):
            with self.assertRaises(ValueError):
                module.measure(rows, maps)



class MultiClientTests(unittest.TestCase):
    def fixture(self):
        maps={'repo':{'targets':{'A':{'F':'Facts'},'B':{'F':'Facts'}},'symbols':['Facts.L']}}
        rows=[dict(repository='repo',trial=i,target=t,outcome='SUCCESS',called_symbols=['F.L'],evidence='reviewed/result.json') for i in [1,2] for t in ['A','B']]
        abl=[dict(repository='repo',symbol='Facts.L',target=t,baseline_exit=0,ablated_exit=4,evidence='reviewed/ablation.json') for t in ['A','B']]
        return maps,rows,abl
    def test_distinct_targets_and_dependence(self):
        maps,rows,abl=self.fixture();r=module.measure_multiclient(rows,maps,abl)
        self.assertEqual(r['distinct_successful_targets'],2);self.assertEqual(r['observed_usage'][0]['target_count'],2)
        self.assertEqual(r['ablation_dependence'][0]['affected_count'],2);self.assertIsNone(r['proof_prerequisite_depth'])
    def test_unmeasured_is_not_zero_and_repository_scope(self):
        maps,rows,abl=self.fixture();maps['other']=maps['repo'];rows += [dict(x,repository='other') for x in rows]
        result=module.measure_multiclient(rows,maps);self.assertEqual(len(result['observed_usage']),2);self.assertIsNone(result['ablation_dependence'])
    def test_missing_duplicate_conflicting_or_nonproof_evidence(self):
        maps,rows,abl=self.fixture()
        for bad_rows,bad_abl in [(rows+rows[:1],abl),(rows[:-1],abl),(rows,abl[:-1]),(rows,abl+abl[:1]),(rows,[dict(abl[0],ablated_exit=2),abl[1]]),(rows,[dict(abl[0],baseline_exit=4),abl[1]]),(rows,[dict(abl[0],evidence=''),abl[1]])]:
            with self.assertRaises(ValueError):module.measure_multiclient(bad_rows,maps,bad_abl)
    def test_missing_observation_evidence_and_unknown_definitions(self):
        maps,rows,abl=self.fixture()
        for change in [dict(evidence=''),dict(called_symbols=['F.Unknown']),dict(called_symbols=['X.L']),dict(target='Unknown')]:
            with self.assertRaises(ValueError):module.measure_multiclient([dict(rows[0],**change)]+rows[1:],maps,abl)

    def test_failed_trials_not_counted_as_successful_reuse(self):
        maps,rows,_=self.fixture();rows=[dict(r,outcome='PROOF_FAILURE') for r in rows]
        self.assertEqual(module.measure_multiclient(rows,maps)['observed_usage'],[])

if __name__ == '__main__':
    unittest.main()
