"""Offline source/guard checks and fake-verifier integration; no Dafny/model calls."""
import csv,io,json,shutil,tempfile,unittest
from pathlib import Path
import prepare as p
import preflight as v
import review as r
ROOT=Path(__file__).resolve().parent
PRIMARY=ROOT.parent/'repair-diversity-pilot-002/model-001'

class DiagnosticTests(unittest.TestCase):
    def test_exact_rebuild_and_original_frozen_guard_replay(self):
        generated=p.candidates(ROOT)
        self.assertEqual([c for c,_,_ in generated],p.load(ROOT/'cases.json'))
        self.assertTrue(all(c['admitted'] for c,_,_ in generated))
        for case,files,payload in generated:
            self.assertEqual(p.files(ROOT/case['path']),files)
            self.assertEqual((ROOT/case['payload_path']).read_bytes(),payload.encode())
        self.assertEqual(sum(c['protected_file_comparisons'] for c,_,_ in generated),29)
        self.assertEqual(sum(c['protected_body_boundaries'] for c,_,_ in generated),8)

    def test_all_primary_bytes_and_91_parent_copies_are_unchanged(self):
        report=r.primary_preservation(ROOT,PRIMARY)
        self.assertEqual(report['original_archive_files_preserved'],1845)
        self.assertEqual(report['exact_parent_copies'],91)
        self.assertEqual(report['primary_score_unchanged'],'27/32')

    def test_edits_touch_only_exact_initial_statements_and_keep_call_order(self):
        guard,envelope,adapter=p.policy(ROOT)
        for case,source,payload in p.candidates(ROOT):
            original=p.files(ROOT/'parents'/case['parent_trial']/'candidate')
            bodies=json.loads(payload)
            for name,edit in case['edits'].items():
                response=p.load(ROOT/'parents'/case['parent_trial']/'response.json')['text']
                before=json.loads(envelope.extract_json(response)[0])[name];after=bodies[name]
                self.assertEqual(after,edit['after']+before[len(edit['before']):])
                self.assertEqual(p.calls(before),p.calls(after))
                self.assertEqual(edit['start_char'],0)
            for name in set(original)-set(case['edits']):self.assertEqual(source[name],original[name])

    def test_separate_candidates_apply_same_edit_to_both_existing_bodies(self):
        for case,_,payload in p.candidates(ROOT):
            bodies=json.loads(payload)
            if case['sharing']=='separate':
                self.assertEqual(set(bodies),{'HelperA.dfy','HelperB.dfy'})
                self.assertEqual(bodies['HelperA.dfy'],bodies['HelperB.dfy'])
            else:self.assertEqual(set(bodies),{'HelperA.dfy'})

    def test_unexpected_edit_location_is_rejected(self):
        for instance,(old,new) in p.EDIT_PREFIX.items():
            with self.assertRaises(AssertionError):p.transform('assert true; '+old,instance)

    def test_guard_rejects_bypasses_and_protected_parent_edits(self):
        guard,envelope,adapter=p.policy(ROOT);case=p.load(ROOT/'cases.json')[0]
        task=p.load(ROOT/'parents'/case['parent_trial']/'task.json')
        parent=p.load(ROOT/'frozen-001/parents.json')[task['task_id']]
        template={n:b.decode() for n,b in p.files(ROOT/'frozen-001'/parent['template_path']).items()}
        base={n:b.decode() for n,b in p.files(ROOT/'parents'/case['parent_trial']/'candidate').items()}
        with self.assertRaises(ValueError):adapter.apply_response(json.dumps({'HelperA.dfy':'assume false;'}),base,template,task,p.hashes({n:s.encode() for n,s in base.items()}),guard,envelope)
        changed=dict(base);changed['ClientA.dfy']+='\n'
        with self.assertRaises(ValueError):adapter.apply_response((ROOT/case['payload_path']).read_text(),changed,template,task,p.hashes({n:s.encode() for n,s in base.items()}),guard,envelope)

    def test_diagnostic_categories_require_coherent_strict_evidence(self):
        base=dict(exit_code=0,stdout='Dafny program verifier finished with 9 verified, 0 errors\n',stderr='')
        self.assertEqual(v.classify(base,9),'strict_success');self.assertEqual(v.classify(base,7),'evidence_mismatch')
        self.assertEqual(v.classify(dict(base,exit_code=4,stdout=''),9),'evidence_mismatch')
        self.assertEqual(v.classify(dict(base,exit_code=2,stdout='Unknown failure'),9),'evidence_mismatch')
        self.assertEqual(v.classify(dict(base,exit_code=4,stdout='X.dfy(1,1): Error: assertion might not hold\nDafny program verifier finished with 8 verified, 1 error\n'),9),'proof_failure')

    def fake_run(self,*,fail_first=False):
        temp=tempfile.TemporaryDirectory();self.addCleanup(temp.cleanup);root=Path(temp.name)/'bundle'
        shutil.copytree(ROOT,root,ignore=shutil.ignore_patterns('__pycache__','verification-001','manifest.json'))
        pins={x.relative_to(root).as_posix():p.sha(x) for x in root.rglob('*') if x.is_file()}
        p.save(root/'manifest.json',pins);cases=p.load(root/'cases.json');scope=p.load(root/'frozen-001/measurement-scope.json');sent=[]
        def fake(files):
            case=cases[len(sent)];self.assertEqual(p.hashes(files),case['source_sha256']);sent.append(case['case_id'])
            fail=fail_first and len(sent)==1;stream=io.StringIO();writer=csv.writer(stream,lineterminator='\n');writer.writerow(v.target_metrics.HEADER)
            for symbol,kinds in scope['tasks'][case['task_id']]['expected_units'].items():
                for kind in kinds:writer.writerow([f'{symbol} ({kind})','Failed' if fail and symbol=='HelperA.Prove' else 'Passed','0:00:00.001','1','0'])
            csv_files={'fake.csv':stream.getvalue()};n=case['expected_verified_obligations']
            stdout=f'Dafny program verifier finished with {n-int(fail)} verified, {int(fail)} errors\n'
            if fail:stdout='HelperA.dfy(1,1): Error: assertion might not hold\n'+stdout
            return dict(command=v.COMMAND,exit_code=4 if fail else 0,stdout=stdout,stderr='',elapsed_seconds=0,
                source_sha256=p.hashes(files),csv=csv_files,csv_sha256={n:p.digest(s.encode()) for n,s in csv_files.items()},model_calls=0,attempts=1)
        environment=lambda:dict(job_id='FAKE',partition='test',host='FAKE-COMPUTE',dafny=v.TOOLCHAIN,z3=v.Z3,model_calls=0,offline_fake=True)
        self.assertEqual(v.run(root,verifier=fake,environment=environment),not fail_first)
        self.assertEqual(len(sent),5)
        report=r.review(root,PRIMARY,write=False,allow_fake=True)
        self.assertEqual(report['analyst_strict_successes'],4 if fail_first else 5)
        self.assertTrue(report['complete']);self.assertEqual(report['primary_score_unchanged'],'27/32')
        with self.assertRaises(FileExistsError):v.run(root,verifier=fake,environment=environment)
        self.assertEqual(len(sent),5)
        with self.assertRaises(AssertionError):r.review(root,PRIMARY,write=False)

    def test_five_case_fake_runner_and_reviewer_roundtrip(self):self.fake_run()
    def test_fake_failed_hypothesis_is_preserved_without_retry_or_rescore(self):self.fake_run(fail_first=True)

if __name__=='__main__':unittest.main(verbosity=2)
