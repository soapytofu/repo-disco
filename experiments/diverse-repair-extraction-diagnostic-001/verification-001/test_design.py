"""Offline-only extraction/guard/staging/reviewer tests; no provider or real Dafny."""
import ast,csv,io,json,os,shutil,tempfile,types,unittest
from pathlib import Path
from unittest.mock import patch
import prepare as p
import preflight as v
import logging_verifier
import review

class Tests(unittest.TestCase):
    def test_exact_eight_payloads_bodies_and_protected_files(self):
        generated=p.candidates();self.assertEqual([r for r,_,_ in generated],p.load(p.ROOT/'cases.json'))
        self.assertEqual(len(generated),8);self.assertTrue(all(c['admitted'] for c,_,_ in generated))
        protected=boundaries=0
        guard,_,_=p.policy();parents=p.load(p.ROOT/'frozen-001/parents.json')
        for case,fs,payload in generated:
            self.assertEqual(fs,p.files(p.ROOT/case['path']));self.assertEqual(p.hashes(fs),case['source_sha256'])
            self.assertEqual((p.ROOT/case['payload_path']).read_bytes(),payload.encode())
            origin=p.ROOT/'parents'/case['parent_trial'];raw=p.load(origin/'response.json')['text'];where=case['selection']
            self.assertEqual(raw[where['payload_start_char']:where['payload_end_char']],payload)
            parent=parents[case['task_id']];base=p.files(p.ROOT/'frozen-001'/parent['base_path']);template=p.files(p.ROOT/'frozen-001'/parent['template_path']);task=p.load(origin/'task.json');bodies=json.loads(payload)
            for n in base:
                if n not in task['editable_files']:self.assertEqual(fs[n],base[n]);protected+=1
                else:
                    pre,suf=guard.split_seed(template[n].decode());self.assertEqual(fs[n],(pre+bodies[n]+suf).encode());boundaries+=1
        self.assertEqual((protected,boundaries),(52,12))

    def test_sole_explicit_fence_ambiguities_are_rejected(self):
        _,envelope,_=p.policy();raw='Prose has s[1..], [0] and [].\n```json\n{"HelperA.dfy": "\n"}\n```\n'
        # A literal newline inside a JSON string is invalid.
        with self.assertRaises(ValueError):p.extract_one_fence(raw,envelope)
        raw='Prose has s[1..], [0] and [].\n```json\n{"HelperA.dfy": "ok"}\n```\n'
        payload,where=p.extract_one_fence(raw,envelope);self.assertEqual(payload,'{"HelperA.dfy": "ok"}\n')
        self.assertEqual(raw[where['payload_start_char']:where['payload_end_char']],payload)
        for bad in [raw+raw,raw+'```text\nextra\n```\n',raw.replace('```json','```dafny'),'{"HelperA.dfy":"ok"}',
                    '```json\n{"x":"a","x":"b"}\n```\n','```json\n[1,2]\n```\n','```json\n{"x":NaN}\n```\n']:
            with self.assertRaises(ValueError):p.extract_one_fence(bad,envelope)

    def test_old_full_response_rejections_stay_rejections(self):
        _,envelope,_=p.policy()
        for case,_,_ in p.candidates():
            origin=p.ROOT/'parents'/case['parent_trial'];raw=p.load(origin/'response.json')['text'];old=p.load(origin/'extraction.json')
            with self.assertRaisesRegex(ValueError,old['reason']):envelope.extract_json(raw)
            self.assertFalse(old['accepted']);self.assertEqual(p.load(origin/'result.json')['outcome'],'OUTPUT_REJECTED')

    def test_guard_bypass_and_parent_mutation_are_rejected(self):
        guard,envelope,adapter=p.policy();case,_,payload=p.candidates()[0]
        parent=p.load(p.ROOT/'frozen-001/parents.json')[case['task_id']];task=p.load(p.ROOT/'parents'/case['parent_trial']/'task.json')
        base={n:b.decode() for n,b in p.files(p.ROOT/'frozen-001'/parent['base_path']).items()};template={n:b.decode() for n,b in p.files(p.ROOT/'frozen-001'/parent['template_path']).items()}
        for forbidden in ['assume false;','reveal K.Weave;','lemma Prove() ensures true {}']:
            with self.assertRaises(ValueError):adapter.apply_response(json.dumps(dict.fromkeys(task['editable_files'],forbidden)),base,template,task,parent['source_sha256'],guard,envelope)
        altered=dict(base);altered['Kernel.dfy']+='\n'
        with self.assertRaises(ValueError):adapter.apply_response(payload,altered,template,task,parent['source_sha256'],guard,envelope)

    def test_fake_verifier_exact_staging_and_csv_bytes(self):
        for case,fs,_ in p.candidates():
            def process(command,cwd,capture_output,text):
                self.assertEqual(command,v.COMMAND);self.assertEqual(p.files(Path(cwd)),fs)
                (Path(cwd)/'fake.csv').write_bytes(b'header\r\nvalue\r\n')
                return types.SimpleNamespace(returncode=0,stdout='FAKE',stderr='')
            with patch.object(logging_verifier.subprocess,'run',side_effect=process) as run:ev=logging_verifier.verify(fs)
            self.assertEqual(run.call_count,1);self.assertEqual(ev['csv'],{'fake.csv':'header\r\nvalue\r\n'})
            self.assertEqual(ev['source_sha256'],case['source_sha256']);self.assertEqual(ev['model_calls'],0)

    def test_compute_requirement_precedes_process_calls(self):
        with patch.dict(os.environ,{},clear=True),patch.object(v.socket,'gethostname',return_value='holylogin07'),patch.object(v.subprocess,'run') as run,patch('sys.argv',['preflight.py','--output','verification-001']):
            with self.assertRaises(SystemExit):v.main()
            run.assert_not_called()

    def test_diagnostic_categories_distinguish_warnings_and_failures(self):
        cases=[(0,'Dafny program verifier finished with 11 verified, 0 errors\n','strict_success'),
               (4,'program.dfy(1,0): Error: a postcondition could not be proved\n','proof_failure'),
               (4,'program.dfy(1,0): Error: cannot prove termination; try supplying a decreases clause\n','termination_failure'),
               (2,'1 parse errors detected in program.dfy\n','frontend_failure'),
               (4,'1 parse errors detected in program.dfy\n','unexpected_frontend_exit'),
               (2,'program.dfy(1,0): Warning: no trigger\nDafny program verifier finished with 11 verified, 0 errors\n','warning_only'),
               (0,'Dafny program verifier finished with 11 verified, 0 errors\nWarning: unexpected\n','evidence_mismatch'),
               (124,'','verifier_timeout')]
        for code,text,expected in cases:self.assertEqual(v.classify(dict(exit_code=code,stdout=text,stderr='')),expected)

    def test_runtime_pins_and_remote_script_syntax(self):
        for n,h in p.load(p.ROOT/'manifest.json').items():self.assertEqual(p.sha(p.ROOT/n),h,n)
        self.assertEqual(p.load(p.ROOT/'provenance.json')['prior_archive_files_preserved'],1204)
        for node in ast.walk(ast.parse((p.ROOT/'ops.py').read_text())):
            if isinstance(node,ast.Constant) and isinstance(node.value,str) and node.value.startswith('import '):compile(node.value,'remote','exec')

    def test_offline_reviewer_checks_exact_source_and_targets(self):
        pins=p.load(p.ROOT/'manifest.json');generated=p.candidates();scope=p.load(p.ROOT/'frozen-001/measurement-scope.json')
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);out=root/'verification-001';out.mkdir();rows=[]
            for target in [root,out]:
                for name in [*pins,'manifest.json']:
                    dest=target/name;dest.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(p.ROOT/name,dest)
            p.save(out/'environment.json',dict(job_id='FAKE_OFFLINE',host='fake-compute',dafny=v.TOOLCHAIN,z3=v.Z3,model_calls=0))
            for case,fs,_ in generated:
                text=io.StringIO();writer=csv.writer(text);writer.writerow(v.target_metrics.HEADER)
                for symbol,kinds in scope['tasks'][case['task_id']]['expected_units'].items():
                    for kind in kinds:writer.writerow([f'{symbol} ({kind})','Passed','00:00:00.001','1','0'])
                csvtext=text.getvalue();ev=dict(case_id=case['case_id'],parent_trial=case['parent_trial'],source_sha256=p.hashes(fs),model_calls=0,attempts=1,command=v.COMMAND,category='strict_success',exit_code=0,
                    stdout='Dafny program verifier finished with 11 verified, 0 errors\n',stderr='',csv={'fake.csv':csvtext},csv_sha256={'fake.csv':p.digest(csvtext.encode())})
                ev['target_metrics']=v.measured(ev,scope['tasks'][case['task_id']]);rows.append(ev);p.save(out/(case['case_id']+'.json'),ev)
                dest=out/'raw-csv'/case['case_id']/'fake.csv';dest.parent.mkdir(parents=True);dest.write_bytes(csvtext.encode())
            p.save(out/'summary.json',dict(model_calls=0,planned=8,completed=8,saved_responses=8,all_strict_verified=True,results=rows))
            preserved=dict(prior_archive_files_preserved=1204,exact_parent_copies=64,original_primary_score='16/24',prior_score_unchanged=True)
            with patch.object(review,'primary_preservation',return_value=preserved):report=review.review(root,write=False)
            self.assertTrue(report['all_strict_verified']);self.assertEqual(report['strict_diagnostic_successes'],8)
            damaged=out/generated[0][0]['path']/'HelperA.dfy';damaged.write_bytes(damaged.read_bytes()+b'\n')
            with patch.object(review,'primary_preservation',return_value=preserved),self.assertRaises(AssertionError):review.review(root,write=False)

if __name__=='__main__':unittest.main(verbosity=2)
