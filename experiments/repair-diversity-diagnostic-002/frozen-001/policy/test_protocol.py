"""Offline protocol tests: injected source strings only, no Dafny or API calls."""
from pathlib import Path
from unittest.mock import patch
import copy,hashlib,importlib.util,json,sys,tempfile,unittest
import body_guard as g
import extract_response as envelope
import repair_protocol as adapter

ROOT=Path(__file__).resolve().parent
PARENT=ROOT.parent
FAMILIES=('arithmetic','sequence','witness','maps')

def load(path):return json.loads(path.read_text())
def files(folder):return {p.name:p.read_text() for p in sorted(folder.glob('*.dfy'))}
def all_records():
    result=[]
    for family in FAMILIES:
        folder=PARENT/family;tasks={t['task_id']:t for t in load(folder/'tasks.json')};cases=load(folder/'cases.json')
        for case in cases:
            task=tasks[case['task_id']]
            empty=next(c for c in cases if c['task_id']==task['task_id'] and c['variant']=='empty')
            faulty=next(c for c in cases if c['task_id']==task['task_id'] and c['variant']=='faulty')
            result.append(dict(family=family,task=task,case=case,template=files(folder/empty['path']),
                base=files(folder/faulty['path']),candidate=files(folder/case['path'])))
    return result

def payload(record):
    bodies={}
    for name in record['task']['editable_files']:
        before,after=g.split_seed(record['template'][name]);source=record['candidate'][name]
        assert source.startswith(before) and source.endswith(after)
        bodies[name]=source[len(before):len(source)-len(after)]
    return json.dumps(bodies)

class ProtocolTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):cls.records=all_records()
    def record(self,semantic='compression_fixed_point',variant='reference',sharing='shared'):
        return next(r for r in self.records if r['task']['semantic_instance']==semantic and r['case']['variant']==variant and r['task']['sharing']==sharing)
    def parse(self,body,semantic='compression_fixed_point'):
        r=self.record(semantic);names=r['task']['editable_files']
        return g.parse_response(json.dumps({name:body for name in names}),r['template'],r['task'])
    def test_all_current_fixture_bytes_and_negative_body_admission(self):
        admitted=rejected=body_count=0
        for r in self.records:
            with self.subTest(case=r['case']['case_id']):
                self.assertEqual(g.hashes(r['candidate']),r['case']['source_sha256'])
                if r['case']['expected']=='resolution_failure':
                    with self.assertRaises(ValueError):g.parse_response(payload(r),r['template'],r['task'])
                    rejected+=1;continue
                actual,decision=g.parse_response(payload(r),r['template'],r['task'])
                self.assertEqual(actual,r['candidate']);self.assertFalse(decision['semantic_verification_performed'])
                admitted+=1;body_count+=len(decision['bodies'])
        self.assertEqual((len(self.records),admitted,rejected,body_count),(78,70,8,105))
    def test_exact_failing_base_repair_for_all_current_allowed_bodies(self):
        for r in self.records:
            if r['case']['expected']=='resolution_failure':continue
            with self.subTest(case=r['case']['case_id']):
                actual,decision=adapter.apply_response(payload(r),r['base'],r['template'],r['task'],g.hashes(r['base']))
                self.assertEqual(actual,r['candidate']);self.assertEqual(decision['model_calls'],0)
    def test_registry_exact_templates_and_boundary_hashes(self):
        entries=g.registry();self.assertEqual(len(entries),8)
        for task_id,entry in entries.items():
            r=next(r for r in self.records if r['task']['task_id']==task_id)
            self.assertEqual(g.validate_template(r['template'],r['task']),entry)
            for name,b in entry['body_boundaries'].items():
                before,after=g.split_seed(r['template'][name])
                self.assertEqual(len(before.encode()),b['start_utf8_byte']);self.assertEqual(b['start_utf8_byte'],b['end_utf8_byte'])
                self.assertEqual(g.digest(before),b['prefix_sha256']);self.assertEqual(g.digest(after),b['suffix_sha256'])
    def test_task_registry_cannot_expand_edit_scope_or_calls(self):
        r=self.record();task=r['task']
        mutations=[('task_id','unknown'),('semantic_instance','saturating_assoc'),('sharing','separate'),('depth','deep'),('entry','HelperA.dfy'),
                   ('editable_files',['HelperA.dfy','ClientA.dfy']),('source_sha256',{}),('params',['s','K']),('calls',{'O.Drop':1}),('pure',{'K.Other':1}),('body_boundaries',{})]
        for key,value in mutations:
            changed=copy.deepcopy(task);changed[key]=value
            with self.subTest(key=key),self.assertRaises(ValueError):g.parse_response(payload(r),r['template'],changed)
    def test_registry_file_drift_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d);(p/'registry.json').write_bytes((ROOT/'registry.json').read_bytes()+b'\n')
            with patch.object(g,'ROOT',p),self.assertRaises(ValueError):g.registry()
    def test_every_protected_file_and_helper_contract_is_immutable(self):
        for r in (self.record(),self.record('saturating_assoc'),self.record('exact_gap_pair'),self.record('overlap_override_restrict')):
            for name in r['template']:
                changed=dict(r['template']);changed[name]+='\n'
                with self.subTest(task=r['task']['task_id'],name=name),self.assertRaises(ValueError):g.parse_response(payload(r),changed,r['task'])
            for addition in ('Extra.dfy','../HelperA.dfy'):
                changed=dict(r['template']);changed[addition]=''
                with self.assertRaises(ValueError):g.parse_response(payload(r),changed,r['task'])
    def test_failing_parent_hash_and_contract_preservation(self):
        r=self.record();h=g.hashes(r['base']);edited=dict(r['base']);edited['HelperA.dfy']+='\n'
        with self.assertRaises(ValueError):adapter.apply_response(payload(r),edited,r['template'],r['task'],h)
        for name in r['base']:
            edited=dict(r['base']);edited[name]='// protected source changed\n'+edited[name]
            with self.subTest(name=name),self.assertRaises(ValueError):adapter.apply_response(payload(r),edited,r['template'],r['task'],g.hashes(edited))
    def test_exact_filename_set_no_extra_or_missing_or_retyped_keys(self):
        for sharing in ('shared','separate'):
            r=self.record(sharing=sharing);b=json.loads(payload(r))
            invalid=[{},[],{'body':b},dict(b,**{'ClientA.dfy':''}),dict(b,**{'../HelperA.dfy':''}),{k:0 for k in b},{k:[] for k in b},{k:None for k in b}]
            if sharing=='separate':invalid.append({'HelperA.dfy':b['HelperA.dfy']})
            else:invalid.append(dict(b,**{'HelperB.dfy':''}))
            for obj in invalid:
                with self.subTest(sharing=sharing,obj=str(obj)[:60]),self.assertRaises(ValueError):g.parse_response(json.dumps(obj),r['template'],r['task'])
    def test_duplicate_malformed_nonstandard_and_unicode_payloads_rejected(self):
        r=self.record()
        raw=['{"HelperA.dfy":"", "HelperA.dfy":""}','{"HelperA.dfy":NaN}', '{"HelperA.dfy":""} {}','{"HelperA.dfy":"",}',
             json.dumps({'HelperA.dfy':'\ud800'}),'{"HelperA.dfy":"\\u0000"}', 'null', '"{}"', '[]', '']
        for item in raw:
            with self.subTest(raw=repr(item)),self.assertRaises(ValueError):g.parse_response(item,r['template'],r['task'])
    def test_no_bypass_or_scope_escape(self):
        invalid=['assume false;','reveal K.Compress();','assert {:axiom} false;','assert {:verify false} false;','expect false;',
                 'while true {}','lemma Other() {}','function X(): int {0}','ghost var x := 0;','return;','calc {0;}',
                 '}\n lemma X() {}\n{','include "secret"','import Evil = Kernel`Internal','H.Prove(s);','HelperB.Prove(s);',
                 'O.Drop(s);','K.Compress(s);','assert true; // assume false;', 'assert true; /* comment */','s := [];']
        for body in invalid:
            with self.subTest(body=body),self.assertRaises(ValueError):self.parse(body)
    def test_no_symbol_alias_parameter_or_local_rebinding(self):
        for semantic,names in [('compression_fixed_point',['s','K','O','Prove']),('exact_gap_pair',['a','b','c','d','gap','O','K','A']),('overlap_override_restrict',['m','n','keep','D','V','A','K'])]:
            for name in names:
                for body in ('var '+name+' := 0;', 'forall '+name+' | true ensures true {}', 'assert forall '+name+' :: true;', 'var tmp := map '+name+' | true :: 0;'):
                    with self.subTest(semantic=semantic,body=body),self.assertRaises(ValueError):self.parse(body,semantic)
        for body in ['var rest := s; var rest := s;', 'var rest := s; if true { var rest := s; }','var rest := s; rest := [];']:
            with self.assertRaises(ValueError):self.parse(body)
    def test_lexical_scope_does_not_leak_or_needlessly_reserve_sibling_names(self):
        self.parse('if true { var rest := s; assert rest == s; } else { var rest := s; assert rest == s; }')
        for body in ['if true { var rest := s; } assert rest == s;', 'assert forall q :: q == q; assert q == 0;',
                     'var mm := map q | q in s :: q; assert q == 0;','forall q | q in s ensures q == q { } assert q == 0;']:
            with self.assertRaises(ValueError):self.parse(body)
    def test_general_sequence_syntax_not_reference_pattern_matching(self):
        body="var tail' := s[1..]; var prefix := s[..1]; var middle := s[0..1]; assert [s[0]] + tail' == s; assert |tail'| + 1 == |s|; if !(|s| < 2) { O.TailInvariant(s); Prove(tail'); O.Boundary(s); O.Keep(s); }"
        _,d=self.parse(body);self.assertGreater(d['bodies']['HelperA.dfy']['tokens'],0)
        self.parse('assert false; Prove(s);') # Semantic and termination failures belong to Dafny.
    def test_quantified_expressions_are_bounded_general_and_truth_agnostic(self):
        self.parse('assert forall q :: q in m ==> q !in n;', 'overlap_override_restrict')
        self.parse('assert forall q | q in keep :: q == q;', 'overlap_override_restrict')
        self.parse('assert forall q :: (forall r :: q == r);', 'overlap_override_restrict')
        for body in ['assert forall q: int :: true;','assert forall q, r :: true;','assert forall q {:trigger q} :: true;','assert exists q :: true;']:
            with self.assertRaises(ValueError):self.parse(body,'overlap_override_restrict')
    def test_existing_map_and_arithmetic_syntax(self):
        self.parse('var mm := map q | q in m :: m[q]; var updated := mm[0 := 1]; var kk := {0,1}; assert updated.Keys == kk;','overlap_override_restrict')
        self.parse('var u := if a + gap < c then c-gap else a; var v := u+gap; assert a <= u <= b; O.Left(a,b,u);','exact_gap_pair')
    def test_arity_and_unknown_symbols_rejected(self):
        for body in ['O.Base();','O.Base(s,s);','O.Unknown(s);','Unknown(s);','assert K.Compress(s,s)==s;','assert K.Unknown(s)==s;','assert unknown==s;','Prove();','K.Clean(s);','assert O.Base(s);']:
            with self.subTest(body=body),self.assertRaises(ValueError):self.parse(body)
        with self.assertRaises(ValueError):self.parse('Prove(c,a,b,d);','saturating_assoc')
    def test_finite_limits(self):
        invalid=[' '* (g.MAX_BODY+1), 'assert true;'*(g.MAX_STATEMENTS+1),
                 'assert '+ '(' * 40+'true'+')'*40+';', 'if true {'*26+'assert true;'+'}'*26,
                 'assert 1234567890123 == 0;', 'assert '+ '+'.join('0' for _ in range(g.MAX_TOKENS))+'==0;']
        for body in invalid:
            with self.subTest(length=len(body)),self.assertRaises(ValueError):self.parse(body)
        r=self.record()
        with self.assertRaises(ValueError):g.parse_response(' '* (g.MAX_RESPONSE+1),r['template'],r['task'])
    def test_envelope_is_separate_pinned_v2_and_preserves_exact_body(self):
        self.assertEqual(hashlib.sha256((ROOT/'extract_response.py').read_bytes()).hexdigest(),adapter.ENVELOPE_SHA256)
        r=self.record();raw='Here is the proof.\n```json\n'+payload(r)+'\n```\n'
        with self.assertRaises(ValueError):g.parse_response(raw,r['template'],r['task'])
        actual,d=adapter.apply_response(raw,r['base'],r['template'],r['task'],g.hashes(r['base']))
        self.assertEqual(actual,r['candidate']);self.assertEqual(d['original_guard_decision']['envelope']['version'],envelope.VERSION)
        for item in [raw+payload(r),raw+'\n```json\n'+payload(r)+'\n```', 'Explanation '+payload(r)]:
            with self.assertRaises(ValueError):adapter.apply_response(item,r['base'],r['template'],r['task'],g.hashes(r['base']))
    def test_inherited_grammar_same_parse_trees_outside_new_quantifier_syntax(self):
        spec=importlib.util.spec_from_file_location('frozen_legacy_replay',ROOT/'legacy_body_guard.py');legacy=importlib.util.module_from_spec(spec);spec.loader.exec_module(legacy)
        bodies=0
        with patch.object(legacy,'policy',side_effect=g.policy):
            for r in self.records:
                if r['case']['expected']=='resolution_failure' or r['case']['variant']=='collision_assumption':continue
                for name,body in json.loads(payload(r)).items():
                    with self.subTest(case=r['case']['case_id'],file=name):
                        before=legacy.Grammar(body,r['task']);after=g.Grammar(body,r['task'])
                        self.assertEqual(before.sequence(),after.sequence());self.assertIsNone(before.peek());self.assertIsNone(after.peek())
                        bodies+=1
        self.assertEqual(bodies,102)
    def test_legacy_grammar_tokens_and_bounds_unchanged(self):
        spec=importlib.util.spec_from_file_location('frozen_legacy',ROOT/'legacy_body_guard.py');legacy=importlib.util.module_from_spec(spec);spec.loader.exec_module(legacy)
        self.assertEqual(g.TOKEN.pattern,legacy.TOKEN.pattern);self.assertEqual(g.PRECEDENCE,legacy.PRECEDENCE)
        for name in ('MAX_RESPONSE','MAX_BODY','MAX_TOKENS','MAX_STATEMENTS'):self.assertEqual(getattr(g,name),getattr(legacy,name))
        self.assertEqual(hashlib.sha256((ROOT/'legacy_body_guard.py').read_bytes()).hexdigest(),'c749c53fd11742937adc3cdefa1fa5444ee0232443fa6d1cb7d2b83bea8a6c6b')

