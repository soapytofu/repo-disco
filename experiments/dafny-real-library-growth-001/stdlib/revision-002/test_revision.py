"""Offline revision-integrity checks; no claim of mathematical verification."""
import collections
import json
from pathlib import Path
import re
import unittest

import build as b


class RevisionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.cases = json.loads((b.ROOT / 'cases.json').read_bytes())
        cls.by_id = {c['id']: c for c in cls.cases}
        cls.old = {c['id']: c for c in json.loads((b.PARENT / 'cases.json').read_bytes())}

    def test_only_existing_invariant_line_is_moved(self):
        changed = []
        for path in (b.ROOT / 'bodies').glob('*.txt'):
            old = (b.PARENT / 'bodies' / path.name).read_bytes()
            new = path.read_bytes()
            self.assertEqual(collections.Counter(old.splitlines()), collections.Counter(new.splitlines()))
            if old != new:
                changed.append(path.stem)
                self.assertEqual(old.replace(b.FRESH.encode(), b''), new.replace(b.FRESH.encode(), b''))
                self.assertIn((b.FRESH + b.VALID).encode(), new)
            self.assertNotRegex(new.decode(), r'\bassume\b|\bexpect\b|\baxiom\b|\bdecreases\s+\*|\{:\s*(?:verify|extern|axiom|options)\b')
        self.assertEqual(set(changed), b.CHANGED_BODIES)

    def test_upstream_and_all_protected_source_bytes_are_identical(self):
        upstream = b.original.upstream_sources(b.PARENT)
        for case in self.cases:
            folder = b.ROOT / case['workspace_dir']
            for source, raw in upstream.items():
                self.assertEqual((folder / source).read_bytes(), raw)
            for source, template in ((b.original.APPEND, 'AppendAll.dfy'), (b.original.ROTATE, 'AppendRotated.dfy')):
                if source not in case['source_sha256']:
                    continue
                before, after = b.original.fixed_parts(template, b.PARENT)
                raw = (folder / source).read_text()
                self.assertTrue(raw.startswith(before))
                self.assertTrue(raw.endswith(after))

    def test_scope_categories_and_named_outcomes_are_preserved(self):
        self.assertEqual(len(self.cases), 11)
        self.assertNotIn('baseline', self.by_id)
        for case in self.cases:
            old = self.old[case['id']]
            for field in ('stage', 'command_files', 'declared_scope_files', 'expected_category',
                          'expected_native_category', 'expected_failed_targets',
                          'expected_passed_targets', 'required_targets', 'omitted_targets', 'omit_from_command'):
                self.assertEqual(case[field], old[field], (case['id'], field))
            folder = b.ROOT / case['workspace_dir']
            actual = {p.relative_to(folder).as_posix(): b.sha(p.read_bytes()) for p in folder.rglob('*') if p.is_file()}
            self.assertEqual(actual, case['source_sha256'])
            self.assertFalse(case['model_acceptance'])
            self.assertEqual(case['native_status'], 'UNKNOWN')

    def test_parent_identity_and_failed_parent_control_remain_explicit(self):
        ref = self.by_id['append-reference']['source_sha256'][b.original.APPEND]
        for case in self.cases:
            if case['stage'] == 2 and case['id'] != 'rotate-unproved-append':
                self.assertEqual(case['source_sha256'][b.original.APPEND], ref)
        bad = self.by_id['rotate-unproved-append']
        self.assertEqual(bad['source_sha256'][b.original.APPEND], self.by_id['append-empty']['source_sha256'][b.original.APPEND])
        self.assertEqual(bad['expected_failed_targets'], [b.original.APPEND_TARGET])
        self.assertEqual(bad['expected_passed_targets'], [b.original.ROTATE_TARGET])
        direct = (b.ROOT / 'bodies/rotate-direct.txt').read_text()
        self.assertNotIn('Append.AppendAll(', direct)
        self.assertIn('a.Push(', direct)

    def test_exact_reconstruction_and_prior_evidence_pins(self):
        files = b.material()
        for name, raw in files.items():
            self.assertEqual((b.ROOT / name).read_bytes(), raw, name)
        revision = json.loads(files['revision.json'])
        self.assertEqual(revision['first_native_phase']['case_ids'], ['append-reference', 'rotate-reference'])
        self.assertFalse(revision['first_native_phase']['baseline_repeated'])
        self.assertEqual(len(revision['remaining_controls']['case_ids']), 9)
        self.assertFalse(revision['remaining_controls']['dispatch_allowed'])
        self.assertEqual(revision['preserved_native_evidence_sha256'], b.evidence_pins())


if __name__ == '__main__':
    unittest.main(verbosity=2)
