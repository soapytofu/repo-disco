"""Keep the private bearer token in memory and scope its environment visibility.

Some SDK authentication decisions happen when a request is made, after client
construction. The token therefore covers both steps and is removed/restored on
every exit. This module does not construct a client or read a handoff at import.
It must remain behind the durable bounded RequestGate; it never retries.
"""
import os
import threading
import copy

from bounded_requests import bedrock_transport, consume_key
from provider_error import extract_provider_error

BEARER_ENV = 'AWS_BEARER_TOKEN_BEDROCK'
_MISSING = object()


def empty_provider_error():
    return {'Error': {'Code': None, 'Message': None},
            'ResponseMetadata': {'RequestId': None, 'HTTPStatusCode': None, 'RetryAttempts': None}}


def validate_failure_diagnostic(value):
    """Validate an already redacted record; never read credentials or infer fields."""
    if (type(value) is not dict or set(value) != {'schema', 'phase', 'capture_status', 'provider_error'} or
            value['schema'] != 'repodisco-growth-transport-failure-v1' or
            value['phase'] not in ('credential_load', 'client_construction', 'invocation_or_response') or
            value['capture_status'] not in ('EXTRACTED', 'EXTRACTION_FAILED') or
            type(value['provider_error']) is not dict or
            extract_provider_error(value['provider_error']) != value['provider_error'] or
            (value['capture_status'] == 'EXTRACTION_FAILED' and value['provider_error'] != empty_provider_error())):
        raise ValueError('Invalid bounded transport diagnostic')
    return copy.deepcopy(value)


def capture_failure(error, phase, token, previous):
    """Best-effort allowlisted extraction while this transport owns the token.

    Never serialize the exception, traceback, headers, environment or request.
    Literal loaded/previous bearer values are redacted before truncation. An
    extractor/property error cannot replace the original transport exception.
    """
    record = dict(schema='repodisco-growth-transport-failure-v1', phase=phase,
                  capture_status='EXTRACTION_FAILED', provider_error=empty_provider_error())
    try:
        secrets = tuple(value for value in (token, previous)
                        if type(value) is str and 0 < len(value) <= 65536)
        record['provider_error'] = extract_provider_error(getattr(error, 'response', None), secret_values=secrets)
        record['capture_status'] = 'EXTRACTED'
    except BaseException:
        # Do not emit repr/type/message from the failed diagnostic operation.
        pass
    return record


def _restore(environ, previous):
    if previous is _MISSING:
        environ.pop(BEARER_ENV, None)
    else:
        environ[BEARER_ENV] = previous


def _valid_token(value):
    if not isinstance(value, str) or not value or len(value) > 65536:
        raise ValueError('Private bearer token was not loaded')
    return value


def load_private_token(path):
    """Consume the existing handoff once; expose no value in logs or files.

The unchanged handoff helper temporarily writes to os.environ. Capture only the
new value in memory, then restore the caller's prior state even on exceptions.
An ambient token is not a substitute for the separately supplied handoff.
"""
    previous = os.environ.get(BEARER_ENV, _MISSING)
    os.environ.pop(BEARER_ENV, None)
    try:
        consume_key(path)
        return _valid_token(os.environ.get(BEARER_ENV))
    finally:
        _restore(os.environ, previous)


class ScopedBearerTransport:
    """Single-owner, lazy transport with request-time bearer authentication.

token_loader is called at most once. A successful client is reused across the
fixed independent slots, while the environment is restored between calls. Any
loader, factory or invocation error closes this object; the outer RequestGate
also preserves and closes its reservation. Injected loaders/factories are for
explicit offline tests only; production selects the private handoff and the
unchanged no-retry Bedrock transport.
"""
    def __init__(self, settings, token_loader, *, transport_factory=bedrock_transport,
                 environ=None):
        self._settings = settings
        self._token_loader = token_loader
        self._transport_factory = transport_factory
        self._environ = os.environ if environ is None else environ
        self._token = None
        self._backend = None
        self._failed = False
        self._failure_diagnostic = None
        self._lock = threading.Lock()

    def failure_diagnostic(self):
        """Only bounded, already redacted metadata leaves the private transport."""
        return copy.deepcopy(self._failure_diagnostic)

    def __call__(self, payload):
        if not self._lock.acquire(blocking=False):
            raise RuntimeError('Concurrent or reentrant credential transport forbidden')
        previous = self._environ.get(BEARER_ENV, _MISSING)
        try:
            if self._failed:
                raise RuntimeError('Credential transport is terminal after failure')
            phase = 'credential_load'
            try:
                if self._token is None:
                    self._token = _valid_token(self._token_loader())
                self._environ[BEARER_ENV] = self._token
                phase = 'client_construction'
                if self._backend is None:
                    self._backend = self._transport_factory(self._settings)
                phase = 'invocation_or_response'
                return self._backend(payload)
            except BaseException as error:
                self._failed = True
                try:
                    self._failure_diagnostic = capture_failure(error, phase, self._token, previous)
                except BaseException:
                    self._failure_diagnostic = None
                raise
        finally:
            _restore(self._environ, previous)
            self._lock.release()
