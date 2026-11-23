"""Fake-token/fake-client lifecycle tests; no handoff, SDK or network access."""
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import credential_transport as c
from bounded_requests import RequestGate, GateClosed
from native_host import _native_environment

DUMMY = 'SYNTHETIC-NOT-A-CREDENTIAL'


class CredentialLifecycleTests(unittest.TestCase):
    def test_late_token_resolution_two_calls_one_loader_one_factory(self):
        env = {}; calls = []; loads = []; factories = []
        def load():
            loads.append(True)
            return DUMMY
        def factory(settings):
            self.assertEqual(env[c.BEARER_ENV], DUMMY)
            factories.append(settings)
            def invoke(payload):
                # Model the SDK's request-time lookup, after client creation.
                self.assertEqual(env[c.BEARER_ENV], DUMMY)
                calls.append(payload)
                return {'returned': len(calls)}
            return invoke
        transport = c.ScopedBearerTransport({'frozen': True}, load,
                    transport_factory=factory, environ=env)
        first = {'messages': ['first frozen payload']}
        second = {'messages': ['second actual-parent payload']}
        self.assertEqual(transport(first), {'returned': 1})
        self.assertNotIn(c.BEARER_ENV, env)
        self.assertEqual(transport(second), {'returned': 2})
        self.assertNotIn(c.BEARER_ENV, env)
        self.assertEqual((len(loads), len(factories)), (1, 1))
        self.assertIs(calls[0], first)
        self.assertIs(calls[1], second)

    def test_prior_environment_restored_and_never_forwarded_to_native(self):
        prior = 'SYNTHETIC-OLDER-AMBIENT-TOKEN'
        env = {c.BEARER_ENV: prior, 'PATH': '/synthetic/bin'}
        native_snapshots = []
        def factory(settings):
            self.assertEqual(env[c.BEARER_ENV], DUMMY)
            def invoke(payload):
                native_snapshots.append(_native_environment(env))
                return {'ok': True}
            return invoke
        transport = c.ScopedBearerTransport({}, lambda: DUMMY,
                    transport_factory=factory, environ=env)
        transport({})
        self.assertEqual(env[c.BEARER_ENV], prior)
        self.assertNotIn(c.BEARER_ENV, native_snapshots[0])
        self.assertNotIn(c.BEARER_ENV, _native_environment(env))
        self.assertEqual(native_snapshots[0]['PATH'], '/synthetic/bin')

    def test_factory_and_invocation_exceptions_restore_environment_and_close(self):
        for phase in ('factory', 'invoke'):
            for previous in (None, 'SYNTHETIC-PRIOR'):
                with self.subTest(phase=phase, previous_present=previous is not None):
                    env = {} if previous is None else {c.BEARER_ENV: previous}
                    loads = []; factories = []; invocations = []
                    def loader():
                        loads.append(True)
                        return DUMMY
                    def factory(settings):
                        factories.append(True)
                        self.assertEqual(env[c.BEARER_ENV], DUMMY)
                        if phase == 'factory':
                            raise RuntimeError('Synthetic constructor failure')
                        def invoke(payload):
                            invocations.append(True)
                            self.assertEqual(env[c.BEARER_ENV], DUMMY)
                            raise RuntimeError('Synthetic invocation failure')
                        return invoke
                    transport = c.ScopedBearerTransport({}, loader,
                                transport_factory=factory, environ=env)
                    with self.assertRaises(RuntimeError):
                        transport({})
                    self.assertEqual(env.get(c.BEARER_ENV), previous)
                    with self.assertRaisesRegex(RuntimeError, 'terminal'):
                        transport({})
                    self.assertEqual((len(loads), len(factories)), (1, 1))
                    self.assertEqual(len(invocations), int(phase == 'invoke'))

    def test_invalid_or_failed_loader_never_constructs_client_and_restores(self):
        for loaded in (None, '', 1, 'x' * 65537):
            with self.subTest(kind=type(loaded).__name__, empty=loaded == ''):
                env = {c.BEARER_ENV: 'SYNTHETIC-PRIOR'}
                def forbidden(settings):
                    raise AssertionError('Client construction reached')
                transport = c.ScopedBearerTransport({}, lambda: loaded,
                            transport_factory=forbidden, environ=env)
                with self.assertRaises(ValueError):
                    transport({})
                self.assertEqual(env[c.BEARER_ENV], 'SYNTHETIC-PRIOR')

    def test_handoff_adapter_capture_and_exception_cleanup_use_only_fake_consumer(self):
        for previous in (None, 'SYNTHETIC-PRIOR'):
            with self.subTest(previous_present=previous is not None), patch.dict(os.environ, {}, clear=True):
                if previous is not None:
                    os.environ[c.BEARER_ENV] = previous
                def fake_consume(path):
                    self.assertNotIn(c.BEARER_ENV, os.environ)
                    os.environ[c.BEARER_ENV] = DUMMY
                with patch.object(c, 'consume_key', fake_consume):
                    self.assertEqual(c.load_private_token('/synthetic/not-read'), DUMMY)
                self.assertEqual(os.environ.get(c.BEARER_ENV), previous)
                def failed_consume(path):
                    os.environ[c.BEARER_ENV] = DUMMY
                    raise RuntimeError('Synthetic handoff failure')
                with patch.object(c, 'consume_key', failed_consume), self.assertRaises(RuntimeError):
                    c.load_private_token('/synthetic/not-read')
                self.assertEqual(os.environ.get(c.BEARER_ENV), previous)
                with patch.object(c, 'consume_key', lambda _: None), self.assertRaises(ValueError):
                    c.load_private_token('/synthetic/not-read')
                self.assertEqual(os.environ.get(c.BEARER_ENV), previous)

    def test_reentrant_invocation_is_rejected_without_token_leak(self):
        env = {}; transport = None
        def factory(settings):
            return lambda payload: transport(payload)
        transport = c.ScopedBearerTransport({}, lambda: DUMMY,
                    transport_factory=factory, environ=env)
        with self.assertRaisesRegex(RuntimeError, 'reentrant'):
            transport({})
        self.assertNotIn(c.BEARER_ENV, env)
        with self.assertRaisesRegex(RuntimeError, 'terminal'):
            transport({})

    def test_request_gate_keeps_failed_credential_reservation_closed(self):
        with tempfile.TemporaryDirectory() as temp:
            env = {}; count = []
            def factory(settings):
                def invoke(payload):
                    count.append(True)
                    raise RuntimeError('Synthetic late SDK authentication failure')
                return invoke
            transport = c.ScopedBearerTransport({}, lambda: DUMMY,
                        transport_factory=factory, environ=env)
            gate = RequestGate(Path(temp) / 'requests', 8, 2000, transport, clock=lambda: 1000)
            with self.assertRaises(RuntimeError):
                gate.invoke({}, task_id='vmc-move', attempt_id='slot-01')
            self.assertTrue(gate.closed)
            self.assertEqual(gate.state['reservations'][0]['status'], 'AMBIGUOUS_OR_UNSAVED')
            with self.assertRaises(GateClosed):
                gate.invoke({}, task_id='vmc-move', attempt_id='slot-02')
            self.assertEqual(count, [True])
            self.assertNotIn(c.BEARER_ENV, env)


if __name__ == '__main__':
    unittest.main()
