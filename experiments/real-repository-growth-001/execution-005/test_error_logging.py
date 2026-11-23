"""Synthetic service errors and saved-evidence replay; no key, SDK or network."""
import copy
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import credential_transport as c
import runtime as r
import run_pilot as host
import review
from bounded_requests import GateClosed, RequestGate
import test_runner as fixtures

REPO = fixtures.REPO

DUMMY = 'SYNTHETIC-PRIVATE-BEARER-DO-NOT-ARCHIVE'
PRIOR = 'SYNTHETIC-OLDER-BEARER-DO-NOT-ARCHIVE'


class FakeServiceError(Exception):
    def __init__(self, response):
        super().__init__('UNSAFE-EXCEPTION-REPR '+DUMMY)
        self.response = response


def service_response(code='AccessDeniedException', retries=0):
    return dict(Error=dict(Code=code, Message='Synthetic denial '+DUMMY+' '+PRIOR,
                           Unapproved='DO-NOT-COPY-ERROR-FIELD'),
                ResponseMetadata=dict(RequestId='synthetic-request-id', HTTPStatusCode=403,
                    RetryAttempts=retries, HTTPHeaders={'authorization': 'DO-NOT-COPY-HEADER'}),
                Unapproved='DO-NOT-COPY-TOP-LEVEL')


class ErrorLoggingTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        fixtures.RunnerTests.setUpClass()
        cls.package = fixtures.RunnerTests.package

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.out = Path(self.temp.name)/'simulation'
        self.environment = {c.BEARER_ENV: PRIOR}
        self.loads, self.calls = [], []
        self.native = fixtures.FakeNative()

    def tearDown(self):
        self.temp.cleanup()

    def transport(self, error):
        def loader():
            self.loads.append(True)
            return DUMMY
        def factory(settings):
            def invoke(payload):
                self.calls.append(payload)
                raise error
            return invoke
        return c.ScopedBearerTransport({}, loader, transport_factory=factory, environ=self.environment)

    def simulate(self, transport, reader=None):
        return host.simulate(REPO, self.out, transport, self.native, deadline=2000,
            acknowledge_synthetic=True, clock=lambda:1000, package=self.package,
            validate=lambda:None, run_id='synthetic-error-run',
            transport_diagnostic=transport.failure_diagnostic if reader is None else reader)

    def replay(self):
        return review.review_run(REPO, self.out, allow_synthetic=True, expected_package=self.package)

    def refresh_manifest(self):
        value={p.relative_to(self.out).as_posix():r.sha(p.read_bytes()) for p in r.archive_files(self.out)}
        (self.out/'archive-manifest.json').write_bytes(r.encode(value))

    def assert_terminal(self, result, error_type='FakeServiceError'):
        self.assertEqual(result['status'],'SYNTHETIC_STOPPED')
        self.assertEqual((result['transport_reservations'],result['completed_responses'],
                          result['ambiguous_or_unsaved'],result['accepted_stages']), (1,0,1,0))
        self.assertEqual(result['fatal']['error_type'],error_type)
        self.assertEqual((len(self.calls),len(self.loads),len(self.native.calls)),(1,1,0))
        self.assertEqual(self.environment[c.BEARER_ENV],PRIOR)
        ledger=r.read(self.out/'requests/ledger.json')
        self.assertTrue(ledger['closed'])
        self.assertEqual(ledger['closed_reason'],'transport_or_response_failure')
        self.assertEqual(result['unused_capacity_never_reassigned'],7)
        self.assertFalse(list((self.out/'requests').glob('response-*.json')))

    def test_service_metadata_is_bound_redacted_and_unscored(self):
        transport=self.transport(FakeServiceError(service_response()))
        result=self.simulate(transport)
        self.assert_terminal(result)
        record=r.read(self.out/'slot-01/transport-error.json')
        provider=record['diagnostic']['provider_error']
        self.assertEqual(provider,dict(Error=dict(Code='AccessDeniedException',
            Message='Synthetic denial [REDACTED] [REDACTED]'),
            ResponseMetadata=dict(RequestId='synthetic-request-id',HTTPStatusCode=403,RetryAttempts=0)))
        self.assertEqual(r.read(self.out/'slot-01/request.json'), self.calls[0])
        for path in r.archive_files(self.out):
            text=path.read_text()
            for forbidden in (DUMMY,PRIOR,'UNSAFE-EXCEPTION-REPR','DO-NOT-COPY'):
                self.assertNotIn(forbidden,text)
        audited=self.replay()
        self.assertFalse(audited['experiment_complete'])
        self.assertIsNone(audited['reservation_audit'][0]['proof_score'])
        self.assertEqual(audited['transport_error_audit']['status'],'SAVED')
        with self.assertRaisesRegex(RuntimeError,'terminal'):transport({})
        self.assertEqual(len(self.calls),1)

    def test_missing_retry_metadata_stays_unknown_and_nonzero_is_preserved(self):
        for retries in (None,2):
            with self.subTest(retries=retries):
                response=service_response(retries=retries)
                if retries is None:response['ResponseMetadata'].pop('RetryAttempts')
                error=FakeServiceError(response)
                transport=self.transport(error)
                with self.assertRaises(FakeServiceError) as caught:transport({})
                self.assertIs(caught.exception,error)
                self.assertIs(transport.failure_diagnostic()['provider_error']['ResponseMetadata']['RetryAttempts'],retries)

    def test_nonservice_exception_has_null_metadata_without_message_inference(self):
        transport=self.transport(TimeoutError('DO-NOT-COPY '+DUMMY))
        result=self.simulate(transport)
        self.assert_terminal(result,'TimeoutError')
        record=r.read(self.out/'slot-01/transport-error.json')
        self.assertEqual(record['diagnostic']['provider_error'],c.empty_provider_error())
        self.assertIsNone(self.replay()['reservation_audit'][0]['proof_score'])

    def test_response_property_failure_preserves_original_exception(self):
        class BadResponseError(Exception):
            @property
            def response(self):raise RuntimeError('DO-NOT-COPY '+DUMMY)
        error=BadResponseError('DO-NOT-COPY')
        transport=self.transport(error)
        with self.assertRaises(BadResponseError) as caught:transport({})
        self.assertIs(caught.exception,error)
        self.assertEqual(transport.failure_diagnostic()['capture_status'],'EXTRACTION_FAILED')
        self.assertEqual(transport.failure_diagnostic()['provider_error'],c.empty_provider_error())
        self.assertEqual(self.environment[c.BEARER_ENV],PRIOR)

    def test_extractor_failure_does_not_replace_original_or_reopen_gate(self):
        error=FakeServiceError(service_response())
        transport=self.transport(error)
        gate=RequestGate(self.out,8,2000,transport,clock=lambda:1000)
        with patch.object(c,'extract_provider_error',side_effect=SystemExit('DO-NOT-COPY')):
            with self.assertRaises(FakeServiceError) as caught:gate.invoke({},task_id='vmc-move',attempt_id='slot-01')
        self.assertIs(caught.exception,error)
        self.assertTrue(gate.closed)
        self.assertEqual(transport.failure_diagnostic()['capture_status'],'EXTRACTION_FAILED')
        with self.assertRaises(GateClosed):gate.invoke({},task_id='vmc-move',attempt_id='slot-02')
        self.assertEqual(len(self.calls),1)

    def test_capture_boundary_failure_still_preserves_original(self):
        error=FakeServiceError(service_response());transport=self.transport(error)
        with patch.object(c,'capture_failure',side_effect=KeyboardInterrupt('DO-NOT-COPY')):
            with self.assertRaises(FakeServiceError) as caught:transport({})
        self.assertIs(caught.exception,error)
        self.assertIsNone(transport.failure_diagnostic())
        self.assertEqual(self.environment[c.BEARER_ENV],PRIOR)
        with self.assertRaisesRegex(RuntimeError,'terminal'):transport({})
        self.assertEqual(len(self.calls),1)

    def test_host_diagnostic_reader_failure_is_terminal_and_reported(self):
        transport=self.transport(FakeServiceError(service_response()))
        def broken():raise KeyboardInterrupt('DO-NOT-COPY '+DUMMY)
        result=self.simulate(transport,broken)
        self.assert_terminal(result)
        self.assertEqual(result['fatal']['transport_diagnostic']['status'],'CAPTURE_FAILED')
        self.assertEqual(self.replay()['transport_error_audit']['status'],'CAPTURE_FAILED')

    def test_diagnostic_write_failure_cannot_mask_error_or_dispatch(self):
        transport=self.transport(FakeServiceError(service_response()))
        write=host.write_bytes
        def fail(path,raw):
            if path.name=='transport-error.json':
                self.assertTrue(r.read(self.out/'requests/ledger.json')['closed'])
                path.write_bytes(raw[:20])
                raise OSError('SYNTHETIC-DISK-FULL')
            return write(path,raw)
        with patch.object(host,'write_bytes',side_effect=fail):result=self.simulate(transport)
        self.assert_terminal(result)
        self.assertEqual(result['fatal']['transport_diagnostic']['status'],'WRITE_FAILED')
        self.assertEqual(self.replay()['transport_error_audit']['status'],'WRITE_FAILED')

    def test_diagnostic_is_written_only_after_gate_is_durably_closed(self):
        transport=self.transport(FakeServiceError(service_response()))
        def read():
            ledger=r.read(self.out/'requests/ledger.json')
            self.assertTrue(ledger['closed'])
            self.assertEqual(ledger['reservations'][0]['status'],'AMBIGUOUS_OR_UNSAVED')
            return transport.failure_diagnostic()
        self.assert_terminal(self.simulate(transport,read))

    def test_reviewer_rejects_missing_saved_diagnostic_even_with_rebuilt_archive(self):
        self.simulate(self.transport(FakeServiceError(service_response())))
        (self.out/'slot-01/transport-error.json').unlink();self.refresh_manifest()
        with self.assertRaisesRegex(ValueError,'Missing or extra saved transport diagnostic'):self.replay()

    def test_reviewer_rejects_stale_bindings_and_extra_fields(self):
        self.simulate(self.transport(FakeServiceError(service_response())))
        path=self.out/'slot-01/transport-error.json';baseline=r.read(path)
        for field,value in [('run_id','synthetic-other-run'),('slot_id','slot-02'),
                            ('request_sha256','0'*64),('reservation_sha256','0'*64),
                            ('runtime_sha256','1'*64),('returned_model_response',True),('proof_score',0)]:
            record=copy.deepcopy(baseline);record[field]=value;path.write_bytes(r.encode(record))
            summary=r.read(self.out/'summary.json');summary['fatal']['transport_diagnostic']['artifact_sha256']=r.sha(path.read_bytes())
            (self.out/'summary.json').write_bytes(r.encode(summary));(self.out/'stop.json').write_bytes(r.encode(summary['fatal']))
            self.refresh_manifest()
            with self.subTest(field=field),self.assertRaisesRegex(ValueError,'terminal unscored reservation'):self.replay()
        record=copy.deepcopy(baseline);record['diagnostic']['provider_error']['SecretField']='unapproved'
        path.write_bytes(r.encode(record));summary['fatal']['transport_diagnostic']['artifact_sha256']=r.sha(path.read_bytes())
        (self.out/'summary.json').write_bytes(r.encode(summary));(self.out/'stop.json').write_bytes(r.encode(summary['fatal']))
        self.refresh_manifest()
        with self.assertRaisesRegex(ValueError,'Invalid bounded transport diagnostic'):self.replay()

    def test_success_does_not_create_diagnostic_and_reads_are_defensive_copies(self):
        transport=c.ScopedBearerTransport({},lambda:DUMMY,transport_factory=lambda _:lambda p:{'ok':True},environ={})
        self.assertEqual(transport({}),{'ok':True});self.assertIsNone(transport.failure_diagnostic())
        failed=self.transport(FakeServiceError(service_response()))
        with self.assertRaises(FakeServiceError):failed({})
        first=failed.failure_diagnostic();first['provider_error']['Error']['Code']='tampered'
        self.assertEqual(failed.failure_diagnostic()['provider_error']['Error']['Code'],'AccessDeniedException')

    def test_pre_dispatch_error_phase_does_not_claim_a_provider_response(self):
        for phase in ('credential_load','client_construction'):
            with self.subTest(phase=phase):
                error=RuntimeError('DO-NOT-COPY')
                def fail(*args):raise error
                transport=c.ScopedBearerTransport({},fail if phase=='credential_load' else lambda:DUMMY,
                    transport_factory=fail,environ={})
                with self.assertRaises(RuntimeError) as caught:transport({})
                self.assertIs(caught.exception,error)
                record=transport.failure_diagnostic()
                self.assertEqual(record['phase'],phase)
                self.assertEqual(record['provider_error'],c.empty_provider_error())


if __name__=='__main__':unittest.main()
