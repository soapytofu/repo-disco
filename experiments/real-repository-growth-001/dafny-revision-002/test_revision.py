"""Byte-preservation and namespace-binding checks; no Dafny execution."""
import unittest

import build_revision as b


class NamespaceRevisionTests(unittest.TestCase):
    def test_exact_permitted_header_changes_and_inverse_reconstruction(self):
        provenance = b.read(b.ROOT / 'source-provenance.json')
        self.assertEqual(len(provenance), 24)
        changed = 0
        for relative, record in provenance.items():
            before = (b.PARENT / relative).read_bytes()
            after = (b.ROOT / relative).read_bytes()
            self.assertEqual(b.sha(before), record['parent_sha256'])
            self.assertEqual(b.sha(after), record['revision_sha256'])
            expected, changes = b.rewrite(relative.rsplit('/', 1)[-1], before)
            self.assertEqual(after, expected)
            self.assertEqual(changes, record['permitted_edits'])
            inverse = after.decode().splitlines(keepends=True)
            for change in changes:
                self.assertEqual(inverse[change['line']-1], change['after'])
                inverse[change['line']-1] = change['before']
            self.assertEqual(''.join(inverse).encode(), before)
            self.assertEqual(after.splitlines(keepends=True)[3:], before.splitlines(keepends=True)[3:])
            changed += bool(changes)
        self.assertEqual(changed, 22)

    def test_contract_body_decreases_and_export_bytes_unchanged(self):
        for relative in b.read(b.ROOT / 'source-provenance.json'):
            before = (b.PARENT / relative).read_bytes()
            after = (b.ROOT / relative).read_bytes()
            for marker in (b'  export Public', b'    // BEGIN MODEL BODY\n'):
                if marker in before:
                    self.assertEqual(before.split(marker, 1)[1], after.split(marker, 1)[1])
            for forbidden in (b'assume ', b'{:axiom}', b'{:verify false}', b'decreases *', b'reveal Shift.'):
                self.assertNotIn(forbidden, after)

    def test_control_catalog_outcomes_registration_and_labels_preserved(self):
        old = b.read(b.PARENT / 'controls-manifest.json')
        new = b.read(b.ROOT / 'controls-manifest.json')
        self.assertEqual(len(new['cases']), 12)
        self.assertEqual([x['id'] for x in old['cases']], [x['id'] for x in new['cases']])
        for before, after in zip(old['cases'], new['cases']):
            for field in ('id', 'expected', 'explicitly_omit_from_command'):
                self.assertEqual(before[field], after[field])
            self.assertEqual(set(before['additions']), set(after['additions']))
            self.assertEqual(after['required_units'], [x.replace('FisherYates.GrowthShift.', 'RepoDiscoGrowthShift.')
                .replace('FisherYates.GrowthPick.', 'RepoDiscoGrowthPick.') for x in before['required_units']])
        explicit = next(x for x in new['cases'] if x['id']=='detached-explicit')
        omitted = next(x for x in new['cases'] if x['id']=='detached-omitted')
        self.assertEqual(explicit['additions'], omitted['additions'])

    def test_top_level_names_distinct_and_upstream_unchanged(self):
        source = next(x for x in b.read(b.SOURCE_MANIFEST) if x['id']=='dafny-vmc')
        self.assertEqual(len(source['files']), 91)
        for name, value in source['files'].items():
            raw = (b.UPSTREAM / name).read_bytes()
            self.assertEqual(b.sha(raw), value)
            self.assertNotIn(b'RepoDiscoGrowthShift', raw)
            self.assertNotIn(b'RepoDiscoGrowthPick', raw)
        move = (b.ROOT / 'templates/MoveToFront.dfy').read_text()
        pair = (b.ROOT / 'templates/PickPair.dfy').read_text()
        self.assertIn('module RepoDiscoGrowthShift {\n  import Model = FisherYates.Model\n', move)
        self.assertIn('module RepoDiscoGrowthPick {\n  import Shift = RepoDiscoGrowthShift`Public\n', pair)
        self.assertNotIn('module FisherYates.', move + pair)

    def test_old_frozen_source_and_failure_evidence_still_exact(self):
        for name, value in b.read(b.PARENT / 'offline-files-001.json')['files'].items():
            self.assertEqual(b.sha((b.PARENT / name).read_bytes()), value)
        design = b.read(b.ROOT / 'design.json')
        self.assertEqual(design['parent_failure']['category'], 'RESOLUTION_OR_TYPE_FAILURE')
        self.assertEqual(design['parent_failure']['exit_code'], 2)
        for name, value in design['parent_failure']['raw_evidence_sha256'].items():
            self.assertEqual(b.sha((b.FAILURE / name).read_bytes()), value)
        self.assertEqual(design['native_verifier_calls'], 0)
        self.assertTrue(design['new_unit_labels_provisional_until_native_csv'])


if __name__ == '__main__':
    unittest.main()
