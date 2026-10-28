import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import baseline_smoke as b
from patch import compute_text_diff

class BaselineTests(unittest.TestCase):
    def test_freeze_binds_order_prompts_code_and_input_bytes(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp);exp=root/'exp';exp.mkdir();data=root/'data';data.mkdir();preflight=root/'pre';preflight.mkdir()
            source='method A() { assert false; }';items=[];reports=[]
            for i in range(20):
                name=f'hints_removed/{i}.dfy';dest=data/name;dest.parent.mkdir(exist_ok=True);dest.write_text(source)
                item=dict(path=name,sha256=b.sha(source.encode()),partition='hints_removed');items.append(item)
                report=dict(**item,exit_code=4,legacy_outcome='FAIL',stdout='assertion failed',stderr='');reports.append(report)
                dest=preflight/'logs'/name;dest.parent.mkdir(parents=True,exist_ok=True);dest.with_suffix('.json').write_text(json.dumps(report))
            manifest=dict(files=items,revision='pinned')
            for dest in [exp/'dataset-manifest.json',preflight/'dataset-manifest.json']:dest.write_text(json.dumps(manifest))
            (preflight/'summary.json').write_text(json.dumps(dict(total_files=20,model_calls=0)))
            selection=sorted(reports,key=lambda r:b.sha(('baseline-reproduction-001:'+r['path']).encode()))
            for name in ['eligible.json','smoke-selection.json']:(preflight/name).write_text(json.dumps(selection))
            (root/'code.py').write_text('pinned code')
            with patch.object(b,'ROOT',root),patch.object(b,'EXP',exp),patch.object(b,'CODE',['code.py']):
                tasks=b.prepare(data,preflight,exp/'bundle');settings,frozen=b.validate_freeze(exp/'bundle')
                self.assertEqual([t['path'] for t in frozen],[r['path'] for r in selection])
                self.assertEqual(tasks[0]['messages'][0]['role'],'system')
                (root/'code.py').write_text('changed')
                with self.assertRaises(ValueError):b.validate_freeze(exp/'bundle')
    def test_patch_and_verification_use_actual_candidate(self):
        source='method A() {\n}\n';target='method A() {\n  assert true;\n}\n';seen=[]
        with tempfile.TemporaryDirectory() as temp:
            result=b.evaluate({'source':source},{'text':compute_text_diff(source,target)},temp,parser=lambda s:s,
                verifier=lambda s:seen.append(s) or dict(exit_code=0,legacy_outcome='SUCCESS',category='VERIFIED'))
            self.assertEqual(seen,[target]);self.assertTrue(result['success'])
            self.assertTrue(json.loads((Path(temp)/'audit.json').read_text())['manual_review_required'])
    def test_rejected_patch_never_runs_verifier(self):
        with tempfile.TemporaryDirectory() as temp,patch.object(b,'apply_text_diff',side_effect=ValueError()),patch.object(b,'verify_source') as verify:
            result=b.evaluate({'source':'old'},{'text':'bad'},temp,parser=lambda s:s,verifier=verify)
            self.assertEqual(result['outcome'],'PATCH_REJECTED');verify.assert_not_called()
    def test_external_include_is_rejected_before_process(self):
        with patch.object(b.subprocess,'run') as process:
            self.assertEqual(b.verify_source('include "/private/example"')['category'],'EXTERNAL_INCLUDE_REJECTED')
            process.assert_not_called()
    def test_exactly_twenty_requests_single_attempt_and_no_restart(self):
        tasks=[dict(sequence=i,path=f'{i}.dfy',source='old',messages=[{'role':'user','content':str(i)}]) for i in range(1,21)]
        with tempfile.TemporaryDirectory() as temp:
            folder=Path(temp);bundle=folder/'bundle';bundle.mkdir();calls=[]
            with patch.object(b,'validate_freeze',return_value=({'max_calls':20},tasks)),patch.object(b,'CODE',[]),patch.object(b,'evaluate',return_value={'outcome':'PROOF_FAILURE','success':False}):
                results=b.run(bundle,folder/'out',lambda p:calls.append(p) or {'text':'saved'},parser=lambda s:s)
                self.assertEqual(len(calls),20);self.assertEqual(len(results),20)
                with self.assertRaises(FileExistsError):b.run(bundle,folder/'out',lambda p:None,parser=lambda s:s)
            ledger=json.loads((folder/'out/requests/ledger.json').read_text())
            self.assertEqual(len(ledger['reservations']),20)
    def test_api_error_stops_entire_baseline(self):
        tasks=[dict(sequence=i,path=f'{i}.dfy',source='old',messages=[]) for i in range(1,21)]
        with tempfile.TemporaryDirectory() as temp:
            folder=Path(temp);bundle=folder/'bundle';bundle.mkdir();calls=[]
            def fail(p):calls.append(p);raise TimeoutError()
            with patch.object(b,'validate_freeze',return_value=({'max_calls':20},tasks)),patch.object(b,'CODE',[]):
                results=b.run(bundle,folder/'out',fail,parser=lambda s:s)
            self.assertEqual(len(calls),1);self.assertEqual(results[0]['outcome'],'REQUEST_STOP')

if __name__=='__main__':unittest.main()
