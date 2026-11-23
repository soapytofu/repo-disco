"""Offline fixture, guard and finite semantic checks; never invokes Dafny."""
from collections import Counter
import importlib.util
import json
from pathlib import Path
import random
import sys
import unittest

import build

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / 'compatibility'))
import guard
import review_native


def read(path):
    return json.loads(path.read_bytes())


def sources(folder):
    return {p.relative_to(folder).as_posix(): p.read_bytes() for p in sorted(folder.rglob('*.dfy'))}


def encode_frame(payload):
    assert len(payload) < 65536
    return len(payload).to_bytes(2, 'big') + payload


def decode_counted(data, count):
    """Finite executable oracle, not a translation or validation of Dafny."""
    assert count >= 0
    offset, payloads = 0, []
    for _ in range(count):
        if len(data) - offset < 2:
            return None
        size = int.from_bytes(data[offset:offset + 2], 'big')
        start = offset + 2
        end = start + size
        if end > len(data):
            return None
        payloads.append(data[start:end])
        offset = end
    return payloads, data[offset:]


def decode_tagged(data, tag, budget):
    assert 0 <= tag <= 255 and budget >= 0
    pair = decode_counted(data, 2)
    if pair is None:
        return None
    (left, right), rest = pair
    if not left or left[0] != tag or len(left) - 1 + len(right) > budget:
        return None
    return left[1:], right, rest


