"""Synthetic-only metadata tests. No actual SDK, provider, credential or I/O."""
import copy
import json
import unittest

import provider_error as adapter


EMPTY = {'Error': {'Code': None, 'Message': None},
         'ResponseMetadata': {'RequestId': None, 'HTTPStatusCode': None, 'RetryAttempts': None}}


class DoNotInspect:
    def __repr__(self):
        raise AssertionError('Object repr must not be inspected')
    def __str__(self):
        raise AssertionError('Object str must not be inspected')
    def __getattr__(self, name):
        raise AssertionError('Arbitrary object attributes must not be inspected')


class ErrorMetadataTests(unittest.TestCase):
    def test_only_allowlisted_fields_are_returned_without_changing_input(self):
        response = {
            'Error': {'Code': 'SyntheticDenied', 'Message': 'Synthetic explanation.', 'Other': 'DROP-ERROR-EXTRA'},
            'ResponseMetadata': {'RequestId': 'synthetic-request-001', 'HTTPStatusCode': 403,
                                 'RetryAttempts': 0, 'HTTPHeaders': {'Authorization': 'DROP-HEADER-TOKEN'}},
            'request': {'body': 'DROP-REQUEST-BODY'}, 'config': 'DROP-CONFIG', 'environment': 'DROP-ENV',
        }
        original = copy.deepcopy(response)
        result = adapter.extract_provider_error(response)
        self.assertEqual(result, {
            'Error': {'Code': 'SyntheticDenied', 'Message': 'Synthetic explanation.'},
            'ResponseMetadata': {'RequestId': 'synthetic-request-001', 'HTTPStatusCode': 403, 'RetryAttempts': 0},
        })
        self.assertEqual(response, original)
        self.assertNotIn('DROP-', json.dumps(result))

    def test_supplied_token_is_redacted_in_every_string_field(self):
        token = 'SYNTHETIC-SECRET-VALUE-123456789'
        response = {'Error': {'Code': token, 'Message': 'Bearer ' + token + '; again ' + token},
                    'ResponseMetadata': {'RequestId': token}}
        result = adapter.extract_provider_error(response, secret_values=[token])
        self.assertEqual(result['Error']['Code'], '[REDACTED]')
        self.assertEqual(result['Error']['Message'], 'Bearer [REDACTED]; again [REDACTED]')
        self.assertEqual(result['ResponseMetadata']['RequestId'], '[REDACTED]')
        self.assertNotIn(token, json.dumps(result))

    def test_overlapping_and_literal_special_character_secrets_are_redacted(self):
        short, long = 'synthetic-token', 'synthetic-token-with-extra-suffix'
        literal = 'FAKE[.*]\\"\nUNICODE-λ'
        message = long + '|' + short + '|' + literal
        result = adapter.extract_provider_error({'Error': {'Message': message}},
                                                secret_values=[short, long, literal])
        self.assertEqual(result['Error']['Message'], '[REDACTED]|[REDACTED]|[REDACTED]')
        for secret in (short, long, literal):
            self.assertNotIn(secret, result['Error']['Message'])

    def test_unknown_objects_and_malformed_fields_are_not_coerced(self):
        opaque = DoNotInspect()
        for value in (None, [], 'not a response', opaque):
            self.assertEqual(adapter.extract_provider_error(value), EMPTY)
        self.assertEqual(adapter.extract_provider_error({'Error': opaque, 'ResponseMetadata': []}), EMPTY)
        response = {'Error': {'Code': opaque, 'Message': opaque},
                    'ResponseMetadata': {'RequestId': opaque, 'HTTPStatusCode': opaque, 'RetryAttempts': opaque}}
        self.assertEqual(adapter.extract_provider_error(response), EMPTY)
        class HostileDict(dict):
            def get(self, *args):
                raise AssertionError('Dict subclass must not be inspected')
        self.assertEqual(adapter.extract_provider_error(HostileDict()), EMPTY)

    def test_absent_fields_stay_unknown_without_inferred_status_or_count(self):
        result = adapter.extract_provider_error({'Error': {'Code': 'AccessDeniedException'}})
        self.assertEqual(result['Error']['Code'], 'AccessDeniedException')
        self.assertIsNone(result['Error']['Message'])
        self.assertEqual(result['ResponseMetadata'], EMPTY['ResponseMetadata'])
        self.assertEqual(adapter.extract_provider_error({}), EMPTY)
        self.assertEqual(adapter.extract_provider_error({'Error': {'Message': ''}})['Error']['Message'], '')

    def test_numeric_fields_require_bounded_integers_and_never_accept_booleans(self):
        for value in (True, False, '403', 403.0, -1, None, {}, 2**100):
            result = adapter.extract_provider_error({'ResponseMetadata': {'HTTPStatusCode': value, 'RetryAttempts': value}})
            self.assertIsNone(result['ResponseMetadata']['HTTPStatusCode'])
            self.assertIsNone(result['ResponseMetadata']['RetryAttempts'])
        for value in (99, 600):
            self.assertIsNone(adapter.extract_provider_error({'ResponseMetadata': {'HTTPStatusCode': value}})['ResponseMetadata']['HTTPStatusCode'])
        self.assertEqual(adapter.extract_provider_error({'ResponseMetadata': {'HTTPStatusCode': 200, 'RetryAttempts': 2}})['ResponseMetadata'],
                         {'RequestId': None, 'HTTPStatusCode': 200, 'RetryAttempts': 2})

    def test_message_is_redacted_before_truncation_and_oversized_input_is_omitted(self):
        token = 'SYNTHETIC-BOUNDARY-TOKEN-12345'
        message = 'x' * (adapter.MAX_MESSAGE_CHARS - 3) + token + 'TAIL'
        result = adapter.extract_provider_error({'Error': {'Message': message}}, secret_values=[token])
        self.assertEqual(len(result['Error']['Message']), adapter.MAX_MESSAGE_CHARS)
        self.assertTrue(result['Error']['Message'].endswith('[RE'))
        self.assertNotIn('SYN', result['Error']['Message'])
        self.assertIsNone(adapter.extract_provider_error({'Error': {'Message': 'x' * (adapter.MAX_RAW_MESSAGE_CHARS + 1)}})['Error']['Message'])
        result = adapter.extract_provider_error({'Error': {'Code': 'x' * 129}, 'ResponseMetadata': {'RequestId': 'x' * 257}})
        self.assertIsNone(result['Error']['Code'])
        self.assertIsNone(result['ResponseMetadata']['RequestId'])

    def test_redaction_marker_cannot_introduce_a_supplied_short_secret(self):
        result = adapter.extract_provider_error({'Error': {'Message': 'Synthetic text', 'Code': 'Synthetic'},
                                                'ResponseMetadata': {'RequestId': 'synthetic'}}, secret_values=['REDACTED'])
        self.assertIsNone(result['Error']['Message'])
        self.assertIsNone(result['Error']['Code'])
        self.assertIsNone(result['ResponseMetadata']['RequestId'])
        # A later replacement can create an earlier, longer secret by joining
        # its marker to adjacent text. Do not return that reconstructed value.
        result = adapter.extract_provider_error({'Error': {'Message': 'tokenfoo'}},
                                                secret_values=['token', 'REDACTED]foo'])
        self.assertIsNone(result['Error']['Message'])

    def test_malformed_secret_arguments_fail_without_representing_them(self):
        for values in ('not-a-sequence', [None], [''], [DoNotInspect()], ['x'] * 65, ['x' * 65537]):
            with self.assertRaises(ValueError):
                adapter.extract_provider_error({}, secret_values=values)


if __name__ == '__main__':
    unittest.main()
