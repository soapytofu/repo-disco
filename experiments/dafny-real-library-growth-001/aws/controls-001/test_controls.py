"""Source/header/coverage construction tests; no native or model invocation."""
import json
from pathlib import Path
import re
import unittest

import build as b


class ControlTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.cases = json.loads((b.ROOT / 'cases.json').read_bytes())
        cls.by_id = {case['id']:case for case in cls.cases}
        cls.refs = {stage:b.reference(stage) for stage in (0, 1, 2)}

    def sources(self, case):
        folder = b.ROOT / case['workspace_dir']
        return {p.relative_to(folder).as_posix():p.read_bytes() for p in folder.rglob('*') if p.is_file()}

    def test_exact_nine_controls_exclude_all_three_positive_cases(self):
        self.assertEqual(tuple(c['id'] for c in self.cases), b.CONTROL_IDS)
        self.assertEqual(len(self.by_id), 9)
        self.assertEqual(sum(c['expected_category'] == 'PROOF_FAILURE' for c in self.cases), 8)
        self.assertEqual(sum(c['expected_category'] == 'COVERAGE_OMISSION' for c in self.cases), 1)
        self.assertTrue(set(self.by_id).isdisjoint(b.REFERENCE_IDS.values()))
        for case in self.cases:
            self.assertFalse(case['native_dispatch_allowed'])
            self.assertFalse(case['model_acceptance'])
            self.assertEqual(case['native_status'], 'UNKNOWN')

    def test_all_102_upstream_sources_and_scope_order_are_exact(self):
        baseline = self.refs[0][1]
        self.assertEqual(len(baseline), 102)
        for case in self.cases:
            sources = self.sources(case)
            self.assertEqual(b.source_hashes(sources), case['source_sha256'])
            self.assertEqual(len(sources), 102 + case['stage'])
            for name, raw in baseline.items():
                self.assertEqual(sources[name], raw, (case['id'], name))
            roots = self.refs[case['stage']][0]['explicit_root_files']
            self.assertEqual(case['declared_scope_files'], roots)
            self.assertEqual(case['command_files'], [p for p in roots if p not in case['omit_from_command']])

    def test_seven_draft_body_variants_preserve_every_fixed_header_byte(self):
        for ident in b.BAD_BODY_IDS:
            case = self.by_id[ident]
            sources = self.sources(case)
            reference = self.refs[case['stage']][1]
            changed = {name for name in sources if sources[name] != reference[name]}
            self.assertEqual(changed, set(case['replacement_inputs']))
            self.assertEqual(len(changed), 1)
            path = next(iter(changed))
            origin = case['replacement_inputs'][path]['aws_relative_path']
            self.assertEqual(sources[path], (b.AWS / origin).read_bytes())
            target = b.PARENT_TARGET if path == b.STAGE1 else b.CHILD_TARGET
            before, after = b.fixed_parts(reference[path], target)
            self.assertTrue(sources[path].startswith(before))
            self.assertTrue(sources[path].endswith(after))
            body = sources[path][len(before):-len(after)].decode()
            self.assertNotRegex(body, r'\bassume\b|\baxiom\b|\bexpect\b|\bdecreases\s+\*|\{:\s*(?:verify|extern|axiom|options)\b')

    def test_unproved_parent_retains_exact_reference_child_without_claiming_success(self):
        case = self.by_id['unproved-parent-passing-child']
        sources = self.sources(case)
        self.assertEqual(sources[b.STAGE1], (b.AWS / 'draft/negatives/stage1-always-failure.dfy').read_bytes())
        self.assertEqual(sources[b.STAGE2], self.refs[2][1][b.STAGE2])
        self.assertEqual(case['expected_failed_targets'], [b.PARENT_TARGET])
        self.assertEqual(case['expected_passed_targets'], [])
        self.assertEqual(case['inspect_targets'], [b.CHILD_TARGET])
        self.assertFalse(case['child_outcome_predetermined'])
        self.assertEqual(case['expected_category'], 'PROOF_FAILURE')

    def test_omitted_target_is_staged_hashed_but_never_in_argv_or_include_closure(self):
        case = self.by_id['stage2-omitted-from-roots']
        sources = self.sources(case)
        self.assertEqual(sources, self.refs[2][1])
        self.assertIn(b.STAGE2, case['source_sha256'])
        self.assertIn(b.STAGE2, case['declared_scope_files'])
        self.assertNotIn(b.STAGE2, case['command_files'])
        self.assertNotIn(b.STAGE2, case['argv'])
        self.assertEqual(b.include_closure(case['command_files'], sources), set(self.refs[1][1]))
        self.assertEqual(case['command_files'], self.refs[1][0]['explicit_root_files'])
        self.assertEqual(case['omitted_targets'], [b.CHILD_TARGET])
        self.assertEqual(case['expected_category'], 'COVERAGE_OMISSION')
        self.assertEqual(case['expected_native_category'], 'PROOF_PASS')

    def test_full_argv_limits_and_all_generated_hashes_are_deterministic(self):
        config = json.loads((b.PACKAGE / 'qualification-002/configs/aws.json').read_bytes())
        prefix = [config['dafny'], 'verify'] + config['options']
        for case in self.cases:
            self.assertEqual(case['argv'], prefix + case['command_files'])
            self.assertEqual(b.include_closure(case['command_files'], self.sources(case)),
                             set(case['source_sha256']) - set(case['omit_from_command']))
        files = b.material()
        for name, raw in files.items():
            self.assertEqual((b.ROOT / name).read_bytes(), raw, name)


if __name__ == '__main__':
    unittest.main(verbosity=2)
