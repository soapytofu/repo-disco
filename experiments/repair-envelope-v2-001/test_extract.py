"""Offline protocol/adversarial cases. Frozen task-body guards remain independent."""
import importlib.util,json,unittest
from pathlib import Path
import extract_response as e
ROOT=Path(__file__).resolve().parent
FROZEN=ROOT.parent/'diverse-repair-pilot-001/frozen-001'

def module(name,path):
    spec=importlib.util.spec_from_file_location(name,path);obj=importlib.util.module_from_spec(spec);spec.loader.exec_module(obj);return obj
GUARD=module('original_diverse_guard',FROZEN/'policy/body_guard.py')
ADAPTER=module('original_repair_adapter',FROZEN/'policy/repair_protocol.py')
PARENT=json.loads((FROZEN/'parents.json').read_text())['weave_unweave-shared']
TASK=json.loads((FROZEN/PARENT['task_path']).read_text())
BASE={p.name:p.read_text() for p in (FROZEN/PARENT['base_path']).glob('*.dfy')}
SEED={p.name:p.read_text() for p in (FROZEN/PARENT['template_path']).glob('*.dfy')}
BODY='if |s| == 0 { A.Empty(s,t); } else { Prove(s[1..],t[1..]); O.Unfold(s,t); A.Project(s[0],t[0],K.Weave(s[1..],t[1..])); assert s == [s[0]] + s[1..]; assert t == [t[0]] + t[1..]; }'
PAYLOAD=json.dumps({'HelperA.dfy':BODY})
def fenced(payload=PAYLOAD,tag='json'):return '```'+tag+'\n'+payload+'\n```\n'

