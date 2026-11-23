"""Read-only reference-mapping boundary tests against retained observations."""
import ast
import copy
import json
from pathlib import Path
import unittest
from unittest.mock import patch

import review
import mapping

HERE = Path(__file__).resolve().parent
EXPERIMENT = HERE.parent
native = review.native


def obj(path):
    return json.loads(path.read_bytes())


class ReferenceReviewTests(unittest.TestCase):
    def setUp(self):
        self.selection = obj(HERE / 'selection-001.json')
        self.binding = self.selection['tasks']['aws-batch']

    def test_exact_aws_inspection_and_unlogged_definitions(self):
        inspection = obj(HERE / 'reviews/aws-native-002/inspection.json')
        self.assertEqual(inspection['status'], 'INSPECTION_ONLY')
        self.assertFalse(inspection['all_references_match'])
        self.assertEqual({task: row['named_units'] for task, row in inspection['tasks'].items()},
                         {'aws-batch': 81, 'aws-tagged': 79})
        for task, row in inspection['tasks'].items():
            profile = obj(EXPERIMENT / row['native_profile']['path'])
            self.assertEqual(profile['project'], task)
            self.assertEqual(profile['stage'], 1)
            self.assertEqual(row['inherited_unit_count'], 77)
            self.assertTrue(profile['unlogged_definitions'])
            for definition in profile['unlogged_definitions']:
                self.assertFalse(definition['counted_as_pass'])
                self.assertFalse(any(name.startswith(definition['name'] + ' (')
                                     for name in profile['required_units']))
            for path, digest in row['input_files'].items():
                self.assertEqual(native.sha((EXPERIMENT / path).read_bytes()), digest)
            for receipt in [row['native_review'], row['reference_record'],
                            *row['reference_raw'].values(), *row['reference_sources'].values()]:
                self.assertEqual(native.sha((EXPERIMENT / receipt['path']).read_bytes()), receipt['sha256'])
        self.assertFalse((HERE / 'reference-gate.json').exists())

    def test_partial_or_unready_selection_cannot_issue_gate(self):
        for tasks, reason in [(None, 'binding is not ready'), (['aws-batch'], 'Partial review')]:
            with self.subTest(tasks=tasks), self.assertRaisesRegex(native.EvidenceError, reason):
                review.run(HERE / 'selection-001.json', tasks)
        self.assertFalse((HERE / 'reference-gate.json').exists())

    def test_actual_failed_stdlib_reference_is_not_qualified(self):
        profile = obj(EXPERIMENT / 'stdlib/profiles/stdlib-filter.json')
        binding = dict(family='stdlib', runtime_root='qualification-001', case_id='filter-reference',
            observation='qualification-001/retrieved-stdlib/qualification-001/output-stdlib/filter-reference',
            edit_profile='stdlib/profiles/stdlib-filter.json',
            base_sources={name: 'stdlib/base/' + name for name in profile['base_source_sha256']},
            inherited_profile='qualification-001/inherited-profiles/stdlib-stage0.json',
            fixture_manifest='stdlib/manifest.json', target='RepoDiscoStableFilter.StableFilterBelow')
        with self.assertRaisesRegex(native.EvidenceError, 'preliminary native checks'):
            review.inspect_task('stdlib-filter', binding, [], [], {}, {})

    def test_stale_raw_bytes_rejected_before_mapping(self):
        original = review.read
        raw_path = self.binding['observation'] + '/raw/stdout.txt'

        def changed(path, pins):
            raw = original(path, pins)
            return raw + b'changed' if path == raw_path else raw

        with patch.object(review, 'read', side_effect=changed):
            with self.assertRaisesRegex(native.EvidenceError, 'raw hashes changed'):
                review.load_observation(self.binding['observation'], {})

    def test_missing_inherited_and_current_target_units_fail_closed(self):
        original = mapping.inventory
        for mode, reason in [('old', 'Inherited native inventory'), ('target', 'Primary task target')]:
            def incomplete(*args):
                rows, definitions, unlogged, multiplicities = original(*args)
                if mode == 'old':
                    bad = next(row['label'] for row in rows if row['file'] == 'libraries/src/BoundedInts.dfy')
                    rows = [row for row in rows if row['label'] != bad]
                else:
                    rows = [row for row in rows if not row['label'].startswith(self.binding['target'] + ' (')]
                return rows, definitions, unlogged, multiplicities
            with self.subTest(mode=mode), patch.object(mapping, 'inventory', side_effect=incomplete):
                with self.assertRaisesRegex(native.EvidenceError, reason):
                    review.inspect_task('aws-batch', self.binding, [], [], {}, {})

    def test_duplicate_or_unmapped_native_units_rejected(self):
        _, sources, raw = review.load_observation(self.binding['observation'], {})
        inherited = obj(EXPERIMENT / self.binding['inherited_profile'])
        csv_path = next(path for path in raw if path.startswith('csv/'))
        lines = raw[csv_path].splitlines(keepends=True)
        duplicated = dict(raw, **{csv_path: raw[csv_path] + lines[1]})
        with self.assertRaisesRegex(native.EvidenceError, 'duplicate native proof unit'):
            mapping.inventory('aws', sources, duplicated, inherited)
        changed = dict(raw, **{csv_path: raw[csv_path].replace(
            b'RepoDiscoFrameBatch.ReadCountedFrames', b'UnreviewedModule.ReadCountedFrames')})
        with self.assertRaisesRegex(native.EvidenceError, 'native module ownership'):
            mapping.inventory('aws', sources, changed, inherited)

    def test_fixed_contract_drift_prevents_reconstruction(self):
        original = review.read

        def changed(path, pins):
            raw = original(path, pins)
            if path == self.binding['edit_profile']:
                profile = json.loads(raw)
                profile['addition']['template_utf8'] = profile['addition']['template_utf8'].replace(
                    'ensures result.Success? <==> HasCountedFrames(input, count)',
                    'ensures result.Success? ==> HasCountedFrames(input, count)', 1)
                return native.canonical(profile)
            return raw

        with patch.object(review, 'read', side_effect=changed):
            with self.assertRaisesRegex(native.EvidenceError, 'changed fixed headers'):
                review.inspect_task('aws-batch', self.binding, [], [], {}, {})

    def test_wrong_fixture_manifest_cannot_certify_selected_sources(self):
        original = review.read

        def changed(path, pins):
            raw = original(path, pins)
            if path == self.binding['fixture_manifest']:
                manifest = json.loads(raw)
                del manifest['files']['cases/counted-reference/workspace/StandardLibrary/src/RepoDiscoFrameBatch.dfy']
                return native.canonical(manifest)
            return raw

        with patch.object(review, 'read', side_effect=changed):
            with self.assertRaisesRegex(native.EvidenceError, 'exact fixture manifest'):
                review.inspect_task('aws-batch', self.binding, [], [], {}, {})

    def test_scanner_functions_have_exact_published_origin(self):
        old_text = (HERE / 'origins/prepare.py').read_text()
        new_text = (HERE / 'source_scan.py').read_text()
        names = {'lex', 'line_number', 'declaration_headers'}
        selected = lambda text: {node.name: ast.dump(node, include_attributes=False)
            for node in ast.parse(text).body if isinstance(node, ast.FunctionDef) and node.name in names}
        self.assertEqual(selected(old_text), selected(new_text))
        self.assertEqual(set(selected(new_text)), names)


if __name__ == '__main__':
    unittest.main(verbosity=2)
