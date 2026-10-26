"""Offline candidate tests using frozen task guards and saved verified source."""
import json
from pathlib import Path
import sys
import unittest
from unittest.mock import patch
from types import SimpleNamespace

from language.dafny.candidate import prepare_candidate, verify_candidate, hashes
ROOT = Path(__file__).resolve().parents[1]
TASK = ROOT/'experiments'/'inductive-sharing-001'
sys.path.insert(0, str(TASK))
from provider_guard import parse_response


def provider_guard(before, after):
    parsed, _ = parse_response(json.dumps({'Facts.dfy': after.decode()}), before.decode())
    if parsed.encode() != after:
        raise ValueError('guard output must equal supplied bytes')


class CandidateTests(unittest.TestCase):
    def setUp(self):
        self.base = {p.name:p.read_bytes() for p in (TASK/'revision-003/fixtures/shared_empty').glob('*.dfy')}
        self.proof = (TASK/'revision-003/fixtures/shared_reference/Facts.dfy').read_bytes()

    def prepare(self, replacements, **extra):
        args = dict(entry='All.dfy', expected_hashes=hashes(self.base), guards={'Facts.dfy':provider_guard})
        args.update(extra)
        return prepare_candidate(self.base, replacements, **args)

    def test_frozen_guard_repair_preserves_all_dependency_bytes(self):
        original = dict(self.base)
        candidate = self.prepare({'Facts.dfy':self.proof})
        self.assertEqual(self.base, original)
        self.assertEqual(candidate.changed_files, ('Facts.dfy',))
        for name in self.base:
            if name != 'Facts.dfy': self.assertEqual(candidate.files[name],self.base[name])
        with self.assertRaises(TypeError): candidate.files['Facts.dfy'] = b'changed'

    def test_reject_contract_changes_before_verification(self):
        with self.assertRaises(ValueError): self.prepare({'Facts.dfy':self.proof.replace(b'decreases |s|',b'decreases *')})

    def test_reject_immutable_and_added_files(self):
        for replacement in [{'ClientA.dfy':b''},{'new.dfy':b''}]:
            with self.assertRaises(ValueError): self.prepare(replacement)

    def test_reject_stale_base_and_noop(self):
        with self.assertRaises(ValueError): self.prepare({'Facts.dfy':self.proof}, expected_hashes={})
        with self.assertRaises(ValueError): self.prepare({'Facts.dfy':self.base['Facts.dfy']})

    def test_multiple_replacements_are_all_guarded(self):
        base = {'A.dfy':b'oldA','B.dfy':b'oldB','All.dfy':b'entry'}
        seen=[]
        def guard(before,after): seen.append((before,after))
        candidate = prepare_candidate(base,{'A.dfy':b'newA','B.dfy':b'newB'},entry='All.dfy',expected_hashes=hashes(base),guards={'A.dfy':guard,'B.dfy':guard})
        self.assertEqual(len(seen),2)
        self.assertEqual(candidate.changed_files,('A.dfy','B.dfy'))
        self.assertEqual(base['A.dfy'],b'oldA')

    def test_failed_guard_leaves_base_untouched(self):
        base={'A.dfy':b'a','B.dfy':b'b'}
        def reject(*args): raise ValueError('rejected')
        with self.assertRaises(ValueError):
            prepare_candidate(base,{'A.dfy':b'x','B.dfy':b'y'},entry='A.dfy',expected_hashes=hashes(base),guards={'A.dfy':lambda *args:None,'B.dfy':reject})
        self.assertEqual(base,{'A.dfy':b'a','B.dfy':b'b'})

    def test_single_verification_no_promotion_even_on_failure(self):
        candidate=self.prepare({'Facts.dfy':self.proof})
        for status in [0,4,124]:
            fake=SimpleNamespace(evidence={'exit_code':status})
            with patch('language.dafny.candidate.verify_repository',return_value=fake) as verify:
                result=verify_candidate(candidate)
            verify.assert_called_once_with(dict(candidate.files),'All.dfy',timeout=60)
            self.assertFalse(result.evidence['candidate']['promoted'])
            self.assertEqual(self.base['Facts.dfy'],(TASK/'revision-003/fixtures/shared_empty/Facts.dfy').read_bytes())

if __name__=='__main__': unittest.main()
