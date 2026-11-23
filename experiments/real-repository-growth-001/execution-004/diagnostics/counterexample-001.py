"""Concrete analyst trace of the exact saved body; no Dafny/model execution."""
from collections import Counter
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SLOT = ROOT / 'retrieved-001/model-001/slot-01'
SOURCE = SLOT / 'source-overlay/repodisco-growth/MoveToFront.dfy'
RESPONSE = SLOT / 'response.json'
SOURCE_SHA = 'ef4dacc5fe562fba502477c827762d028df4ea14e5505344cce29fdfd2a09ef2'
RESPONSE_SHA = '933305bd3b9065f7c3504e10134d3e86c6eeb43ab672d5e5d699334b1eedecd5'

assert hashlib.sha256(SOURCE.read_bytes()).hexdigest() == SOURCE_SHA
assert hashlib.sha256(RESPONSE.read_bytes()).hexdigest() == RESPONSE_SHA
expected_body = ('if k == 0 then\n      xs\n    else\n'
                 '      var prev := MoveToFront(xs, k - 1);\n'
                 '      var swapped := Model.Swap(prev, k - 1, k);\n      swapped')
assert expected_body in SOURCE.read_text()
response = json.loads(RESPONSE.read_bytes())
assert json.loads(response['text'].removeprefix('```json\n').removesuffix('\n```')) == {'replacement': expected_body}

# This is a manual translation of this particular body and the fixed upstream
# Swap semantics, not a general Dafny evaluator or an independent native proof.
trace = []
def candidate(xs, k):
    assert 0 <= k < len(xs)
    if k == 0:
        result = list(xs)
    else:
        result = candidate(xs, k - 1)
        result[k - 1], result[k] = result[k], result[k - 1]
    trace.append({'k': k, 'result': list(result)})
    return result

xs, k = [0, 1, 2], 2
actual = candidate(xs, k)
required = [xs[k]] + xs[:k] + xs[k + 1:]
assert actual == [1, 2, 0] and required == [2, 0, 1] and actual != required
print(json.dumps(dict(schema='repodisco-source-bound-concrete-counterexample-v1',
    analyst_authored=True, source_sha256=SOURCE_SHA, response_sha256=RESPONSE_SHA,
    inputs={'xs': xs, 'k': k}, recursive_trace=trace, actual=actual, required=required,
    ordered_sequence_postcondition=False, length_postcondition=len(actual)==len(xs),
    multiset_postcondition=Counter(actual)==Counter(xs), model_calls=0, native_calls=0,
    interpretation='This concrete trace refutes the ordered-sequence contract for the exact saved implementation. The original native classification remains resource exhaustion; this is not an analyst repair, native rerun or rescore.'),indent=2,sort_keys=True))
