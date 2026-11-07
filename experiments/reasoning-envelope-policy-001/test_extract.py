"""Ambiguity and boundary tests; the caller still supplies the pinned body guard."""
import importlib.util
import json
from pathlib import Path
import unittest
from extract_response import extract_json, parse_response, MAX_RESPONSE

EXP = Path(__file__).resolve().parent.parent
path = EXP/'monorepo-policy-integration-001/body_guard.py'
spec = importlib.util.spec_from_file_location('pinned_v4', path)
guard = importlib.util.module_from_spec(spec)
spec.loader.exec_module(guard)
task = json.loads((EXP/'conditional-monotonicity-001/tasks.json').read_text())[0]
seeds = {p.name:p.read_text() for p in (EXP/'conditional-monotonicity-001/fixtures'/task['task_id']/'empty').glob('*.dfy')}
payload = json.dumps({'HelperA.dfy':'assert true;'})


class ExtractTests(unittest.TestCase):
    def test_plain_fenced_and_prose_preserve_exact_span(self):
        for raw in [payload, '\n'+payload+'\n', '```json\n'+payload+'\n```',
                    'Reasoning about [l,h].\n'+payload+'\nExplanation.']:
            result, meta = extract_json(raw)
            self.assertEqual(result, payload)
            self.assertEqual(raw[meta['start_char']:meta['end_char']], payload)
            self.assertEqual(parse_response(raw,seeds,task,guard)[0],
                             guard.parse_response(payload,seeds,task)[0])

    def test_multiple_objects_rejected_even_identical_or_invalid_proof(self):
        for raw in [payload+'\n'+payload, payload+'\n{}', '{"note":"one"}\n'+payload,
                    payload+'\n'+json.dumps({'HelperA.dfy':'assume false;'})]:
            with self.assertRaises(ValueError):
                parse_response(raw,seeds,task,guard)

    def test_wrappers_and_arrays_cannot_select_nested_payloads(self):
        for raw in ['{"answer":'+payload+'}', '['+payload+']',
                    '{"answer":'+payload, '['+payload, '{"answer":'+payload+'}\n'+payload]:
            with self.assertRaises(ValueError):
                parse_response(raw,seeds,task,guard)

    def test_duplicate_keys_and_incomplete_json_rejected(self):
        for raw in ['{"HelperA.dfy":"","HelperA.dfy":"assert true;"}',
                    '{"HelperA.dfy":"assert true;"', payload+' {"incomplete":',
                    '{"broken": '+payload, '{ "HelperA.dfy": NaN }']:
            with self.assertRaises(ValueError):
                parse_response(raw,seeds,task,guard)

    def test_escape_and_nested_statement_braces_remain_body_bytes(self):
        body = 'var quoted\' := 0; if quoted\' == 0 { assert true; }'
        raw = json.dumps({'HelperA.dfy':body})
        self.assertEqual(json.loads(extract_json('Text\n'+raw)[0])['HelperA.dfy'], body)
        candidate,_ = parse_response(raw,seeds,task,guard)
        self.assertEqual(candidate,guard.parse_response(raw,seeds,task)[0])

    def test_extra_missing_keys_and_code_bypass_still_fail(self):
        for value in [{'HelperA.dfy':'assume false;'}, {'HelperA.dfy':'reveal K.Clamp();'},
                      {'HelperA.dfy':'assert {:axiom} false;'}, {'HelperA.dfy':seeds['HelperA.dfy']},
                      {'HelperB.dfy':'assert true;'}, {'HelperA.dfy':'','Other.dfy':''}]:
            with self.assertRaises(ValueError):
                parse_response('Answer\n'+json.dumps(value),seeds,task,guard)

    def test_malformed_and_oversized_json_are_not_repaired(self):
        for raw in [payload[:-1], payload.replace('"HelperA.dfy"', "'HelperA.dfy'"),
                    payload.replace('assert true;', 'assert true;\n'), ' '*MAX_RESPONSE+payload]:
            with self.assertRaises(ValueError):
                parse_response(raw,seeds,task,guard)

    def test_quoted_json_and_protected_seed_mutation_fail(self):
        with self.assertRaises(ValueError):
            parse_response(json.dumps(payload),seeds,task,guard)
        changed = dict(seeds)
        changed['ClientA.dfy'] += '\n'
        with self.assertRaises(ValueError):
            parse_response(payload,changed,task,guard)

    def test_unrelated_json_container_is_conservatively_ambiguous(self):
        with self.assertRaises(ValueError):
            extract_json('An example [1,2].\n'+payload)


if __name__=='__main__':
    unittest.main(verbosity=2)