class EnvelopeTests(unittest.TestCase):
    def test_whole_response_json_preserves_exact_span(self):
        for raw in (PAYLOAD,' \r\n'+PAYLOAD+'\t\n'):
            payload,meta=e.extract_json(raw);self.assertEqual(payload,PAYLOAD)
            self.assertEqual(raw[meta['start_char']:meta['end_char']],payload);self.assertEqual(meta['mode'],'whole_response')

    def test_json_fence_with_sequence_explanation(self):
        for text in ['Use s[1..] and t[0].','The equation `K.Weave([],[]) == []` is the base case.',
                     'The display `[s[0]] + s[1..]` reconstructs s.','Bounds lie in `[a,b]`.']:
            payload,meta=e.extract_json(text+'\n'+fenced());self.assertEqual(payload,PAYLOAD);self.assertEqual(meta['mode'],'explicit_json_fence')

    def test_one_json_fence_permits_nonjson_dafny_explanation(self):
        for tag in ['dafny','','text']:
            raw='Some explanation.\n```'+tag+'\nif a != e {\n var u := a;\n} else {\n var u := b;\n}\n```\n'+fenced()+'The result preserves the contract.\n'
            payload,meta=e.extract_json(raw);self.assertEqual(payload,PAYLOAD);self.assertEqual(meta['surrounding_non_json_fences'],1)

    def test_casefolded_json_label_and_crlf(self):
        raw='Explanation.\r\n  ```JSON\r\n  '+PAYLOAD+'\r\n  ```\r\n'
        payload,_=e.extract_json(raw);self.assertEqual(payload,PAYLOAD)

    def test_unicode_offsets_and_body_strings_are_exact(self):
        body="var quoted' := 0; if quoted' == 0 { assert true; }"
        payload=json.dumps({'HelperA.dfy':body},ensure_ascii=False);raw='Reasoning π: s[1..].\n'+fenced(payload)
        answer,meta=e.extract_json(raw);self.assertEqual(json.loads(answer)['HelperA.dfy'],body)
        self.assertEqual(raw.encode()[meta['start_utf8_byte']:meta['end_utf8_byte']],answer.encode())
        self.assertNotEqual(meta['start_char'],meta['start_utf8_byte'])

    def test_escaped_braces_quotes_and_backticks_in_strings(self):
        value='A quote " and slash \\ with braces { } and markers ```json; newline\n'
        payload=json.dumps({'HelperA.dfy':value});selected,_=e.extract_json(fenced(payload))
        self.assertEqual(selected,payload);self.assertEqual(json.loads(selected)['HelperA.dfy'],value)
        with self.assertRaises(ValueError):e.parse_response(fenced(payload),SEED,TASK,GUARD)

    def test_identical_or_different_multiple_answers_are_rejected(self):
        for raw in [PAYLOAD+'\n'+PAYLOAD,fenced()+fenced(),fenced()+fenced(PAYLOAD,'JSON'),fenced()+'\n'+PAYLOAD,
                    '{"note":"one"}\n'+fenced(),'Text\n'+PAYLOAD+'\n'+fenced()]:
            with self.assertRaises(ValueError):e.extract_json(raw)

    def test_other_language_or_untagged_structured_answer_is_rejected(self):
        for tag in ['dafny','python','text','']:
            for alternate in [PAYLOAD,'{"broken":','[1,2]','[{"answer":"x"}]','[1,','"quoted root"']:
                with self.assertRaises(ValueError):e.extract_json(fenced()+fenced(alternate,tag))
                with self.assertRaises(ValueError):e.extract_json(fenced(alternate,tag)+fenced())

    def test_json_shaped_answer_hidden_in_explanatory_code_is_rejected(self):
        for body in ['// answer\n'+PAYLOAD,'var note := '+PAYLOAD+';','if x > 0 {\n '+PAYLOAD+'\n}',
                     '// malformed\n{"HelperA.dfy":','// array\n[1,2]']:
            with self.assertRaises(ValueError):e.extract_json(fenced(body,'dafny')+fenced())

    def test_trailing_malformed_json_or_array_is_rejected(self):
        for tail in [' {"incomplete":','\n{broken','\n[1,','\nAnswer: {unquoted','\nExample [1,2].','\n`[1,2]`', '\n`{"bad":`']:
            with self.assertRaises(ValueError):e.extract_json(fenced()+tail)

    def test_nested_wrappers_arrays_and_quoted_objects_are_rejected(self):
        for payload in ['{"answer":'+PAYLOAD+'}','['+PAYLOAD+']','{"answer":'+PAYLOAD,'['+PAYLOAD,json.dumps(PAYLOAD),'null','42','true']:
            with self.assertRaises(ValueError):e.extract_json(payload)
            with self.assertRaises(ValueError):e.extract_json(fenced(payload))
        for raw in ['{"answer":\n'+fenced()+'}','[\n'+fenced()+']']:
            with self.assertRaises(ValueError):e.extract_json(raw)

    def test_duplicate_keys_and_nonstandard_or_wrong_value_types_rejected(self):
        for payload in ['{"HelperA.dfy":"","HelperA.dfy":"x"}','{"HelperA.dfy":NaN}',
                        '{"HelperA.dfy":Infinity}','{"HelperA.dfy":-Infinity}','{"HelperA.dfy":1e999}',
                        '{"HelperA.dfy":123}','{"HelperA.dfy":null}','{"HelperA.dfy":[]}']:
            with self.assertRaises(ValueError):e.extract_json(payload)
            with self.assertRaises(ValueError):e.extract_json(fenced(payload))

    def test_incomplete_or_reformatted_json_is_not_repaired(self):
        for payload in [PAYLOAD[:-1],PAYLOAD.replace('"HelperA.dfy"',"'HelperA.dfy'"),PAYLOAD.replace('assert true;','assert true;\n') if 'assert true;' in PAYLOAD else '{"HelperA.dfy":"raw\nnewline"}']:
            with self.assertRaises(ValueError):e.extract_json(fenced(payload))

    def test_stray_nested_or_unsupported_fences_are_rejected(self):
        for raw in [fenced()+'```\n', '```dafny\n'+fenced(),fenced().replace('```json','````json'),
                    fenced().replace('```','~~~'),'Text ``` stray\n'+fenced(),fenced(PAYLOAD,'jsonc'),
                    fenced().replace('\n```\n','\n```bad\n')]:
            with self.assertRaises(ValueError):e.extract_json(raw)

    def test_unclosed_inline_code_is_rejected(self):
        with self.assertRaises(ValueError):e.extract_json('Missing `code ending s[1..]\n'+fenced())

    def test_unfenced_embedded_answer_is_intentionally_unsupported(self):
        for raw in ['Text\n'+PAYLOAD,'Reasoning [a,b].\n'+PAYLOAD+'\nExplanation.']:
            with self.assertRaises(ValueError):e.extract_json(raw)

    def test_size_type_surrogate_and_deep_wrapper_limits(self):
        for raw in [None,b'{}',' '*e.MAX_RESPONSE+PAYLOAD,'π'*(e.MAX_RESPONSE//2)+PAYLOAD,'\ud800', '{"HelperA.dfy":"\\ud800"}',
                    '{"x":'*2000+'"body"'+'}'*2000]:
            with self.assertRaises(ValueError):e.extract_json(raw)

    def test_admitted_body_matches_the_original_body_guard_exactly(self):
        expected,_=GUARD.parse_response(PAYLOAD,SEED,TASK)
        for raw in [PAYLOAD,fenced(),'Reasoning s[1..].\n'+fenced()]:
            candidate,_=e.parse_response(raw,SEED,TASK,GUARD);self.assertEqual(candidate,expected)
            for n in SEED:
                if n not in TASK['editable_files']:self.assertEqual(candidate[n],SEED[n])
        candidate,_=ADAPTER.apply_response(fenced(),BASE,SEED,TASK,PARENT['source_sha256'],GUARD,e)
        self.assertEqual(candidate,expected)

    def test_bypass_attempts_and_body_scope_still_fail(self):
        for value in [{'HelperA.dfy':'assume false;'}, {'HelperA.dfy':'reveal K.Weave;'},
                      {'HelperA.dfy':'assert {:axiom} false;'}, {'HelperA.dfy':SEED['HelperA.dfy']},
                      {'HelperA.dfy':'lemma Extra() {}'}, {'HelperA.dfy':'H.Prove(s,t);'},
                      {'HelperB.dfy':BODY},{'HelperA.dfy':BODY,'Other.dfy':''},{}]:
            with self.assertRaises(ValueError):e.parse_response(fenced(json.dumps(value)),SEED,TASK,GUARD)

    def test_immutable_parent_and_template_checks_still_fail(self):
        changed=dict(SEED);changed['ClientA.dfy']+='\n'
        with self.assertRaises(ValueError):e.parse_response(fenced(),changed,TASK,GUARD)
        changed=dict(BASE);changed['Kernel.dfy']+='\n'
        with self.assertRaises(ValueError):ADAPTER.apply_response(fenced(),changed,SEED,TASK,PARENT['source_sha256'],GUARD,e)

if __name__=='__main__':unittest.main(verbosity=2)
