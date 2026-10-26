# Offline request-gate prototype

This addresses a baseline-integration gap: an outer agenda attempt may contain
multiple repair requests, and workers can catch transport errors and continue.
The prototype meters each injected transport invocation, persists a reservation
before dispatch, and permanently closes on ambiguous transport or response-save
failure. A caught exception cannot reopen it. Reservations are never refunded.
It checks the deadline both before reservation and immediately before transport.

Eight offline tests pass using fake transports only. They exercise nested repair
loops sharing one cap, caught timeouts, deadline crossings, restart refusal,
reservation-write failure, response serialization failure, reentrant invocation
and preservation of the recorded prompt when transport mutates its input.
Raw exception text is not logged. `tests.log` contains the test output.

This is an experimental **single-process, single-owner** gate. It supplies no
credentials, SDK configuration, provider client, live command, or LangChain worker
adapter. It has not been tested with actual workers or distributed processes.
It does not interrupt an already-dispatched request at the deadline or prevent
retries inside an injected transport. Future live integration must disable SDK
retries and coordinate one global budget across any worker processes. A directory
cannot be reopened for recovery; ambiguous records require explicit inspection.
Prompt/response logging will require a non-secret input policy before live use.

The frozen eight-call dispatcher and prior evidence remain unchanged. This work
made **zero model/API calls and zero verifier calls**. It does not authorize a
baseline experiment or establish published-baseline reproduction.

Run from the repository root:

```
python3 -m unittest discover -s experiments/request-gate-001 -p test_gate.py -v
```
