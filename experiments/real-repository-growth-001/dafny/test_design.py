"""Finite semantic and source-bound construction checks, not Dafny verification."""
import itertools
import unittest
from pathlib import Path
import build_controls as b


def move_spec(xs, k):
    return [xs[k]] + xs[:k] + xs[k+1:]


def move_via_adjacent_swaps(xs, k):
    if k == 0:
        return xs[:]
    swapped = xs[:]
    swapped[k-1], swapped[k] = swapped[k], swapped[k-1]
    return move_via_adjacent_swaps(swapped, k-1)


def pair_spec(xs, i, j):
    return [xs[i], xs[j]] + xs[:i] + xs[i+1:j] + xs[j+1:]


class DesignTests(unittest.TestCase):
    def test_reference_and_alternative_semantics_on_small_sequences(self):
        # Includes duplicate values, empty remainders and both endpoint cases.
        for n in range(1, 6):
            for items in itertools.product(range(3), repeat=n):
                xs = list(items)
                for k in range(n):
                    self.assertEqual(move_via_adjacent_swaps(xs, k), move_spec(xs, k))
                for i in range(n):
                    for j in range(i+1, n):
                        first = move_spec(xs, i)
                        reference = [first[0]] + move_spec(first[1:], j-1)
                        alternative = move_spec(move_spec(xs, j), i+1)
                        self.assertEqual(reference, pair_spec(xs, i, j))
                        self.assertEqual(alternative, reference)
                        self.assertEqual(sorted(reference), sorted(xs))

    def test_distinct_wrong_candidates_have_concrete_counterexamples(self):
        xs = [0, 1, 2, 3]
        self.assertNotEqual(xs, move_spec(xs, 2))
        endpoint = xs[:]
        endpoint[0], endpoint[2] = endpoint[2], endpoint[0]
        self.assertNotEqual(endpoint, move_spec(xs, 2))
        self.assertNotEqual(xs, pair_spec(xs, 1, 3))
        self.assertNotEqual(move_spec(xs, 1), pair_spec(xs, 1, 3))
        self.assertNotEqual(move_spec(move_spec(xs, 3), 1), pair_spec(xs, 1, 3))

    def test_all_cases_preserve_interface_and_body_boundaries(self):
        for _, move, pair, _, _ in b.CASES:
            for kind, body in [('move', move), *([('pair', pair)] if pair else [])]:
                name = 'MoveToFront.dfy' if kind == 'move' else 'PickPair.dfy'
                template = (b.ROOT / 'templates' / name).read_text()
                rendered = b.render(kind, body).decode()
                self.assertEqual(template.split(b.BEGIN)[0], rendered.split(b.BEGIN)[0])
                self.assertEqual(template.split(b.END)[1], rendered.split(b.END)[1])
                for forbidden in ('assume ', '{:axiom}', '{:verify false}', 'decreases *', 'reveal Shift.'):
                    self.assertNotIn(forbidden, rendered)

    def test_coverage_controls_are_distinct_from_source_validity(self):
        ids = [case[0] for case in b.CASES]
        self.assertEqual(len(ids), len(set(ids)))
        explicit = next(x for x in b.CASES if x[0] == 'detached-explicit')
        omitted = next(x for x in b.CASES if x[0] == 'detached-omitted')
        self.assertEqual(explicit[1:3], omitted[1:3])
        self.assertTrue(explicit[4] and omitted[4])
        self.assertEqual(omitted[3], 'NATIVE_PASS_COVERAGE_REJECT')


if __name__ == '__main__':
    unittest.main()
