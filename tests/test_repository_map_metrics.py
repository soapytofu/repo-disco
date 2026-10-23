import importlib.util
import json
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('map_metrics', ROOT / 'scripts/repository_map_metrics.py')
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
measure = module.measure


def graph(bindings):
    return {'modules': list(bindings), 'imports': bindings}


class MapMetricsTests(unittest.TestCase):
    def test_diamond_longest_path_and_redundant_alias(self):
        result = measure(graph({'Client': {'a': 'A', 'b': 'B', 'again': 'A'},
                                'A': {'c': 'C'}, 'B': {'c': 'C'}, 'C': {}, 'Unused': {}}), 'Client')
        self.assertEqual(result['root_import_depth'], 2)
        self.assertEqual(result['distinct_import_edge_count'], 4)
        self.assertEqual(result['alias_binding_count'], 5)
        self.assertEqual(result['unreachable_modules'], ['Unused'])
        self.assertIsNone(result['proof_depth'])

    def test_cycles_including_unreachable_cycle_are_rejected(self):
        for bindings in ({'Client': {'self': 'Client'}},
                         {'Client': {}, 'A': {'b': 'B'}, 'B': {'a': 'A'}}):
            with self.assertRaisesRegex(ValueError, 'cycle'):
                measure(graph(bindings), 'Client')

    def test_malformed_maps_are_rejected(self):
        cases = [[], {}, {'modules': ['A', 'A'], 'imports': {'A': {}}},
                 {'modules': ['A'], 'imports': {}}, graph({'A': {'x': 'Missing'}}),
                 graph({'A': []}), graph({'A': {'': 'A'}}), graph({'A': {'x': []}})]
        for value in cases:
            with self.subTest(value=value), self.assertRaises(ValueError):
                measure(value, 'A')

    def test_unknown_root_rejected(self):
        with self.assertRaisesRegex(ValueError, 'root'):
            measure(graph({'A': {}}), 'Client')

    def test_isolated_module_has_zero_depth(self):
        self.assertEqual(measure(graph({'A': {}}), 'A')['root_import_depth'], 0)

    def test_current_pilot_maps(self):
        paths = sorted((ROOT / 'experiments/composition-pilot-001/tasks').glob('*/dependency-map.json'))
        self.assertEqual(len(paths), 3)
        for path in paths:
            with self.subTest(task=path.parent.name):
                result = measure(json.loads(path.read_text()), 'Client')
                self.assertEqual(result['module_count'], 3)
                self.assertEqual(result['root_import_depth'], 2)
                self.assertEqual(result['distinct_import_edge_count'], 3)
                self.assertEqual(result['unreachable_modules'], [])


if __name__ == '__main__':
    unittest.main()
