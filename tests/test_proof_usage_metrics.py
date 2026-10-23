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


if __name__ == '__main__':
    unittest.main()
