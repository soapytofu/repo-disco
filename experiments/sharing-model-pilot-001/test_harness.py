import json,tempfile,unittest
from collections import Counter
from pathlib import Path
from harness import ROOT,CLIENTS,parse_response,request_for,evaluate

def inputs(condition='shared',kind='missing'):
    return {n:(ROOT/'fixtures'/f'{condition}_{kind}'/n).read_text() for n in CLIENTS}

class HarnessTests(unittest.TestCase):
    def test_frozen_bundle_and_tamper_detection(self):
        import hashlib
        import pilot
        from unittest.mock import patch
        pilot.verify_freeze()
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);(root/'file').write_text('original')
            (root/'frozen-bundle.json').write_text(json.dumps({'file':hashlib.sha256(b'original').hexdigest()}))
            with patch.object(pilot,'ROOT',root):
                pilot.verify_freeze()
                (root/'file').write_text('modified')
                with self.assertRaises(ValueError):pilot.verify_freeze()
    def test_reference_repairs_accepted(self):
        for condition in ['shared','separate']:
            self.assertEqual(parse_response(json.dumps(inputs(condition,'reference')),inputs(condition)),inputs(condition,'reference'))
    def test_protected_changes_rejected(self):
        for old,new in [('requires F.Size(s) > k','requires true'),('ensures F.Large((s + t) + u, k)','ensures true'),('Facts`ViewA','Facts`ViewB')]:
            data=inputs(kind='reference');data['ClientA.dfy']=data['ClientA.dfy'].replace(old,new)
            with self.assertRaises(ValueError):parse_response(json.dumps(data),inputs())
    def test_forbidden_body_content_rejected(self):
        for content in ['assume false;','assert true;','reveal F.Size();','// comment','F.Finish(s, unknown);','F.Finish(s, k); } module Evil {','F.Finish(s, k)']:
            data=inputs();data['ClientA.dfy']=data['ClientA.dfy'].replace('  {\n','  {\n    '+content+'\n')
            with self.subTest(content=content),self.assertRaises(ValueError):parse_response(json.dumps(data),inputs())
    def test_schema_missing_extra_duplicate_keys(self):
        for value in [{},[],{'ClientA.dfy':1,'ClientB.dfy':2},dict(inputs(),**{'Facts.dfy':'changed'})]:
            with self.assertRaises(ValueError):parse_response(json.dumps(value),inputs())
        with self.assertRaises(ValueError):parse_response('{"ClientA.dfy":"x","ClientA.dfy":"y","ClientB.dfy":"z"}',inputs())
    def test_wrong_valid_calls_reach_verifier(self):
        data=inputs();data['ClientA.dfy']=data['ClientA.dfy'].replace('  {\n','  {\n    F.NotARealLemma(s, k);\n')
        self.assertEqual(parse_response(json.dumps(data),inputs()),data)
    def test_frozen_order_and_prompt_source(self):
        trials=[request_for(i) for i in range(1,9)]
        self.assertEqual([t['condition'] for t,_ in trials],['shared','separate','separate','shared','shared','separate','separate','shared'])
        self.assertEqual(Counter(t['condition'] for t,_ in trials),{'shared':4,'separate':4})
        self.assertEqual(len({m[0]['content'] for _,m in trials}),1)
        for t,m in trials:
            source=ROOT/'fixtures'/f"{t['condition']}_missing"
            for f in source.glob('*.dfy'):self.assertIn('\nFILE '+f.name+'\n'+f.read_text(),m[1]['content'])
        # Whole user prompts differ only in protected ClientB export selection.
        self.assertEqual(trials[0][1][1]['content'].replace('Facts`ViewA\n  lemma Prove(s: seq<int>, t: seq<int>, u: seq<int>, k: nat)\n    requires F.Size(t)', 'Facts`ViewB\n  lemma Prove(s: seq<int>, t: seq<int>, u: seq<int>, k: nat)\n    requires F.Size(t)'),trials[1][1][1]['content'])
    def test_no_verification_on_invalid_response_and_no_overwrite(self):
        with tempfile.TemporaryDirectory() as directory:
            out=Path(directory)/'trial'
            def forbidden(*a):self.fail('Invalid response reached verifier')
            self.assertEqual(evaluate('shared','{}',out,forbidden)['outcome'],'EDIT_REJECTED')
            with self.assertRaises(FileExistsError):evaluate('shared','{}',out,forbidden)
    def test_timeout_stops_checks_and_provider_is_copied(self):
        calls=[]
        def fake(folder,entry):
            calls.append(entry)
            return dict(outcome='TIMEOUT',exit_code=124,stdout='',stderr='',seconds=60,command=[])
        with tempfile.TemporaryDirectory() as directory:
            out=Path(directory)/'trial'
            result=evaluate('separate',json.dumps(inputs('separate','reference')),out,fake)
            self.assertEqual(result['outcome'],'TIMEOUT');self.assertEqual(calls,['All.dfy'])
            self.assertEqual((out/'Facts.dfy').read_bytes(),(ROOT/'fixtures/separate_missing/Facts.dfy').read_bytes())

if __name__=='__main__':unittest.main()
