# Single-object JSON envelope extraction

Offline development validation; **zero model calls and zero new verifier invocations**. Nine adversarial test methods pass. Forty saved responses reconstruct byte-identical previously audited candidates: 24 six-task reasoning responses, eight conditional-monotonicity responses, and eight interval-witness responses. This is compatibility evidence, not independent sampling, a new success rate, or a revision of old results.

`extract_response.py` allows prose or Markdown around exactly one complete JSON object. It retains the exact payload span and logs its offset and hash. An injected body guard still enforces the exact editable filename set, bounded proof grammar, seed hashes, and immutable contracts. This audit uses the unchanged v4 guard; the wrapper neither repairs JSON nor edits proof strings.

Competing containers (even identical objects), nested wrapper payloads, malformed JSON-looking containers, duplicate keys, nonstandard constants, oversized responses, and body/contract bypass attempts are rejected. A top-level array is never searched for a usable inner object. Numeric JSON arrays in explanatory prose are conservatively treated as competing containers. This is a bounded extraction policy, not a general Markdown or arbitrary-text parser.

- [Tests and raw log](offline-tests.log): nine methods covering accepted wrappers and adversarial ambiguity/protection cases.
- [Saved-response audit](saved-response-audit.json): exact input hashes, extracted spans, prior evidence links, and candidate hashes for all 40 responses.
- [Replay script](audit_saved.py): checks unchanged input bytes and candidates without calling Dafny or any provider.

The old strict pilot outcomes remain 18/24, 29/32, and 1/8 respectively; the monotonicity extraction diagnostic remains separate. Accepting an output format does not make an incorrect proof correct. In particular, the three prior interval precondition failures and prior map assertion failures are preserved, not repaired by this wrapper. All replayed responses belong to development tasks already inspected by the researcher.

Reproduce offline from the repository root:

```sh
python3 -B experiments/reasoning-envelope-policy-001/test_extract.py
python3 -B experiments/reasoning-envelope-policy-001/audit_saved.py
```
