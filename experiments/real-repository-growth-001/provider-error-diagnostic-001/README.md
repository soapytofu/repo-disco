# Offline provider-error metadata adapter

Execution-003 stopped with `AccessDeniedException`, but its frozen failure
record retained only the exception class. The missing AWS explanation, request
ID and HTTP status cannot be recovered from that saved record. This package
does not establish the actual denial cause, HTTP status or service request count.

`extract_provider_error(response, secret_values=())` is a standalone pure adapter
for a future caller to pass an SDK exception's plain `response` dictionary. It
returns only `Error.Code`, `Error.Message`, `ResponseMetadata.RequestId`,
`ResponseMetadata.HTTPStatusCode` and `ResponseMetadata.RetryAttempts`. Missing
or malformed fields remain `None` (JSON `null`); no value is inferred from an
error name. The original exception remains the caller's failure to preserve.

Only caller-supplied secret strings are redacted, literally and longest first,
before text is truncated. Redaction covers all three string fields. The message
is capped at 512 characters; raw messages exceeding 16,384 characters are
omitted. Codes and request IDs exceeding 128 and 256 characters are omitted.
If the redaction marker itself contains a supplied secret, string fields are
omitted. This cannot detect unlisted or transformed secrets; it is not a general
sanitizer. No exception repr, arbitrary headers, request body, configuration or
environment is serialized or inspected.

The focused tests use only synthetic dictionaries and dummy secret strings.
There are no SDK imports, credential/environment/file reads by the adapter,
network/provider/native calls, retries, recovery, dispatch or scoring behavior.
Full focused test stdout/stderr and source hashes are saved under `tests/`.

This adapter is **unintegrated**. Every frozen execution package and historical
result remains unchanged. It creates no runner, authorization, submission or
permission for any future model call. Root review is required before deciding
whether to publish or use it in a separately reviewed future runtime.
