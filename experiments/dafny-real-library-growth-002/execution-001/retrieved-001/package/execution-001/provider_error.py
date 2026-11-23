"""Pure allowlisted extraction from an explicitly supplied ClientError response.

No exception repr, credential, environment, SDK, transport or filesystem access.
The caller retains the original exception and chooses whether/how to record this
diagnostic; extraction itself never changes retry, dispatch or failure behavior.
"""

MAX_MESSAGE_CHARS = 512
MAX_RAW_MESSAGE_CHARS = 16384
MAX_CODE_CHARS = 128
MAX_REQUEST_ID_CHARS = 256
REDACTED = '[REDACTED]'


def _redaction_values(values):
    if type(values) not in (tuple, list) or len(values) > 64:
        raise ValueError('Explicit secret values must be a list or tuple of at most 64 strings')
    if any(type(value) is not str or not value or len(value) > 65536 for value in values):
        raise ValueError('Explicit secret values must be nonempty bounded strings')
    return sorted(set(values), key=lambda value: (-len(value), value))


def _text(value, secrets, *, raw_limit, output_limit, allow_empty=False):
    if type(value) is not str or len(value) > raw_limit or (not value and not allow_empty):
        return None
    # Avoid introducing a supplied short secret through the marker itself.
    if any(secret in REDACTED for secret in secrets):
        return None
    for secret in secrets:
        value = value.replace(secret, REDACTED)
    # Replacement plus adjacent text must not recreate another supplied secret.
    if any(secret in value for secret in secrets):
        return None
    # Redact the full bounded input before truncation, including secrets that
    # cross the output boundary. No suffix or other input-derived field is added.
    return value[:output_limit]


def _integer(value, lower, upper):
    return value if type(value) is int and lower <= value <= upper else None


def extract_provider_error(response, *, secret_values=()):
    """Return only five allowlisted fields; unknown/malformed values are null.

Pass a plain response dictionary such as ``exc.response``, not the exception.
Secret strings are explicitly supplied by the caller; none are discovered or
read here. Exact literal occurrences are redacted, longest first. Unlisted or
transformed secrets cannot be detected by this adapter.
"""
    secrets = _redaction_values(secret_values)
    response = response if type(response) is dict else {}
    error = response.get('Error')
    metadata = response.get('ResponseMetadata')
    error = error if type(error) is dict else {}
    metadata = metadata if type(metadata) is dict else {}
    return {
        'Error': {
            'Code': _text(error.get('Code'), secrets,
                          raw_limit=MAX_CODE_CHARS, output_limit=MAX_CODE_CHARS),
            'Message': _text(error.get('Message'), secrets,
                             raw_limit=MAX_RAW_MESSAGE_CHARS,
                             output_limit=MAX_MESSAGE_CHARS, allow_empty=True),
        },
        'ResponseMetadata': {
            'RequestId': _text(metadata.get('RequestId'), secrets,
                               raw_limit=MAX_REQUEST_ID_CHARS, output_limit=MAX_REQUEST_ID_CHARS),
            'HTTPStatusCode': _integer(metadata.get('HTTPStatusCode'), 100, 599),
            'RetryAttempts': _integer(metadata.get('RetryAttempts'), 0, 2147483647),
        },
    }
