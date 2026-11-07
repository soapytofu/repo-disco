"""Offline fake-transport checks for spending limits, replay and immutable proofs."""
import copy
from pathlib import Path
import shutil
import tempfile
import unittest
from unittest.mock import patch
import run_pilot as r
import bounded_requests as bounded


class RunnerTests(unittest.TestCase):
    def setUp(self):
        self.plan, self.tasks, self.trials = r.validate_bundle()
        self.sent, self.checked = [], []

    def response(self, index, **changes):
        trial = self.trials[index]
        task = next(t for t in self.tasks if t['task_id'] == trial['task_id'])
        import json
        text = json.dumps({name: '\n' for name in task['editable_files']})
        result = dict(text=text, request_id=f'fake-{index}', retry_attempts=0,
                      stop_reason='end_turn', usage=dict(inputTokens=1, outputTokens=2, totalTokens=3))
        result.update(changes)
        result['content'] = [dict(text=result['text'])]
        result['raw_response'] = dict(
            output=dict(message=dict(content=result['content'])), usage=result['usage'],
            stopReason=result['stop_reason'],
            ResponseMetadata=dict(RequestId=result['request_id'], RetryAttempts=result['retry_attempts']))
        return result

    def transport(self, request):
        index = len(self.sent)
        self.assertEqual(request, r.load(r.ROOT / 'frozen-001' / self.trials[index]['request_path']))
        self.sent.append(copy.deepcopy(request))
        return self.response(index)

    def verifier(self, files, code=0):
        self.checked.append(copy.deepcopy(files))
        return dict(exit_code=code, source_sha256=r.hashes(files),
                    stdout='Dafny program verifier finished with 14 verified, 0 errors\n',
                    stderr='', attempts=1, model_calls=0, elapsed_seconds=0.1,
                    command=['timeout', '-k', '5s', '60s', 'dafny', 'verify', '--verify-included-files', 'All.dfy'])

    def collect(self, out, transport=None, verifier=None, **kwargs):
        return r.collect(out, transport or self.transport, verifier or self.verifier, 100,
                         clock=lambda: 0, check_runtime=False, **kwargs)

    def test_exact_eight_requests_repeats_and_fresh_context(self):
        with tempfile.TemporaryDirectory() as d:
            rows = self.collect(d)
            self.assertEqual(len(rows), 8)
            self.assertEqual(len(self.sent), 8)
            self.assertEqual(len(self.checked), 8)
            self.assertEqual(self.sent[0], self.sent[5])
            self.assertEqual(self.sent[1], self.sent[4])
            self.assertEqual(self.sent[2], self.sent[7])
            self.assertEqual(self.sent[3], self.sent[6])
            self.assertTrue(all(len(x['messages']) == 1 for x in self.sent))
            ledger = r.load(Path(d) / 'requests/ledger.json')
            self.assertEqual([x['attempt_id'] for x in ledger['reservations']],
                             [x['trial_id'] for x in self.trials])
            self.assertTrue(ledger['closed'])
            self.assertTrue(r.load(Path(d) / 'summary.json')['all_trials_processed'])

    def test_transport_timeout_stops_and_cannot_resume(self):
        def fail(request):
            self.sent.append(request)
            raise TimeoutError('FAKE')
        with tempfile.TemporaryDirectory() as d:
            rows = self.collect(d, transport=fail)
            self.assertEqual(len(self.sent), 1)
            self.assertEqual(rows[0]['outcome'], 'REQUEST_STOP')
            self.assertEqual(r.load(Path(d) / 'requests/ledger.json')['reservations'][0]['status'],
                             'AMBIGUOUS_OR_UNSAVED')
            with self.assertRaises(FileExistsError):
                self.collect(d)
            self.assertEqual(len(self.sent), 1)

    def test_rejections_and_truncations_consume_all_slots(self):
        for mode in ('OUTPUT_REJECTED', 'OUTPUT_TRUNCATED'):
            self.sent = []
            def invalid(request):
                index = len(self.sent)
                self.sent.append(request)
                changes = {'text': 'not JSON'} if mode == 'OUTPUT_REJECTED' else {'stop_reason': 'max_tokens'}
                return self.response(index, **changes)
            with tempfile.TemporaryDirectory() as d:
                rows = self.collect(d, transport=invalid)
                self.assertEqual(len(self.sent), 8)
                self.assertEqual({x['outcome'] for x in rows}, {mode})
                self.assertFalse(self.checked)

    def test_verifier_failure_classification_and_timeouts(self):
        for code, expected, count in [(4, 'PROOF_FAILURE', 8), (2, 'FRONTEND_ERROR', 8),
                                       (124, 'VERIFIER_STOP', 1)]:
            self.sent, self.checked = [], []
            with tempfile.TemporaryDirectory() as d:
                rows = self.collect(d, verifier=lambda fs: self.verifier(fs, code))
                self.assertEqual(len(self.sent), count)
                self.assertEqual({x['outcome'] for x in rows}, {expected})
        warning = self.verifier({})
        warning.update(exit_code=2, stderr='program.dfy(1,0): Warning: missing trigger\n'
                       'Compilation failed because warnings were found and --allow-warnings is false')
        self.assertEqual(r.outcome_for_evidence(warning), 'WARNING_ONLY')
        warning['stdout'] = 'unresolved identifier'
        self.assertEqual(r.outcome_for_evidence(warning), 'FRONTEND_ERROR')

    def test_metadata_errors_stop(self):
        for duplicate in (True, False):
            self.sent, self.checked = [], []
            def invalid(request):
                index = len(self.sent)
                self.sent.append(request)
                return self.response(index, request_id='same', retry_attempts=0 if duplicate else 1)
            with tempfile.TemporaryDirectory() as d:
                rows = self.collect(d, transport=invalid)
                self.assertEqual(len(self.sent), 2 if duplicate else 1)
                self.assertEqual(rows[-1]['outcome'], 'REQUEST_METADATA_STOP')

    def test_runtime_drift_stops_before_next_request(self):
        times = []
        def validate(root):
            times.append(root)
            if len(times) == 3:
                raise ValueError('fake runtime drift')
        with tempfile.TemporaryDirectory() as d, patch.object(r, 'validate_runtime', side_effect=validate):
            with self.assertRaises(ValueError):
                r.collect(d, self.transport, self.verifier, 100, clock=lambda: 0)
            self.assertEqual(len(self.sent), 1)
            self.assertEqual(r.load(Path(d) / 'summary.json')['reserved_calls'], 1)

    def test_sdk_attempts_and_payload(self):
        request = r.load(r.ROOT / 'frozen-001' / self.trials[0]['request_path'])
        seen = {}
        response = self.response(0)
        class Client:
            def converse(self, **kwargs):
                seen['payload'] = kwargs
                return response['raw_response']
        def factory(service, **kwargs):
            seen.update(service=service, config=kwargs['config'])
            return Client()
        reply = bounded.bedrock_transport(self.plan, client_factory=factory,
                                           config_factory=lambda **kwargs: kwargs)(request)
        self.assertEqual(seen['config']['retries']['total_max_attempts'], 1)
        self.assertEqual(seen['payload'], request)
        self.assertEqual(reply['retry_attempts'], 0)

    def test_deadline_after_each_reservation_step(self):
        for ticks in ([2], [0, 0, 2], [0, 0, 0, 0, 2]):
            clock = iter(ticks)
            with tempfile.TemporaryDirectory() as d:
                gate = bounded.RequestGate(Path(d) / 'requests', 8, 1, self.transport,
                                           clock=lambda: next(clock))
                with self.assertRaises(bounded.GateClosed):
                    gate.invoke({}, task_id='t', attempt_id='a')
                self.assertFalse(self.sent)
                self.assertTrue(gate.closed)
                self.assertTrue(all('dispatch_started_at_epoch' not in x for x in gate.state['reservations']))

    def test_spending_cap_and_persistence_failure(self):
        with tempfile.TemporaryDirectory() as d:
            sent = []
            gate = bounded.RequestGate(Path(d) / 'limit', 1, 100, lambda p: sent.append(p) or {}, clock=lambda: 0)
            gate.invoke({}, task_id='t', attempt_id='a')
            with self.assertRaises(bounded.GateClosed):
                gate.invoke({}, task_id='t', attempt_id='b')
            self.assertEqual(len(sent), 1)
            gate = bounded.RequestGate(Path(d) / 'disk', 8, 100, lambda p: sent.append(p) or {}, clock=lambda: 0)
            with patch.object(bounded, 'durable_json', side_effect=OSError('FAKE DISK')):
                with self.assertRaises(OSError):
                    gate.invoke({}, task_id='t', attempt_id='a')
            with self.assertRaises(bounded.GateClosed):
                gate.invoke({}, task_id='t', attempt_id='b')
            self.assertEqual(len(sent), 1)

    def test_response_persistence_failure_closes_gate(self):
        original = bounded.durable_json
        def write(path, value):
            if path.name.startswith('response-'):
                raise OSError('FAKE')
            original(path, value)
        with tempfile.TemporaryDirectory() as d:
            sent = []
            gate = bounded.RequestGate(Path(d) / 'requests', 8, 100, lambda p: sent.append(p) or {}, clock=lambda: 0)
            with patch.object(bounded, 'durable_json', side_effect=write):
                with self.assertRaises(OSError):
                    gate.invoke({}, task_id='t', attempt_id='a')
            with self.assertRaises(bounded.GateClosed):
                gate.invoke({}, task_id='t', attempt_id='b')
            self.assertEqual(len(sent), 1)

    def test_authorization_and_seed_pins(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            (root / 'runtime-freeze.json').write_text('{}')
            auth = dict(authorized=True, max_calls=8, automatic_retries=False, reassign_unused=False,
                        authorization_basis='FAKE TEST', expires_at_epoch=100,
                        proposal_freeze_sha256=r.PROPOSAL_SHA,
                        runtime_freeze_sha256=r.sha(root / 'runtime-freeze.json'))
            bounded.durable_json(root / 'authorization.json', auth)
            self.assertEqual(r.validate_authorization(root, 0)[1], 100)
            for change in ({'max_calls': 9}, {'automatic_retries': True}, {'expires_at_epoch': 0},
                           {'runtime_freeze_sha256': 'wrong'}, {'reassign_unused': True}):
                bounded.durable_json(root / 'authorization.json', dict(auth, **change))
                with self.assertRaises(ValueError):
                    r.validate_authorization(root, 0)
            shutil.copytree(r.ROOT / 'inputs', root / 'inputs')
            shutil.copytree(r.ROOT / 'frozen-001', root / 'frozen-001')
            candidate = root / 'inputs' / r.TASK_PATH / 'fixtures' / self.tasks[0]['task_id'] / 'empty/ClientA.dfy'
            candidate.write_text(candidate.read_text() + '\n')
            with self.assertRaises(ValueError):
                r.validate_bundle(root)

    def test_reference_replay_and_contract_rejection(self):
        guard = r.guard_module(r.ROOT)
        import json
        for task in self.tasks:
            seed = r.sources(r.ROOT, task)
            bodies = {}
            for name in task['editable_files']:
                prefix, suffix = guard.split_seed(seed[name].decode())
                reference = (r.ROOT / 'inputs' / r.TASK_PATH / 'fixtures' / task['task_id'] / 'reference' / name).read_text()
                bodies[name] = reference[len(prefix):-len(suffix)]
            with tempfile.TemporaryDirectory() as d:
                response = dict(text=json.dumps(bodies))
                result = r.evaluate(task, seed, response, Path(d), self.verifier, guard)
                self.assertEqual(result['outcome'], 'VERIFIED')  # Fake verifier, exact reconstruction only.
                for name, original in seed.items():
                    if name not in task['editable_files']:
                        self.assertEqual(self.checked[-1][name], original)
            for body in ('assume false;', 'lemma Prove() ensures true {}'):
                with tempfile.TemporaryDirectory() as d:
                    response = dict(text=json.dumps({n: body for n in bodies}))
                    result = r.evaluate(task, seed, response, Path(d), self.verifier, guard)
                    self.assertEqual(result['outcome'], 'OUTPUT_REJECTED')

    def test_review_roundtrip_and_tamper(self):
        from review_results import review
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            shutil.copytree(r.ROOT / 'inputs', root / 'inputs')
            shutil.copytree(r.ROOT / 'frozen-001', root / 'frozen-001')
            for name in r.RUNTIME_FILES:
                if (r.ROOT / name).exists():
                    shutil.copy2(r.ROOT / name, root / name)
                else:
                    (root / name).write_text('FAKE TEST LOG')
            pins = dict(proposal_freeze_sha256=r.PROPOSAL_SHA, max_calls=8, automatic_retries=False,
                        reassign_unused=False, runtime_sha256={n: r.sha(root/n) for n in sorted(r.RUNTIME_FILES)})
            bounded.durable_json(root / 'runtime-freeze.json', pins)
            auth = dict(authorized=True, max_calls=8, automatic_retries=False, reassign_unused=False,
                        proposal_freeze_sha256=r.PROPOSAL_SHA, expires_at_epoch=100,
                        runtime_freeze_sha256=r.sha(root / 'runtime-freeze.json'))
            out = root / 'model-001'
            out.mkdir()
            r.archive_runtime(root, out, auth)
            bounded.durable_json(out / 'environment.json', dict(
                dafny=self.plan['verifier']['toolchain'], z3=self.plan['verifier']['z3'],
                job_id='FAKE', host='fake-compute'))
            def mixed(request):
                response = self.transport(request)
                index = len(self.sent)-1
                if index % 4 == 1:
                    return self.response(index, text='bad JSON')
                if index % 4 == 2:
                    return self.response(index, stop_reason='max_tokens')
                return response
            r.collect(out, mixed, self.verifier, 100, root=root, clock=lambda: 0)
            report = review(root)
            self.assertTrue(report['all_completed'])
            self.assertEqual(report['returned'], 8)
            self.assertEqual(report['verified'], 4)
            self.assertEqual(report['outcomes'], dict(VERIFIED=4, OUTPUT_REJECTED=2, OUTPUT_TRUNCATED=2))
            self.assertTrue(all(c['planned'] == c['reserved'] == 2 for c in report['cells']))
            path = out / 'monotone-01/candidate/ClientA.dfy'
            path.write_text(path.read_text() + '\n')
            with self.assertRaises(ValueError):
                review(root)


if __name__ == '__main__':
    unittest.main(verbosity=2)
