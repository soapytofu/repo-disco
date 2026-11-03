"""Evidence-link and diagnostic classification checks, without subprocesses."""
import unittest

from body_guard import digest
from evidence_audit import audit, classify_existing_evidence, exact_hashes


def evidence(code=0, verified=1, errors=0, prefix='', suffix=''):
    return dict(exit_code=code, stdout=prefix + '\nDafny program verifier finished with '
                + str(verified) + ' verified, ' + str(errors) + ' errors\n' + suffix, stderr='')


class EvidenceAuditTests(unittest.TestCase):
    def test_saved_evidence_links_without_new_verification(self):
        report = audit()
        self.assertEqual(len(report['saved_responses']), 24)
        self.assertEqual(len(report['fixture_controls']), 128)
        self.assertEqual(report['original_pilot_score'], '18/24 unchanged')
        self.assertEqual(report['new_model_calls'], 0)
        self.assertEqual(report['new_verifier_invocations'], 0)
        # The original trial 03 is still the failing proof, not the analyst repair.
        third = report['saved_responses'][2]
        self.assertEqual(third['original_outcome'], 'PROOF_FAILURE')
        self.assertEqual(third['prior_semantic_evidence']['category'], 'assertion_failure')
        self.assertNotIn('single-fact-repair', third['evidence_path'])

    def test_exact_file_set_and_source_bytes_are_required(self):
        source = {'All.dfy': 'include "Helper.dfy"\n', 'Helper.dfy': 'module Helper {}\n'}
        recorded = {'source_sha256': {name: digest(text) for name, text in source.items()}}
        self.assertEqual(exact_hashes(source, recorded), recorded['source_sha256'])
        for changed in [dict(source, **{'Helper.dfy': 'module Helper {}'}),
                        {'All.dfy': source['All.dfy']}, dict(source, **{'Extra.dfy': ''})]:
            with self.assertRaises(ValueError): exact_hashes(changed, recorded)

    def test_zero_errors_substring_cannot_match_ten_errors(self):
        self.assertEqual(classify_existing_evidence(evidence())['category'], 'strict_success')
        for bad in [evidence(errors=10), evidence(code=4, errors=10), evidence(code=124),
                    evidence(prefix='Helper.dfy(1,1): Error: assertion might not hold')]:
            with self.assertRaises(ValueError): classify_existing_evidence(bad)

    def test_warning_only_is_separate_and_never_strict_success(self):
        warning = 'Helper.dfy(1,1): Warning: Could not find a trigger for this quantifier.\n'
        strict = 'Compilation failed because warnings were found and --allow-warnings is false\n'
        result = classify_existing_evidence(evidence(2, prefix=warning, suffix=strict))
        self.assertEqual(result['category'], 'warning_only_nonzero_exit')
        self.assertEqual(result['diagnostic_warnings'], 1)
        for bad in [evidence(2, prefix=warning), evidence(2, suffix=strict),
                    evidence(0, prefix=warning), evidence(2, errors=1, prefix=warning, suffix=strict)]:
            with self.assertRaises(ValueError): classify_existing_evidence(bad)

    def test_parse_errors_and_ambiguous_summaries_do_not_become_proof_failures(self):
        failure = evidence(4, errors=1, prefix='Helper.dfy(1,1): Error: assertion might not hold')
        self.assertEqual(classify_existing_evidence(failure)['category'], 'assertion_failure')
        parse = dict(failure, stdout=failure['stdout'] + '1 parse errors detected\n')
        double = dict(failure, stdout=failure['stdout'] + failure['stdout'])
        missing = dict(failure, stdout='Error: assertion might not hold\n')
        for bad in [parse, double, missing]:
            with self.assertRaises(ValueError): classify_existing_evidence(bad)


if __name__ == '__main__': unittest.main(verbosity=2)
