"""Fake transports and saved raw evidence only: zero APIs and zero verifier invocations."""
import contextlib
import copy
import io
import json
from pathlib import Path
import shutil
import tempfile
import unittest
from unittest.mock import patch

import common as c
import collect
import review
import verify_candidates as v
from bounded_requests import RequestGate,GateClosed,bedrock_transport,durable_json


class ExecutionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):cls.settings,cls.tasks,cls.order=c.validate_package(runtime=False)

    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup);self.root=Path(self.tmp.name)
        for n in ['frozen-001','fixtures']:shutil.copytree(c.ROOT/n,self.root/n)
        for n in ['body_guard.py','tasks.json']:shutil.copyfile(c.ROOT/n,self.root/n)
        (self.root/'runtime-freeze.json').write_text('{}')
        self.seen=[]

    def validate(self):return self.settings,self.tasks,self.order

    def response(self,index,*,body=None,stop='end_turn',rid=None):
        tid=self.order[index]['task']
        text=json.dumps({'replacement':(self.root/'fixtures'/tid/'reference-body.txt').read_text()}) if body is None else body
        raw=dict(output=dict(message=dict(role='assistant',content=[dict(text=text)])),usage=dict(inputTokens=10,outputTokens=20,totalTokens=30),
                 stopReason=stop,ResponseMetadata=dict(RequestId=rid or 'fake-'+str(index),RetryAttempts=0))
        return dict(text=text,content=raw['output']['message']['content'],usage=raw['usage'],stop_reason=stop,request_id=raw['ResponseMetadata']['RequestId'],retry_attempts=0,raw_response=raw)

    def transport(self,request):
        i=len(self.seen);self.assertEqual(request,c.read(self.root/'frozen-001'/self.order[i]['payload']))
        self.seen.append(copy.deepcopy(request));return self.response(i)

    def run_fake(self,transport=None):
        with contextlib.redirect_stdout(io.StringIO()):
            return collect.collect(self.root/'model-001',transport or self.transport,100,root=self.root,clock=lambda:1,validate=self.validate)

    def test_complete_exact_sixteen_and_review(self):
        s=self.run_fake();self.assertEqual((s['reserved'],s['admitted'],len(self.seen)),(16,16,16))
        r=review.review_collection(self.root,validate=self.validate)
        self.assertEqual(r['unique_request_ids'],16);self.assertEqual(r['tokens']['totalTokens'],480)
        with self.assertRaises(FileExistsError):self.run_fake()
        self.assertEqual(len(self.seen),16)

    def test_timeout_terminal_preserves_prefix(self):
        def transport(request):
            if len(self.seen)==2:raise TimeoutError('not logged verbatim')
            return self.transport(request)
        s=self.run_fake(transport);self.assertEqual((s['reserved'],s['completed_responses'],s['ambiguous_or_unsaved']),(3,2,1))
        r=review.review_collection(self.root,validate=self.validate)
        self.assertFalse(r['collection_complete']);self.assertEqual(len(r['admitted']),2)
        self.assertNotIn('not logged verbatim',json.dumps(c.read(self.root/'model-001/results.json')))

    def test_duplicate_id_stops(self):
        def transport(request):
            i=len(self.seen);self.seen.append(request);return self.response(i,rid='same')
        s=self.run_fake(transport);self.assertEqual(len(self.seen),2);self.assertEqual(s['status'],'COLLECTION_STOPPED')

    def test_invalid_usage_stops(self):
        def transport(request):
            r=self.response(0);r['usage']['totalTokens']=29;self.seen.append(request);return r
        s=self.run_fake(transport);self.assertEqual(len(self.seen),1);self.assertEqual(s['status'],'COLLECTION_STOPPED')

    def test_guard_rejection_and_truncation_consume_slots_without_retry(self):
        def transport(request):
            i=len(self.seen);self.seen.append(request)
            return self.response(i,body='{"replacement":"assume false;"}') if i==0 else self.response(i,stop='max_tokens') if i==1 else self.response(i)
        s=self.run_fake(transport);self.assertEqual((len(self.seen),s['admitted']),(16,14))
        review.review_collection(self.root,validate=self.validate)

    def test_mutated_candidate_rejected_by_review(self):
        self.run_fake();p=self.root/'model-001/slot-01/candidate.txt';p.write_bytes(p.read_bytes()+b' ')
        with self.assertRaisesRegex(ValueError,'Candidate replay'):review.review_collection(self.root,validate=self.validate)

    def test_missing_response_rejected_by_review(self):
        self.run_fake();(self.root/'model-001/slot-01/response.json').unlink()
        with self.assertRaises(FileNotFoundError):review.review_collection(self.root,validate=self.validate)

    def test_raw_provider_metadata_cannot_be_invented(self):
        self.run_fake()
        for p in [self.root/'model-001/slot-01/response.json',self.root/'model-001/requests/response-001.json']:
            r=c.read(p);r['raw_response']['ResponseMetadata']['RequestId']='other';durable_json(p,r)
        with self.assertRaisesRegex(ValueError,'Provider metadata'):review.review_collection(self.root,validate=self.validate)

    def test_sdk_single_attempt_exact_payload(self):
        observed={};request=c.read(self.root/'frozen-001'/self.order[0]['payload']);raw=self.response(0)['raw_response']
        class FakeClient:
            def converse(self,**kw):observed['request']=kw;return raw
        def factory(*args,**kw):observed['client']=(args,kw);return FakeClient()
        def config(**kw):observed['config']=kw;return kw
        response=bedrock_transport(self.settings,client_factory=factory,config_factory=config)(request)
        self.assertEqual(observed['request'],request)
        self.assertEqual(observed['config']['retries']['total_max_attempts'],1)
        self.assertEqual(response['retry_attempts'],0)

    def test_gate_budget_and_closed_latch(self):
        calls=[];g=RequestGate(self.root/'one',1,10,lambda p:calls.append(p) or {},clock=lambda:1)
        g.invoke({},task_id='x',attempt_id='1')
        with self.assertRaises(GateClosed):g.invoke({},task_id='x',attempt_id='2')
        self.assertEqual(len(calls),1)
        def fail(p):raise TimeoutError()
        h=RequestGate(self.root/'closed',2,10,fail,clock=lambda:1)
        with self.assertRaises(TimeoutError):h.invoke({},task_id='x',attempt_id='1')
        with self.assertRaises(GateClosed):h.invoke({},task_id='x',attempt_id='2')
        self.assertEqual(len(h.state['reservations']),1)

    def test_deadline_before_and_after_reservation(self):
        calls=[];g=RequestGate(self.root/'expired',2,10,lambda p:calls.append(p),clock=lambda:10)
        with self.assertRaises(GateClosed):g.invoke({},task_id='x',attempt_id='1')
        times=iter([1,2,10]);h=RequestGate(self.root/'crossed',2,10,lambda p:calls.append(p),clock=lambda:next(times))
        with self.assertRaises(GateClosed):h.invoke({},task_id='x',attempt_id='1')
        self.assertEqual(len(h.state['reservations']),1);self.assertEqual(calls,[])

    def test_command_scope_and_resources(self):
        cmd,logical,limit,required,base=v.make_command('dafny-vmc','slot-01',c.ROOT/'work/dafny-vmc/slot-01')
        self.assertEqual(len(base['explicit_sources']),28);self.assertEqual(len(required),267)
        self.assertEqual([x for x in logical if x.endswith('.dfy')],sorted(base['explicit_sources']))
        cmd,logical,limit,required,base=v.make_command('vest','slot-03',c.ROOT/'work/vest/slot-03')
        self.assertIn('CARGO_BUILD_JOBS=4',cmd);self.assertEqual(logical[-2:],['--num-threads','3']);self.assertNotIn('--focus',logical)
        self.assertEqual([c.STAGES[x]['cpus'] for x in ['collect','dafny-vmc','vest']],[1,1,4])

    def test_qualified_baseline_replay_and_warning_rejection(self):
        q=c.ROOT/'inputs'/c.QUAL_REL
        for project,path in [('dafny-vmc','coverage-001/results/vmc_baseline-adapter'),('vest','vest-coverage-001/results/baseline-adapter')]:
            d=q/path;bound=c.read(d/'bound-record.json');raw={n:(d/n).read_bytes() for n in bound['raw_sha256']}
            base=c.read(q/('coverage-001/profile.json' if project=='dafny-vmc' else 'vest-coverage-001/profile.json'))
            o=c.verification_observation(project,c.read(d/'record.json'),raw,base)
            self.assertTrue(o['qualified_scope_pass']);self.assertFalse(o['strict_zero_warning_pass'])
            altered=copy.deepcopy(base);altered['upstream_warnings']=[]
            self.assertFalse(c.verification_observation(project,c.read(d/'record.json'),raw,altered)['qualified_scope_pass'])

    def test_missing_provider_never_full_scope_pass(self):
        d=c.ROOT/'inputs'/c.PILOT_REL/'runtime-002/verification-001/vest-pair-seed'
        bound=c.read(d/'bound-record.json');raw={n:(d/n).read_bytes() for n in bound['raw_sha256']}
        base=c.read(c.ROOT/'inputs'/c.QUAL_REL/'vest-coverage-001/profile.json')
        o=c.verification_observation('vest',c.read(d/'record.json'),raw,base)
        self.assertEqual(o['category'],'PROOF_FAILURE');self.assertFalse(o['qualified_scope_pass']);self.assertFalse(o['coverage_complete'])

    def test_authorization_binds_budget_freezes_and_expiry(self):
        a=dict(authorized=True,max_calls=16,retries=False,reassign_unused=False,proposal_sha256=c.FREEZE_SHA,runtime_sha256=c.sha(self.root/'runtime-freeze.json'),expires_at_epoch=50,human_basis='test only')
        durable_json(self.root/'authorization.json',a);c.authorization(self.root,now=1)
        for field,val in [('max_calls',17),('runtime_sha256','bad'),('expires_at_epoch',0)]:
            durable_json(self.root/'authorization.json',{**a,field:val})
            with self.assertRaises(ValueError):c.authorization(self.root,now=1)

    def test_fake_native_worker_and_stale_evidence_rejection(self):
        self.run_fake();collection=review.review_collection(self.root,validate=self.validate);entry=collection['admitted'][0]
        task=self.tasks[entry['task']];q=self.root/'fake-upstream';up=q/'upstream/dafny-vmc'/task['file'];up.parent.mkdir(parents=True)
        candidate=(self.root/'model-001/slot-01/candidate.txt').read_bytes();up.write_bytes(candidate)
        meta=self.root/'inputs'/c.QUAL_REL;(meta/'coverage-001').mkdir(parents=True)
        shutil.copyfile(c.ROOT/'inputs'/c.QUAL_REL/'coverage-001/profile.json',meta/'coverage-001/profile.json')
        (meta/'source-manifest.json').write_text(json.dumps([dict(id='dafny-vmc',files={task['file']:c.sha(up)})]))
        gate={k:collection[k] for k in ['proposal_sha256','runtime_sha256','collection_files']};gate['admitted']=[entry]
        durable_json(self.root/'verification-gate.json',gate)
        out=self.root/'verification-dafny-vmc-001';out.mkdir()
        env=dict(job_id='FAKE-NO-COMPUTE',cpus=1,model_calls=0,execution_root=str(self.root),verification_gate_sha256=c.sha(self.root/'verification-gate.json'),runtime_sha256=c.sha(self.root/'runtime-freeze.json'))
        (self.root/'submissions').mkdir();v.write(self.root/'submissions/dafny-vmc.json',dict(job_id=env['job_id']))
        v.write(out/'environment.json',env)
        saved=c.ROOT/'inputs'/c.QUAL_REL/'coverage-001/results/vmc_baseline-adapter'
        def fake(label,command,cwd,output,environment,limit):
            d=output/label;d.mkdir();bound=c.read(saved/'bound-record.json')
            work=self.root/'work/dafny-vmc/slot-01'
            for n in bound['raw_sha256']:
                dest=(work/n[4:]) if n.startswith('csv/') else d/n
                dest.parent.mkdir(parents=True,exist_ok=True);dest.write_bytes((saved/n).read_bytes())
            r=dict(command=command,cwd=str(cwd),exit_code=0,elapsed_seconds=1,model_calls=0,attempts=1,
                   artifacts={n:c.sha(d/n) for n in ['stdout.txt','stderr.txt','resources.txt']})
            v.write(d/'record.json',r);return r
        with patch.object(v,'remote_qualification',return_value=q):
            row=v.verify_one(entry,task,'dafny-vmc',out,env['job_id'],root=self.root,native_capture=fake)
            v.write(out/'complete.json',dict(project='dafny-vmc',model_calls=0,results=[row],expected_candidates=1))
            with patch.object(c,'validate_package',return_value=self.validate()):
                self.assertEqual(review.review_verification('dafny-vmc',self.root)['qualified_passes'],1)
                p=out/'slot-01/bound-record.json';b=c.read(p);b['run_id']='old-job:slot-01';durable_json(p,b)
                with self.assertRaisesRegex(ValueError,'Stale run'):review.review_verification('dafny-vmc',self.root)

    def test_slurm_stages_request_only_declared_resources(self):
        for stage,name in [('collect','collect.sbatch'),('dafny-vmc','verify-dafny-vmc.sbatch'),('vest','verify-vest.sbatch')]:
            script=(c.ROOT/name).read_text();self.assertIn('#SBATCH --cpus-per-task='+str(c.STAGES[stage]['cpus'])+'\n',script)
            self.assertIn('#SBATCH --ntasks=1\n',script);self.assertIn('#SBATCH --no-requeue\n',script)
            self.assertIn('cd "${SLURM_SUBMIT_DIR}"\n',script)


if __name__=='__main__':unittest.main(verbosity=2)
