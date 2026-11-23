"""Offline source-bound control construction checks, not native proof tests."""
import hashlib
import json
from pathlib import Path
import sys
import unittest

HERE = Path(__file__).resolve().parent
PACKAGE = HERE.parent
sys.path.insert(0, str(HERE / 'protocol'))
import guard

TARGET = 'growth/SpliceRange.dfy'
HELPER = 'growth/AppendAll.dfy'
BEGIN = b'    // BEGIN REPLACEMENT\n'
END = b'    // END REPLACEMENT'
IDS = ['splice-retains-old-content', 'splice-unproved-seed-rebuild']


def read(path):
    return json.loads(path.read_bytes())


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def source_map(path):
    return {p.relative_to(path).as_posix(): p.read_bytes() for p in sorted(path.rglob('*.dfy'))}


def body(raw):
    return raw.split(BEGIN, 1)[1].split(END, 1)[0].decode()


class ConstructionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.cases = read(HERE / 'cases.json')
        cls.reference = source_map(HERE / 'origins/reference')
        cls.revision = read(HERE / 'revision.json')
        cls.profile = read(HERE / 'profiles/stdlib-splice.json')

    def test_manifest_and_exact_copied_protocol(self):
        manifest = read(HERE / 'manifest.json')
        self.assertFalse(manifest['native_qualification'])
        for name, digest in manifest['files'].items():
            self.assertEqual(sha((HERE / name).read_bytes()), digest, name)
        for name, entry in self.revision['copy_origins'].items():
            self.assertEqual(sha((HERE / name).read_bytes()), entry['sha256'], name)

    def test_only_two_cases_all_five_inputs_and_unchanged_limits(self):
        self.assertEqual([c['id'] for c in self.cases], IDS)
        for case in self.cases:
            sources = source_map(HERE / case['workspace_dir'])
            self.assertEqual({n:sha(raw) for n,raw in sources.items()}, case['source_sha256'])
            self.assertEqual(set(sources), set(self.reference))
            self.assertEqual(len(sources), 5)
            self.assertEqual(case['declared_scope_files'], case['command_files'])
            self.assertEqual(case['argv'][-5:], case['command_files'])
            self.assertEqual(case['argv'][case['argv'].index('--cores')+1], '1')
            self.assertEqual(case['argv'][case['argv'].index('--resource-limit')+1], '1000000')
            self.assertEqual(case['argv'][case['argv'].index('--verification-time-limit')+1], '300')
            self.assertEqual(case['native_status'], 'UNKNOWN')
            self.assertFalse(case['model_acceptance'])
            self.assertEqual(sha(body(sources[TARGET]).encode()), case['body_sha256'])

    def test_retained_content_removes_exact_clearing_loop_only(self):
        case = self.cases[0]
        sources = source_map(HERE / case['workspace_dir'])
        text = self.reference[TARGET].decode()
        begin = text.index('    while a.size > 0\n')
        end = text.index('    Append.AppendAll(a,\n', begin)
        self.assertEqual(text[begin:end].count('a.PopFast();'), 1)
        self.assertEqual(sources[TARGET], (text[:begin]+text[end:]).encode())
        self.assertEqual([n for n in sources if sources[n] != self.reference[n]], [TARGET])
        self.assertEqual(case['expected_failed_targets'], ['RepoDiscoSplice.Splice'])
        self.assertEqual(case['expected_passed_targets'], ['RepoDiscoStdAppend.AppendAll'])

    def test_guard_reconstructs_retained_content_exactly(self):
        case = self.cases[0]
        sources = source_map(HERE / case['workspace_dir'])
        base = {name:sources[name] for name in self.profile['base_source_sha256']}
        rebuilt, receipt = guard.reconstruct(self.profile, body(sources[TARGET]), base, 'offline-control-construction')
        self.assertEqual(rebuilt, sources)
        self.assertFalse(receipt['acceptance_issued'])

    def test_unproved_helper_uses_exact_old_mutant_and_exact_proved_caller(self):
        case = self.cases[1]
        sources = source_map(HERE / case['workspace_dir'])
        self.assertEqual(sources[TARGET], self.reference[TARGET])
        self.assertEqual(sources[HELPER], (HERE/'origins/old-helper-mutant.dfy').read_bytes())
        self.assertEqual([n for n in sources if sources[n] != self.reference[n]], [HELPER])
        self.assertEqual(case['expected_failed_targets'], ['RepoDiscoStdAppend.AppendAll'])
        self.assertEqual(case['expected_passed_targets'], ['RepoDiscoSplice.Splice'])
        self.assertFalse(case['protected_source_candidate'])

    def test_helper_mutation_is_ineligible_under_real_model_guard(self):
        sources = source_map(HERE / self.cases[1]['workspace_dir'])
        base = {name:sources[name] for name in self.profile['base_source_sha256']}
        with self.assertRaisesRegex(guard.EvidenceError, 'source identity'):
            guard.reconstruct(self.profile, body(sources[TARGET]), base, 'offline-control-construction')

    def test_headers_upstream_and_reference_pins_are_unchanged(self):
        for name, expected in self.revision['input_pins'].items():
            self.assertEqual(sha((PACKAGE/name).read_bytes()), expected, name)
        self.assertEqual({n:sha(raw) for n,raw in self.reference.items()}, self.revision['reference_source_sha256'])
        for case in self.cases:
            sources = source_map(HERE / case['workspace_dir'])
            for name in sources:
                if name not in (TARGET,HELPER):
                    self.assertEqual(sources[name], self.reference[name])
                else:
                    self.assertEqual(sources[name].split(BEGIN,1)[0], self.reference[name].split(BEGIN,1)[0])
                    self.assertEqual(sources[name].split(END,1)[1], self.reference[name].split(END,1)[1])

    def test_resource_failures_are_preserved_and_never_relabelled(self):
        revision = self.revision
        self.assertEqual(revision['active_matrix_cases'],30)
        self.assertEqual(revision['expanded_historical_catalog'],33)
        self.assertEqual(revision['unchanged_matching_prior_controls'],24)
        self.assertEqual(revision['new_control_observations'],2)
        previous = read(PACKAGE/'qualification-002/reviews/native-stdlib-001.json')
        for entry in revision['excluded_prior_control_observations']:
            observation = next(c for c in previous['observations'] if c['case_id']==entry['case_id'])
            self.assertEqual(entry['original_expected_category'],'PROOF_FAILURE')
            self.assertEqual(entry['actual_category'],'RESOURCE_FAILURE')
            self.assertEqual(observation['observation']['category'],entry['actual_category'])
            self.assertFalse(observation['expectation']['expected_match'])
            self.assertFalse(entry['rerun_enabled'])
            self.assertFalse(entry['rescored'])


if __name__=='__main__':
    unittest.main(verbosity=2)