def replay_audit():
    inputs=load(ROOT/'source-inputs.json')
    for rel,want in inputs.items():
        if hashlib.sha256((PARENT/rel).read_bytes()).hexdigest()!=want:
            raise ValueError('Source fixture input changed: '+rel)
    rows=[]
    for record in all_records():
        case=record['case'];task=record['task'];raw=payload(record)
        row=dict(case_id=case['case_id'],task_id=task['task_id'],family=record['family'],
                 variant=case['variant'],fixture_expected_category=case['expected'],
                 payload_sha256=g.digest(raw),source_sha256=case['source_sha256'])
        try:
            actual,decision=adapter.apply_response(raw,record['base'],record['template'],task,g.hashes(record['base']))
        except ValueError as error:
            if case['expected']!='resolution_failure':raise
            row.update(admitted=False,rejection=str(error),reason='Deliberately hidden helper is outside the task call environment')
        else:
            if case['expected']=='resolution_failure' or actual!=record['candidate']:
                raise ValueError('Unexpected admission or source reconstruction: '+case['case_id'])
            guarded=decision['original_guard_decision']['body_guard']
            row.update(admitted=True,byte_exact=True,candidate_sha256=decision['candidate_sha256'],
                       body_sha256={n:d['body_sha256'] for n,d in guarded['bodies'].items()},
                       protected_boundary_checks=len(guarded['bodies']))
        rows.append(row)
    return dict(policy=g.VERSION,registry_sha256=g.REGISTRY_SHA256,
                checks=len(rows),admitted_workspaces=sum(r['admitted'] for r in rows),
                hidden_controls_rejected=sum(not r['admitted'] for r in rows),
                exact_helper_body_reconstructions=sum(r.get('protected_boundary_checks',0) for r in rows),
                input_files_checked=len(inputs),model_calls=0,verifier_invocations=0,
                semantic_claim='Syntax admission and exact reconstruction only; expected fixture categories are not measured by this replay.',
                rows=rows)

if __name__=='__main__':
    if sys.argv[1:]==['--write-replay']:
        audit=replay_audit();(ROOT/'fixture-replay.json').write_text(json.dumps(audit,indent=2)+'\n')
        print(json.dumps({k:v for k,v in audit.items() if k!='rows'},indent=2))
    else:unittest.main()