class ConstructionTests(unittest.TestCase):
    def test_manifest_and_exact_reconstruction_are_deterministic(self):
        actual = build.material()
        for name, raw in actual.items():
            self.assertEqual((ROOT / name).read_bytes(), raw, name)
        manifest = read(ROOT / 'manifest.json')
        for name, digest in manifest['files'].items():
            self.assertEqual(build.sha((ROOT / name).read_bytes()), digest, name)
        self.assertEqual(manifest['reference_cases'], ['counted-reference', 'tagged-reference'])
        self.assertEqual(len(manifest['gated_controls']), 12)

    def test_saved_model_seed_replays_exact_accepted_native_evidence(self):
        base = sources(ROOT / 'seed/workspace')
        self.assertEqual(review_native.hashes(base), build.SEED_HASHES)
        manifest = read(ROOT / 'seed/source-manifest.json')
        self.assertEqual(manifest['chain_id'], 'aws-lineage-01')
        self.assertEqual((manifest['parent_slot'], manifest['accepted_slot']), ('slot-02', 'slot-04'))
        evidence = ROOT / 'seed/evidence/slot-04'
        profile = read(evidence / 'native-profile.json')
        record = read(evidence / 'native/record.json')
        raw = {p.relative_to(evidence / 'native/raw').as_posix(): p.read_bytes()
               for p in (evidence / 'native/raw').rglob('*') if p.is_file()}
        pins = review_native.EvidencePins(profile_sha256=build.sha(build.canonical(profile)),
            record_sha256=build.sha(build.canonical(record)),
            source_revision_sha256=build.sha(build.canonical(build.SEED_HASHES)),
            raw_sha256=tuple(sorted(record['raw_sha256'].items())),
            run_id=record['run_id'], origin='model_candidate')
        replay = review_native.review(profile, base, record, raw, pins)
        self.assertTrue(replay['qualified_success'])
        self.assertEqual((replay['passed_units'], replay['failed_units'], replay['warnings']), (77, 0, 0))
        self.assertFalse(replay['synthetic'])
        self.assertEqual(Counter(u['name'] for u in replay['units']), Counter(manifest['inherited_native_units']))
        old = build.REPO / 'experiments/dafny-real-library-growth-001/common'
        for name in ('guard.py', 'review_native.py'):
            self.assertEqual((ROOT / 'compatibility' / name).read_bytes(), (old / name).read_bytes())

    def test_every_candidate_has_one_fixed_body_and_exact_full_scope(self):
        base = sources(ROOT / 'seed/workspace')
        cases = read(ROOT / 'cases.json')
        self.assertEqual(len(cases), 14)
        self.assertEqual(Counter(c['expected_category'] for c in cases),
                         Counter({'PROOF_PASS': 2, 'PROOF_FAILURE': 10, 'COVERAGE_OMISSION': 2}))
        for case in cases:
            task = build.TASKS[case['project']]
            profile = read(ROOT / 'profiles' / (case['project'] + '.json'))
            self.assertEqual((profile['project'], profile['stage'], profile['stage_id']),
                             (case['project'], 1, case['project']))
            self.assertIsNone(profile['parent_requirement'])
            self.assertEqual(profile['base_source_sha256'], build.SEED_HASHES)
            actual = sources(ROOT / case['workspace_dir'])
            self.assertEqual(review_native.hashes(actual), case['source_sha256'])
            self.assertEqual(len(actual), 6)
            self.assertEqual(build.closure(case['command_files'], actual),
                             set(actual) - set(case['omit_from_command']))
            template = (ROOT / 'templates' / Path(task['path']).name).read_bytes()
            prefix, empty, suffix = build.parts(template)
            self.assertEqual(empty, b'')
            actual_prefix, _, actual_suffix = build.parts(actual[task['path']])
            self.assertEqual((actual_prefix, actual_suffix), (prefix, suffix))
            body = (ROOT / 'bodies' / (case['body_id'] + '.txt')).read_text()
            if case['deliberately_mutated_seed_files']:
                supplied = {n: b for n, b in actual.items() if n != task['path']}
                with self.assertRaisesRegex(review_native.EvidenceError, 'Stage-one source identity'):
                    guard.reconstruct(profile, body, supplied, 'offline-fixture')
                for name in case['deliberately_mutated_seed_files']:
                    old_parts, new_parts = build.parts(base[name]), build.parts(supplied[name])
                    self.assertEqual((old_parts[0], old_parts[2]), (new_parts[0], new_parts[2]))
                    self.assertNotEqual(old_parts[1], new_parts[1])
                self.assertFalse(case['child_outcome_predetermined'])
            else:
                rebuilt, audit = guard.reconstruct(profile, body, base, 'offline-fixture')
                self.assertEqual(rebuilt, actual)
                self.assertFalse(audit['acceptance_issued'])
            self.assertEqual(case['native_status'], 'UNKNOWN')
            self.assertIsNone(case['actual_native_unit_labels'])

    def test_omitted_bad_tasks_are_staged_but_not_reached(self):
        cases = read(ROOT / 'cases.json')
        for task_id, task in build.TASKS.items():
            omitted = next(c for c in cases if c['id'] == task['stem'] + '-omitted')
            failed = next(c for c in cases if c['id'] == task['stem'] + '-always-failure')
            self.assertEqual(omitted['source_sha256'], failed['source_sha256'])
            self.assertEqual(omitted['command_files'], build.BASE_ORDER)
            self.assertIn(task['path'], omitted['source_sha256'])
            self.assertEqual(omitted['expected_native_category'], 'PROOF_PASS')
            self.assertEqual(omitted['expected_category'], 'COVERAGE_OMISSION')
            self.assertEqual(omitted['omitted_targets'], [task['target']])
            self.assertIn(task['target'], omitted['required_targets'])
            self.assertEqual(omitted['omitted_source_all_units'], [task['path']])

    def test_guard_blocks_scope_and_trust_bypasses(self):
        profile = read(ROOT / 'profiles/aws-batch.json')
        base = sources(ROOT / 'seed/workspace')
        for body in ('assume false; Failure("x")', '{:verify false} Failure("x")',
                     '} function method Escape(): bool { true } {',
                     'while true decreases * {}', 'include "extra.dfy"',
                     '    // END REPLACEMENT\nFailure("x")'):
            with self.subTest(body=body), self.assertRaises(review_native.EvidenceError):
                guard.reconstruct(profile, body, base, 'offline-fixture')
        for path in (ROOT / 'templates').glob('*.dfy'):
            text = path.read_text()
            self.assertNotRegex(text, r'\b(?:assume|axiom|admit|extern|external_body)\b|decreases\s*\*|verify\s+false')
        counted = (ROOT / 'templates/RepoDiscoFrameBatch.dfy').read_text()
        self.assertEqual(counted.count('    decreases count\n'), 2)
        self.assertEqual(counted.count('    decreases |payloads|\n'), 2)
        self.assertEqual((guard.MAX_BYTES, guard.MAX_TOKENS, guard.MAX_DEPTH), (65536, 32768, 128))

    def test_counted_finite_boundaries_and_exact_reencoding(self):
        for malformed in (b'', b'\xff', b'\xff\xff', b'\x00\x03a'):
            self.assertEqual(decode_counted(malformed, 0), ([], malformed))
            self.assertIsNone(decode_counted(malformed, 1))
        payloads = [b'', b'\x00\xff', b'z' * 65535]
        suffix = b'\xffmalformed suffix'
        data = b''.join(map(encode_frame, payloads)) + suffix
        for count in range(4):
            actual = decode_counted(data, count)
            expected_payloads = payloads[:count]
            expected_rest = b''.join(map(encode_frame, payloads[count:])) + suffix
            self.assertEqual(actual, (expected_payloads, expected_rest))
            self.assertEqual(b''.join(map(encode_frame, actual[0])) + actual[1], data)
        self.assertIsNone(decode_counted(data, 4))
        self.assertEqual(decode_counted(encode_frame(b'') * 257, 257), ([b''] * 257, b''))
        rng = random.Random(773)
        for _ in range(100):
            frames = [bytes(rng.randrange(256) for _ in range(rng.randrange(9)))
                      for _ in range(rng.randrange(7))]
            suffix = bytes(rng.randrange(256) for _ in range(rng.randrange(5)))
            encoded = b''.join(map(encode_frame, frames)) + suffix
            self.assertEqual(decode_counted(encoded, len(frames)), (frames, suffix))
            if frames:
                truncated = b''.join(map(encode_frame, frames))[:-1]
                self.assertIsNone(decode_counted(truncated, len(frames)))

    def test_tagged_finite_failure_conditions_and_budget_boundary(self):
        tag, left, right, rest = 255, b'abc', b'\x00z', b'untouched\xff'
        data = encode_frame(bytes([tag]) + left) + encode_frame(right) + rest
        self.assertEqual(decode_tagged(data, tag, 5), (left, right, rest))
        self.assertEqual(decode_tagged(data, tag, 1000), (left, right, rest))
        self.assertIsNone(decode_tagged(data, tag, 4))
        self.assertIsNone(decode_tagged(data, tag - 1, 5))
        self.assertIsNone(decode_tagged(encode_frame(b'') + encode_frame(b''), tag, 0))
        self.assertEqual(decode_tagged(encode_frame(b'\xff') + encode_frame(b'') + b'\xff', 255, 0),
                         (b'', b'', b'\xff'))
        self.assertIsNone(decode_tagged(encode_frame(b'\xff') + b'\x00\x02a', 255, 10))
        maximal = b'\x07' + b'p' * 65534
        self.assertEqual(decode_tagged(encode_frame(maximal) + encode_frame(b''), 7, 65534),
                         (maximal[1:], b'', b''))
        result = decode_tagged(data, tag, 5)
        self.assertEqual(encode_frame(bytes([tag]) + result[0]) + encode_frame(result[1]) + result[2], data)

    def test_deliberate_wrong_returns_have_concrete_semantic_witnesses(self):
        frames, rest = [b'a', b'bc'], b'tail'
        data = b''.join(map(encode_frame, frames)) + rest
        correct = decode_counted(data, 2)
        self.assertNotEqual(([frames[0]], encode_frame(frames[1]) + rest), correct)
        self.assertNotEqual((list(reversed(frames)), rest), correct)
        self.assertNotEqual((frames, b''), correct)
        self.assertIsNotNone(decode_counted(b'broken', 0))  # Always-failure is invalid.
        tagged = encode_frame(b'\x07a') + encode_frame(b'b') + rest
        self.assertIsNone(decode_tagged(tagged, 8, 2))  # Skipping tag incorrectly accepts.
        self.assertIsNone(decode_tagged(tagged, 7, 1))  # Skipping budget incorrectly accepts.
        self.assertNotEqual((b'\x07a', b'b', rest), decode_tagged(tagged, 7, 2))
        self.assertIsNotNone(decode_tagged(tagged, 7, 2))  # Always-failure is invalid.


if __name__ == '__main__':
    unittest.main(verbosity=2)
