"""Offline scope, body, contract and finite design checks; not native proof."""
import itertools
import json
from pathlib import Path
import re
import unittest

import build as b


def frame(data):
    if len(data) < 2:
        return None
    n = 256 * data[0] + data[1]
    if len(data) < 2 + n:
        return None
    return data[2:2+n], data[2+n:]


def pair(data):
    first = frame(data)
    if first is None:
        return None
    second = frame(first[1])
    if second is None:
        return None
    return first[0], second[0], second[1]


def encode_frame(payload):
    assert len(payload) < 65536
    return [len(payload) // 256, len(payload) % 256] + payload


class RevisionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.cases = json.loads((b.ROOT / 'cases.json').read_bytes())
        cls.by_id = {case['id']:case for case in cls.cases}

    def sources(self, case):
        folder = b.ROOT / case['workspace_dir']
        return {p.relative_to(folder).as_posix():p.read_bytes() for p in folder.rglob('*') if p.is_file()}

    def test_exact_closed_three_source_baseline_and_preserved_blob_bytes(self):
        base = self.sources(self.by_id['baseline'])
        self.assertEqual(set(base), set(b.BASE))
        self.assertEqual(b.closure(b.BASE, base), set(b.BASE))
        old = json.loads((b.AWS / 'cases-001/aws-baseline-001/case.json').read_bytes())
        old_hashes = {item['path']:item['sha256'] for item in old['source_files']}
        for case in self.cases:
            sources = self.sources(case)
            for name, raw in base.items():
                self.assertEqual(sources[name], raw)
                self.assertEqual(b.sha(raw), old_hashes[name])
            self.assertEqual(len(sources), 3 + case['stage'])
            self.assertEqual({name:b.sha(raw) for name,raw in sorted(sources.items())},case['source_sha256'])

    def test_stage1_spec_body_and_old_negative_bodies_are_exact(self):
        template = (b.ROOT / 'templates/RepoDiscoU16Frame.dfy').read_bytes()
        self.assertEqual(template, (b.PACKAGE / 'pilot/draft-001/templates/aws-stage1.dfy').read_bytes())
        for name in ['stage1-reference'] + b.NEGATIVE1:
            origin = b.AWS / ('draft/overlay/' + b.STAGE1 if name == 'stage1-reference' else 'draft/negatives/' + name + '.dfy')
            _, body, _ = b.original_stage1_parts(origin.read_bytes())
            self.assertEqual((b.ROOT / 'bodies' / (name + '.txt')).read_bytes(), body)

    def test_blank_markers_and_protected_headers_are_identical_for_every_variant(self):
        for case in self.cases:
            sources = self.sources(case)
            for path, template, body_id in ((b.STAGE1,'RepoDiscoU16Frame.dfy',case['parent_body']),
                                             (b.STAGE2,'RepoDiscoFramePair.dfy',case['child_body'])):
                if body_id is None:
                    continue
                before, after = b.split_template((b.ROOT / 'templates' / template).read_bytes())
                body = (b.ROOT / 'bodies' / (body_id + '.txt')).read_bytes()
                self.assertEqual(sources[path], before + body + after)
                self.assertNotRegex(body.decode(),r'\bassume\b|\bexpect\b|\baxiom\b|\bdecreases\s+\*|\{:\s*(?:verify|extern|axiom|options)\b')

    def test_three_positives_nine_controls_and_exact_parent_chain(self):
        self.assertEqual(len(self.cases), 12)
        self.assertEqual([c['id'] for c in self.cases if not c['gated_until_positive_review']], b.FIRST)
        self.assertEqual(sum(c['gated_until_positive_review'] for c in self.cases),9)
        reference = self.sources(self.by_id['stage1-reference'])[b.STAGE1]
        for case in self.cases:
            if case['stage'] == 2 and case['id'] != 'unproved-parent-reference-child':
                self.assertEqual(self.sources(case)[b.STAGE1], reference)
        unproved = self.by_id['unproved-parent-reference-child']
        self.assertEqual(self.sources(unproved)[b.STAGE1], self.sources(self.by_id['stage1-always-failure'])[b.STAGE1])
        self.assertEqual(self.sources(unproved)[b.STAGE2], self.sources(self.by_id['stage2-reference'])[b.STAGE2])
        self.assertEqual(unproved['expected_failed_targets'], [b.TARGET1])
        self.assertFalse(unproved['child_outcome_predetermined'])

    def test_omitted_bad_child_remains_staged_but_outside_actual_scope(self):
        case = self.by_id['stage2-omitted-from-roots']
        sources = self.sources(case)
        self.assertEqual(sources[b.STAGE2], self.sources(self.by_id['stage2-always-failure'])[b.STAGE2])
        self.assertIn(b.STAGE2,case['source_sha256'])
        self.assertNotIn(b.STAGE2,case['command_files'])
        self.assertNotIn(b.STAGE2,case['argv'])
        self.assertEqual(b.closure(case['command_files'],sources),set(self.sources(self.by_id['stage1-reference'])))
        self.assertEqual(case['expected_category'],'COVERAGE_OMISSION')
        self.assertEqual(case['expected_native_category'],'PROOF_PASS')

    def test_finite_pair_oracle_reencoding_boundaries_and_negative_examples(self):
        # Only a finite design oracle: no Dafny compilation/execution is claimed.
        for size_left,size_right in itertools.product(range(4),repeat=2):
            left,right=[255]*size_left,[65]*size_right
            for rest in ([],[99,100]):
                data=encode_frame(left)+encode_frame(right)+rest
                self.assertEqual(pair(data),(left,right,rest))
                actual=pair(data)
                self.assertEqual(encode_frame(actual[0])+encode_frame(actual[1])+actual[2],data)
        self.assertIsNone(pair([]))
        self.assertIsNone(pair([0,0]))
        self.assertIsNone(pair([0,0,0,2,65]))
        self.assertEqual(pair([0,1,255,0,0]),([255],[],[]))  # Raw byte 255 is valid here.
        self.assertEqual(pair(encode_frame([255]*65535)+[0,0,42]),([255]*65535,[],[42]))
        data=[0,1,65,0,1,66,99]
        self.assertNotEqual(pair(data),([66],[65],[99]))
        self.assertNotEqual(pair(data),([65],[66],[0,1,66,99]))
        self.assertIsNone(pair([0,0]))  # A first frame alone cannot justify success.

    def test_explicit_revision_ancestry_no_old_scope_promotion_or_resource_change(self):
        revision=json.loads((b.ROOT/'revision.json').read_bytes())
        self.assertEqual(revision['failed_ancestor']['job_id'],'63088520')
        self.assertTrue(revision['failed_ancestor']['unchanged'])
        self.assertEqual(len(revision['current_scope']['not_in_this_new_component']),99)
        self.assertFalse(revision['native_policy']['resources_changed'])
        self.assertEqual(revision['native_policy']['resource_limit'],500000000)
        self.assertEqual(revision['native_policy']['outer_wall_seconds'],900)
        self.assertEqual(revision['stage2']['parent_call_count'],2)
        self.assertFalse(revision['stage2']['required_reuse'])
        self.assertNotRegex((b.ROOT/'templates/RepoDiscoFramePair.dfy').read_text(),r'UTF8|EncryptionContext|Types\.')
        self.assertEqual((b.ROOT/'bodies/stage2-reference.txt').read_text().count('F.ReadU16Frame('),2)
        self.assertEqual(revision['failed_ancestor']['evidence_sha256'],b.ancestry_pins())
        for name,raw in b.material().items():
            self.assertEqual((b.ROOT/name).read_bytes(),raw,name)


if __name__=='__main__':
    unittest.main(verbosity=2)
