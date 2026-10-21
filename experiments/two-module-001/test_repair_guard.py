"""Offline fixture policy checks; no model calls."""
from pathlib import Path
import unittest
from repair_guard import validate_candidate


class RepairGuardTests(unittest.TestCase):
    def setUp(self):
        self.valid=(Path(__file__).parent/'fixtures/baseline/Arithmetic.dfy').read_text()

    def test_valid_repair(self):
        self.assertTrue(validate_candidate(self.valid))

    def test_rejects_contract_weakening(self):
        with self.assertRaises(ValueError):
            validate_candidate(self.valid.replace('ensures y == x + 1','ensures y >= x'))

    def test_rejects_assumption(self):
        with self.assertRaises(ValueError):
            validate_candidate(self.valid.replace('y := x + 1;','assume false; y := x + 1;'))

    def test_rejects_extra_method(self):
        with self.assertRaises(ValueError):
            validate_candidate(self.valid.replace('y := x + 1;','y := x + 1; } method Escape() {'))

    def test_rejects_verification_bypass_attribute(self):
        with self.assertRaises(ValueError):
            validate_candidate(self.valid.replace('module Arithmetic','module {:verify false} Arithmetic'))

    def test_guard_does_not_claim_semantic_correctness(self):
        self.assertTrue(validate_candidate(self.valid.replace('y := x + 1;','y := x - 1;')))


if __name__=='__main__':unittest.main()
